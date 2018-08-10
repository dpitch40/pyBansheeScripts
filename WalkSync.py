import os.path
import os
import shutil
import threading
import argparse
import operator
import datetime
import logging
import enum
import collections

import config
from core.util import compare_filesets, excape_xml_chars, pathname2xml, sort_key

global showSkipped

class Action(enum.Enum):
    SYNC = 0
    DELETE = 1
    SKIP = 2
    ENCODE = 3

lame_input_formats = ('.mp3', '.wav')

stopEvent = threading.Event()

PLAYLISTS_TO_SYNC = config.PlaylistsToSync
BASE_DIR = config.MediaDir
BASE_DEVICE = config.BaseDevice

#------------------------------------------------------------------------------
# CHECKER THREAD
#------------------------------------------------------------------------------

# Threaded function that determines the actions to take with the tracks to sync
def get_changes(allTracks, changes, bitrate):
    #Populates changes (a Queue) with a series of 4-tuples:
    #trackDict, filename, action, description string

    sortKeys = ["AlbumArtist", "Album", "Disc", "TrackNumber"]
    tracksToSync = sorted(allTracks, key=operator.itemgetter(*sortKeys))
    dests = [t.extraData["Dest"] for t in tracksToSync]

    # Get list of files currently on player
    filesOnPlayer = list()
    for device in os.listdir(BASE_DIR):# dirsToPlaylistIDs.keys():
        artistDir = os.path.join(BASE_DIR, device, "MUSIC")
        for dirpath, dirnames, filenames in os.walk(artistDir):
            for f in filenames:
                filesOnPlayer.append(os.path.join(dirpath, f))
    
    # Handle deletions first
    # Take the set difference of the two sets of filenames
    # with open("FNames.txt", 'w') as f:
    #     f.write("Dests:\n\n%s\n\n" % '\n'.join(sorted(["%s\t%s" % (d, type(d)) for d in dests])))
    #     f.write("Existing:\n\n%s" % '\n'.join(sorted(["%s\t%s" % (d, type(d)) for d in filesOnPlayer])))
    tosyncnew, common, filestoremove = Util.compare_filesets(dests, filesOnPlayer)

    for fName in filestoremove:
        if stopEvent.is_set():
            return
        changes.put((None, fName, DELETE, None))

    for track, dest in zip(tracksToSync, dests):
        if stopEvent.is_set():
            return
        loc = track["Location"]
        if not os.path.exists(loc):
            continue
        action, reason = SKIP, None
        
        sourceBr = track['BitRate']
        # Check if we need to reencode the track down to a lower bitrate
        encodeNeeded = bitrate is not None and bitrate + 5 < sourceBr
        base, ext = os.path.splitext(dest)
        
        if os.path.exists(dest):
            onDiskTime = os.path.getmtime(loc)
            onPlayerTime = os.path.getmtime(dest)
            if onDiskTime <= onPlayerTime:
                # File on player has been modified more recently
                if encodeNeeded and ext in lame_input_formats:
                    #Find destination bitrate
                    dext = os.path.splitext(dest)[1].lower()
                    if dext == '.wav':
                        destBr = 1411
                    elif dext == '.mp3':
                        destBr = MP3(dest, ID3=EasyID3).info.bitrate/1000
                    else:
                        assert False, "I forgot to cover filetype for %s." % dest

                    if abs(bitrate - destBr) <= 5:
                        # destBr is already below the target bit rate, we're good
                        action, reason = SKIP, "Dest bitrate OK"
                    elif destBr < bitrate - 5:
                        action, reason = ENCODE, "Dest bitrate too low"
                    else:
                        # The destination bitrate is too high, needs to be encoded down
                        action, reason = ENCODE, "Dest bitrate too high"
                else: # No encode needed
                    sizeDiffPct = abs((os.path.getsize(dest) - track["FileSize"]) /
                            float(track["FileSize"]))
                    if sizeDiffPct < 0.05: # File sizes within 5% of each other
                        action, reason = SKIP, "File sizes match"
                    elif ext not in lame_input_formats:
                        action, reason = SYNC, "Ext not supported by LAME"
                    else:
                        action, reason = SYNC, "File sizes don't match: %d != %d" % \
                            (os.path.getsize(dest), track["FileSize"])
            elif onDiskTime - 5 > onPlayerTime: # Subtract 5 due to fluctuations
                onDiskStamp = datetime.datetime.fromtimestamp(onDiskTime)
                onPlayerStamp = datetime.datetime.fromtimestamp(onPlayerTime)
                daysNewer = (onDiskStamp - onPlayerStamp).days
                onDiskS = onDiskStamp.strftime(config.TsFmt)
                onPlayerS = onPlayerStamp.strftime(config.TsFmt)
                # File on disk has been modified more recently
                if encodeNeeded:
                    # action, reason = ENCODE, "File has been modified; %s > %s" % (onDiskS, onPlayerS)
                    action, reason = ENCODE, "File has been modified; %d days newer" % daysNewer
                else:
                    # action, reason = SYNC, "File has been modified; %s > %s" % (onDiskS, onPlayerS)
                    action, reason = SYNC, "File has been modified; %d days newer" % daysNewer
            else:
                action, reason = SKIP, "File not changed long enough ago"
        else: # File does not exist on player
            if bitrate is not None:
                if ext not in lame_input_formats:
                    action, reason = SYNC, "Ext not supported by LAME"
                elif encodeNeeded:
                    action, reason = ENCODE, "Does not exist on player"
                else:
                    action, reason = SYNC, "Does not exist on player"
            else:
                action, reason = SYNC, "Does not exist on player"
        # print track["Location"], dest, action, reason
        changes.put((track, dest, action, reason))
    # Sentinel
    changes.put((None, None, None, None))

#------------------------------------------------------------------------------
# SYNCER THREAD
#------------------------------------------------------------------------------

def track_sync(changes, dryrun, bitrate, size):
    #Sync the tracks
    progress = 0
    synced = 0
    encoded = 0
    deleted = 0
    skipped = 0

    dirSizes = dict()
    createdDirs = set()

    sizeDelta = 0
    
    while True:
        try:
            track, dest, action, reason = changes.get(True, 5)
        except Queue.Empty:
            break
        if action is None:
            break

        progress = synced + encoded + deleted + skipped
        total = progress + changes.qsize()

        destDir = os.path.dirname(dest)
        
        if action == DELETE:
            logging.info("Deleting\t!%s!" % dest)

            if destDir in dirSizes:
                dirSizes[destDir] -= 1
            else:
                dirSizes[destDir] = len(os.listdir(destDir)) - 1

            if size:
                sizeDelta -= os.path.getsize(dest)
            if not dryrun:
                os.remove(dest)
            if dirSizes[destDir] == 0:
                logging.info("Removing\t%s" % destDir)
                if not dryrun:
                    try:
                        os.removedirs(destDir)
                    except OSError:
                        logging.error("***ERROR:\tCould not remove %s, it is not empty" % destDir)
            deleted += 1

        elif action == SYNC:
            loc = track["Location"]
            if size:
                sizeDelta += os.path.getsize(loc)
            if loc.lower().endswith(".mp3"):
                audio = MP3(loc, ID3=EasyID3)
                tagChanges = list()
                # print audio, '\n'
                # print track, '\n'
                for tag, fieldName in [("album", "Album"),
                                              # ("albumartistsort", "AlbumArtist"),
                                              ("artist", "Artist"),
                                              ("genre", "Genre"),
                                              ("title", "Title")]:
                    if tag not in audio or audio[tag][0] != track[fieldName]:
                        tagChanges.append((tag, fieldName))
                if len(tagChanges) > 0:
                    logging.debug("Re-tagging\t%s" % 
                            ', '.join(["%s: %s -> %s" % (tag, audio.get(tag, ['""'])[0], track[fieldName])
                                    for tag, fieldName in tagChanges]))

            if destDir not in createdDirs and not os.path.exists(destDir):
                logging.info("Creating\t%s" % destDir)
                createdDirs.add(destDir)
                if not dryrun:
                    os.makedirs(destDir)
            logging.info("Syncing \t%s\t(%s)" % (dest, reason))
            if not dryrun:
                if loc.lower().endswith(".mp3"):
                    if len(tagChanges) > 0:
                        for tag, fieldName in tagChanges:
                            audio[tag] = track[fieldName]
                        audio.save()
                        
                shutil.copy(track["Location"], dest)

                if loc.lower().endswith(".mp3"):
                    # Some changes specifically for the on-device tracks
                    trackChanges = list()
                    # if track["TrackNumber"] != 0:
                    #    trackChanges.append(("tracknumber", str(track["TrackNumber"])))
                    # if track["Disc"] != 0:
                    #    trackChanges.append(("discnumber", str(track["Disc"])))
                    # if track["AlbumArtist"] is not None and track["AlbumArtist"] != track["Artist"]:
                    #     trackChanges.append(("artist", track["AlbumArtist"]))
                    if len(trackChanges) > 0:
                        audio = MP3(dest, ID3=EasyID3)
                        for tag, value in trackChanges:
                            audio[tag] = value
                        # TrackFixup.fixTrack(dest, silent=True)
                        audio.save()
            synced += 1

        elif action == ENCODE:
            if destDir not in createdDirs and not os.path.exists(destDir):
                logging.info("Creating\t%s" % destDir)
                createdDirs.add(destDir)
                if not dryrun:
                    os.makedirs(destDir)
            logging.info("Re-encoding\t%s to %d kbps\t(%s)" % (dest, bitrate, reason))
            if not dryrun:
                track.encode(dest, bitrate)
            encoded += 1
        else:
            if showSkipped:
                logging.info("Skipping\t%s\t(%s)" % (dest, reason))
            skipped += 1

    outStr = '%d synced\t%d encoded\t%d skipped\t %d deleted' % (synced, encoded, skipped, deleted)
    if size:
        sizeStr = "%d" % sizeDelta
        sizeStrMB = "%.2f" % (float(sizeDelta) / (2 ** 20))
        if sizeDelta > 0:
            sizeStr = '+' + sizeStr
            sizeStrMB = '+' + sizeStrMB
        outStr = "%s\t%s bytes (%s MB)" % (outStr, sizeStr, sizeStrMB)
    logging.info(outStr)
    stopEvent.set()

#------------------------------------------------------------------------------
# BASE THREAD
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Initialization
#------------------------------------------------------------------------------

# Returns a set containing TrackIDs of singleton tracks
# def findSingletons(db, playlist, rows, albumArtists):
#     singletons = set()
#     playlistID = playlist["PlaylistID"]
#     if playlist["Smart"]:
#         pl = "Smart"
#     else:
#         pl = ''

#     fullArtists = set()
#     # countByAlbumArtist = dict()
#     for albumArtistID, albumIDs in sorted(albumArtists.items()):
#         c = 0
#         for albumID in albumIDs:
#             # Get info on all the tracks in this album and in the playlist
#             byTrackInfo = db.sql("""SELECT ct.TrackID, ct.TrackCount, ct.Disc, ct.DiscCount
# FROM CoreTracks ct JOIN Core%sPlaylistEntries cpe ON cpe.TrackID = ct.TrackID
# WHERE ct.AlbumID = ? AND cpe.%sPlaylistID = ?""" % (pl, pl), albumID, playlistID)
#             c += len(byTrackInfo)

#             # Get album title
#             # title = db.sql("SELECT Title from CoreAlbums where AlbumID = ?",
#             #                 (albumID,))[0]["Title"]

#             # full = False
#             for r in byTrackInfo:
#                 disc = r["Disc"]
#                 tc = r["TrackCount"]
#                 dc = r["DiscCount"]
#                 # If multiple discs, select just this track's disc
#                 if not dc:
#                     where = "ct.AlbumID = ? AND cpe.%sPlaylistID = ?" % pl
#                     args = (albumID, playlistID)
#                 else:
#                     where = "ct.AlbumID = ? AND ct.Disc = ? AND cpe.%sPlaylistID = ?" % pl
#                     args = (albumID, disc, playlistID)
#                 # Check how many songs from this disc are in the playlist
#                 discCountOnPL = db.sql("""SELECT COUNT(*) as c FROM CoreTracks ct
# JOIN Core%sPlaylistEntries cpe ON cpe.TrackID = ct.TrackID WHERE %s""" % (pl, where), *args)[0]['c']

#                 # Consider this album a "full album" if any of its discs has all its tracks
#                 # represented in the playlist, or it if the count is "close enough")
#                 if tc > 0 and (discCountOnPL == tc or
#                     (discCountOnPL >= 8 and discCountOnPL + 4 >= tc) or
#                     (discCountOnPL >= 4 and discCountOnPL + 1 >= tc)):
#                     # fullDiscs.add((albumID, disc, title))
#                     # This artist has at least one "full" disc
#                     fullArtists.add(albumArtistID)
#                     break

#         # countByAlbumArtist[albumArtistID] = c
#         if c >= 5 and albumArtistID not in fullArtists:
#             fullArtists.add(albumArtistID)
#             # fullArtists |= set(albumIDs)

#     for r in rows:
#         if r['AlbumArtistID'] not in fullArtists:
#             singletons.add(r["TrackID"])

#     return singletons

def add_extra_track_data(playlists):
    all_tracks = list()

    p_names_to_sync = sorted([k for k in playlists.keys() if k in PLAYLISTS_TO_SYNC],
        key=lambda x: (config.DeviceOrder.index(PLAYLISTS_TO_SYNC[x][0]), x))
    for p_name in p_names_to_sync:
        p_tracks = playlists[p_name]
        logging.debug('Found playlist %s, containing %d tracks', p_name, len(p_tracks))
        for track in p_tracks:
            if not hasattr(track, 'device'):
                device, _, _ = PLAYLISTS_TO_SYNC[p_name]
                track.device = device
                all_tracks.append(track)

    if config.GroupSingletons:
        # Singleton detection
        # An artist (along with all tracks associated with that artist) is
        # considered a 'singleton' on a particular device if it has fewer than 5 tracks
        # and no full albums on that device

        device_artists = collections.defaultdict(list)

        for device in config.DeviceOrder:
            for track in all_tracks:
                if track.device != device:
                    continue
                device_artists[track.album_artist].append(track)

        for artist, tracks in sorted(device_artists.items()):
            album_disc_track_counts = dict()
            album_totals = collections.defaultdict(int)
            track_count = len(tracks)

            for track in tracks:
                key = (track.album, track.dn)
                if track.tc and track.album and key not in album_disc_track_counts:
                    album_disc_track_counts[key] = track.tc
                album_totals[key] += 1

            if track_count < 5 and all([tc > album_totals[key] for key, tc in
                                        album_disc_track_counts.items()]):
                for track in tracks:
                    track.singleton = True
                continue

#------------------------------------------------------------------------------
# Playlist syncing
#------------------------------------------------------------------------------

def genM3UPlaylist(p_name, p_tracks, base_dir, group_artists):
    lines = ["#EXTM3U"]
    call_base_dir = callable(base_dir)
    for track in p_tracks:
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        lines.append("#EXTINF:%d,%s - %s" % (track.length/1000, track.artist, track.title))
        lines.append(track.calculate_fname(bd, group_artists=group_artists))
    return "%s\n" % '\n'.join(lines)

def genM3U8Playlist(p_name, p_tracks, base_dir, group_artists):
    lines = ["#EXTM3U"]
    call_base_dir = callable(base_dir)
    for track in p_tracks:
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        lines.append(track.calculate_fname(bd, group_artists=group_artists)
                    .replace('/', '\\'))
    return "%s\n" % '\n'.join(lines)

def genQLPlaylist(p_name, p_tracks, base_dir, group_artists):
    lines = []
    call_base_dir = callable(base_dir)
    for track in p_tracks:
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        lines.append(track.calculate_fname(bd, group_artists=group_artists))
    return "%s\n" % '\n'.join(lines)

def genXSPFPlaylist(p_name, p_tracks, base_dir, group_artists):
    app_data = list()
    track_str_list = list()
    call_base_dir = callable(base_dir)
    for idx, track in enumerate(p_tracks):
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        loc = track.calculate_fname(bd, group_artists=group_artists)
        xmlLoc = pathname2xml(loc)
        track_strs = ["\t\t<track>"]
        track_str_dict = [("location", xmlLoc),
                        ("title", excape_xml_chars(track.title)),
                        ("creator", excape_xml_chars(track.artist)),
                        ("album", excape_xml_chars(track.album)),
                        ("trackNum", "%d" % track.tn),
                       ]
        track_strs.extend(["\t<%s>%s</%s>" % (k, v, k) for k, v in track_str_dict])
        track_strs.append("</track>")

        track_str_list.append('\n\t\t'.join(track_strs))
        app_data.append('\t\t\t<vlc:item tid="%d"/>' % idx)

    fmt_dict = {"Name": p_name,
                "TrackList": '\n'.join(track_str_list),
                "AppData": '\n'.join(app_data)}
    fmt_str = """<?xml version="1.0" encoding="UTF-8"?>
<playlist xmlns="http://xspf.org/ns/0/" xmlns:vlc="http://www.videolan.org/vlc/playlist/ns/0/" version="1">
\t<title>%(Name)s</title>
\t<trackList>
%(TrackList)s
\t</trackList>
\t<extension application="http://www.videolan.org/vlc/playlist/0">
%(AppData)s
\t</extension>
</playlist>
"""
    return fmt_str % fmt_dict

playlist_gens_by_ext = {'': genQLPlaylist,
                        ".m3u": genM3UPlaylist,
                        ".m3u8": genM3U8Playlist,
                        ".xspf": genXSPFPlaylist}

def sync_playlists(dryrun):
    # Mapping from destination playlist filenames to contents
    p_texts = dict()
    # Set of parent directories of the playlists
    p_dirs = list()

    playlists = config.DefaultDb.load_playlists()
    add_extra_track_data(playlists)
    for p_name, p_tracks in sorted(playlists.items()):
        if not p_tracks:
            continue
        if p_name in PLAYLISTS_TO_SYNC:
            _, sort_order, protocols = PLAYLISTS_TO_SYNC[p_name]
            for protocol in protocols:
                protocol_name, p_ext, base_dir, group_artists = protocol

                p_dir = os.path.join(BASE_DIR, BASE_DEVICE, "Playlists%s" % protocol_name)
                if p_dir not in p_dirs:
                    p_dirs.append(p_dir)
                p_dest = os.path.join(p_dir, "%s%s" % (p_name, p_ext))

                if sort_order:
                    p_tracks.sort(key=sort_key(*sort_order))
                p_text = playlist_gens_by_ext[p_ext](p_name, p_tracks,
                                                     base_dir, group_artists)

                if p_text:
                    p_texts[p_dest] = p_text

    # Get list of playlists already on drive
    cur_playlists = list()
    for p_dir in p_dirs:
        if os.path.exists(p_dir):
            cur_pfiles = os.listdir(p_dir)
        else:
            cur_pfiles = []
            logging.info('Creating directory\t%s' % p_dir)

        if ".m3u" in cur_pfiles:
            cur_pfiles.remove(".m3u")
        cur_playlists.extend([os.path.join(p_dir, name) for name in cur_pfiles])

    to_sync, common, to_remove = compare_filesets(list(p_texts.keys()),
                                                cur_playlists, sort=True)

    # Playlists to add
    to_sync_texts = list()
    for p_dest in to_sync:
        text = p_texts[p_dest]
        to_sync_texts.append(text)
        logging.info("Creating playlist\t%s" % p_dest)

    # Playlists to update
    for p_dest in common:
        text = p_texts[p_dest]
        existing = open(p_dest, 'r').read()
        if text != existing:
            logging.info("Updating playlist\t%s" % p_dest)

            to_sync.append(p_dest)
            to_sync_texts.append(text)
        elif showSkipped:
            logging.info("Skipping playlist\t%s" % p_dest)

    # Playlists to remove
    for p_dest in to_remove:
        logging.info("Deleting playlist\t!%s!" % p_dest)

    # Execute changes
    if not dryrun:
        for p_dest in to_sync:
            p_dir = os.path.dirname(p_dest)
            if not os.path.exists(p_dir):
                os.makedirs(p_dir)

            p_text = p_texts[p_dest]
            with open(p_dest, 'w') as f:
                f.write(p_text)

        for p_dest in to_remove:
            os.remove(p_dest)

# Syncs the specified track IDs to the device.
def sync(allTracks, bitrate, dryrun=False, size=False):
    changes = Queue.Queue()
    checker = threading.Thread(target=get_changes, args=(allTracks, changes, bitrate))
    checker.start()
    syncer = threading.Thread(target=track_sync, args=(changes, dryrun, bitrate, size))
    syncer.start()

def main():
    global showSkipped

    parser = argparse.ArgumentParser(description="Sync specified playlists to a "
                    "portable music player. (Specify them in config/user.py)")
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument("--size", action="store_true",
                help="Calculate the total data size (in bytes) added or removed")
    parser.add_argument("--show-skipped", action="store_true",
                help="Show files that were not synced or updated")

    parser.add_argument("-q", "--quiet", action="store_true",
            help="Minimize output to the console.")
    parser.add_argument("-s", "--silent", action="store_true",
            help="Minimize output to the console even more.")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="Maximize output to the console.")

    args = parser.parse_args()

    if args.verbose:
        debugLevel = logging.DEBUG
    elif args.quiet:
        debugLevel = logging.WARNING
    elif args.silent:
        debugLevel = logging.ERROR
    else:
        debugLevel = logging.INFO
    logging.basicConfig(level=debugLevel, format='%(levelname)s\t%(message)s')

    showSkipped = args.show_skipped

    # if args.playlistprotocol:
    sync_playlists(args.test)

    # sync(trackIDsToTracks.values(), args.test, args.size)
    
if __name__ == '__main__':
    main()