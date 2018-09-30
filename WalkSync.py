import os.path
import os
import shutil
import threading
import argparse
import operator
import datetime
import logging
import enum
import glob
import collections
import itertools
from queue import Queue, Empty

import config
from core.util import compare_filesets, excape_xml_chars, pathname2xml, sort_key, \
        escape_fname

global showSkipped

class Action(enum.Enum):
    SYNC = 0
    UPDATE = 1
    DELETE = 2
    SKIP = 3

lame_input_formats = ('.mp3', '.wav')

stop_event = threading.Event()

PLAYLISTS_TO_SYNC = config.PlaylistsToSync
BASE_DIR = config.MediaDir
BASE_DEVICE = config.BaseDevice

loc_sizes = dict()
def getsize(f):
    if f in loc_sizes:
        return loc_sizes[f]
    else:
        size = loc_sizes[f] = os.path.getsize(f)
        return size

#------------------------------------------------------------------------------
# CHECKER THREAD
#------------------------------------------------------------------------------

# Threaded function that determines the actions to take with the tracks to sync
def get_changes(tracks, changes, synchronous):
    #Populates changes (a Queue) with a series of 4-tuples:
    #track, dest, action, description string
    if synchronous:
        changes = list()
        put = changes.append
    else:
        put = changes.put

    tracks.sort(key=sort_key())
    dests = [t.calculate_fname(os.path.join(BASE_DIR, t.device, 'MUSIC'),
                                group_artists=config.GroupArtistsMedia)
                    for t in tracks]

    # Check for cover art
    cover_art_dirs = set()
    art_locs = list()
    art_dests = list()
    for track, dest in zip(tracks, dests):
        if getattr(track, 'singleton', False):
            continue
        d = os.path.dirname(track.location)
        if d not in cover_art_dirs:
            arts = glob.glob(os.path.join(d, '*.jpg'))
            if arts:
                if len(arts) > 1:
                    for art in arts:
                        if 'cover' in art.lower():
                            art_loc = art
                            break
                    else:
                        art_loc = arts[0]
                else:
                    art_loc = arts[0]
                art_base = os.path.basename(art_loc)
                art_dest = os.path.join(os.path.dirname(dest), art_base)

                art_locs.append(art_loc)
                art_dests.append(art_dest)

            cover_art_dirs.add(d)

    dests.extend(art_dests)

    # Get list of files currently on player
    on_player = list()
    for device in os.listdir(BASE_DIR):# dirsToPlaylistIDs.keys():
        artistDir = os.path.join(BASE_DIR, device, "MUSIC")
        for dirpath, dirnames, filenames in os.walk(artistDir):
            for f in filenames:
                on_player.append(os.path.join(dirpath, f))
    
    # Take the set difference of the two sets of filenames
    tosyncnew, common, filestoremove = compare_filesets(dests, on_player)
    logging.debug('%d to sync, %d common, %d to remove' %
        (len(tosyncnew), len(common), len(filestoremove)))
    to_sync_set = set(tosyncnew)

    # Handle deletions first
    for fname in filestoremove:
        if stop_event.is_set():
            return
        put((None, fname, Action.DELETE, None))

    for track_or_art, dest in zip(itertools.chain(tracks, art_locs), dests):
        if stop_event.is_set():
            return
        is_art = isinstance(track_or_art, str)
        if is_art:
            loc = track_or_art
        else:
            loc = track_or_art.location

        action, reason = Action.SKIP, None
        
        base, ext = os.path.splitext(dest)
        
        if dest not in to_sync_set:
            on_disk_time = os.path.getmtime(loc)
            on_player_time = os.path.getmtime(dest)
            if on_disk_time - 5 > on_player_time: # Subtract 5 due to fluctuations
                on_disk_stamp = datetime.datetime.fromtimestamp(on_disk_time)
                on_player_stamp = datetime.datetime.fromtimestamp(on_player_time)

                days = (on_disk_stamp - on_player_stamp).days
                # File on disk has been modified more recently
                action, reason = Action.UPDATE, "File has been modified; %d days newer" % days
            elif config.CheckSizes:
                loc_size = getsize(loc)
                dest_size = getsize(dest)
                if loc_size != dest_size:
                    action, reason = Action.UPDATE, 'Sizes do not match: %d != %d' % (loc_size, dest_size)
        else: # File does not exist on player
            action, reason = Action.SYNC, "Does not exist on player"

        # print loc, dest, action, reason
        put((loc, dest, action, reason))
    # Sentinel
    put((None, None, None, None))

    if synchronous:
        return changes

#------------------------------------------------------------------------------
# SYNCER THREAD
#------------------------------------------------------------------------------

def track_sync(changes, dryrun, size, shell_cmds, synchronous=False):
    #Sync the tracks
    synced = 0
    deleted = 0
    skipped = 0
    updated = 0

    dir_sizes = dict()
    created_dirs = set()

    size_deltas = collections.defaultdict(int)

    if synchronous:
        itr = changes
    else:
        class Itr(object):
            def __init__(self, q):
                self.q = q

            def __iter__(self):
                while True:
                    try:
                        loc, dest, action, reason = self.q.get(True, 5)
                    except Empty:
                        break
                    if action is None:
                        break

                    yield loc, dest, action, reason

        itr = Itr(changes)
    
    for loc, dest, action, reason in itr:

        dest_dir = os.path.dirname(dest)
        # Find destination device
        device = dest[len(config.MediaDir):].strip('/').split('/', 1)[0]
        
        if action == Action.DELETE:
            if shell_cmds:
                print('rm %s' % escape_fname(dest))
            else:
                logging.info("Deleting\t!%s!" % dest)

            if dest_dir in dir_sizes:
                dir_sizes[dest_dir] -= 1
            else:
                dir_sizes[dest_dir] = len(os.listdir(dest_dir)) - 1

            if size:
                size_deltas[device] -= getsize(dest)
            if not dryrun:
                os.remove(dest)
            if dir_sizes[dest_dir] == 0:
                if shell_cmds:
                    print('rm -rf %s' % escape_fname(dest_dir))
                else:
                    logging.info("Removing\t%s" % dest_dir)
                if not dryrun:
                    try:
                        os.removedirs(dest_dir)
                    except OSError:
                        logging.error("***ERROR:\tCould not remove %s, it is not empty" % dest_dir)
            deleted += 1

        elif action == Action.SYNC or action == Action.UPDATE:
            if size:
                if action == Action.SYNC:
                    size_deltas[device] += getsize(loc)
                else:
                    size_deltas[device] += getsize(loc) - getsize(dest)

            if dest_dir not in created_dirs and not os.path.exists(dest_dir):
                if shell_cmds:
                    print('mkdir -p %s' % escape_fname(dest_dir))
                else:
                    logging.info("Creating\t%s" % dest_dir)
                created_dirs.add(dest_dir)
                if not dryrun:
                    os.makedirs(dest_dir)
            if shell_cmds:
                print('cp %s %s' % (escape_fname(loc), escape_fname(dest)))
            else:
                if action == Action.SYNC:
                    logging.info("Syncing \t%s\t(%s)" % (dest, reason))
                else:
                    logging.info("Updating \t%s\t(%s)" % (dest, reason))
            if not dryrun:     
                shutil.copy(loc, dest)

            if action == Action.SYNC:
                synced += 1
            else:
                updated += 1
        else:
            if showSkipped and not shell_cmds:
                logging.info("Skipping\t%s\t(%s)" % (dest, reason))
            skipped += 1

    out_str = '%d synced\t%d updated\t%d skipped\t %d deleted' % \
            (synced, updated, skipped, deleted)
    logging.info(out_str)
    if size:
        for device, size_delta in sorted(size_deltas.items()):
            if size_delta == 0:
                size_str = '%s: No change' % (device)
            else:
                sc = '+' if size_delta > 0 else '-'
                size_str = "%s: %s%d bytes (%s%.2f MB)" % \
                    (device, sc, size_delta, sc, float(size_delta) / (2 ** 20))
            logging.info(size_str)
    stop_event.set()

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

    return all_tracks

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

def backupPlaylist(p_name, p_tracks, base_dir, group_artists):
    return '%s\n' % '\n'.join([t.location for t in p_tracks])

playlist_gens_by_ext = {'': genQLPlaylist,
                        ".m3u": genM3UPlaylist,
                        ".m3u8": genM3U8Playlist,
                        ".xspf": genXSPFPlaylist,
                        '.bkp': backupPlaylist}

def sync_playlists(dryrun):
    # Mapping from destination playlist filenames to contents
    p_texts = dict()
    # Set of parent directories of the playlists
    p_dirs = list()

    playlists = config.DefaultDb().load_playlists()
    all_tracks = add_extra_track_data(playlists)
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

    return all_tracks

# Syncs the specified track IDs to the device.
def sync(allTracks, dryrun=False, size=False, synchronous=False, shell_cmds=False):
    if synchronous:
        changes = get_changes(allTracks, None, synchronous)
        logging.info('%d tracks found' % len(changes))
        track_sync(changes, dryrun, size, shell_cmds, synchronous)
    else:
        changes = Queue()
        checker = threading.Thread(target=get_changes, args=(allTracks, changes, synchronous))
        checker.start()
        # Wait for the first queue item
        item = changes.get(block=True, timeout=None)
        changes.put(item)
        syncer = threading.Thread(target=track_sync, args=(changes, dryrun, size, shell_cmds, synchronous))
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
    parser.add_argument('--synchronous', action='store_true',
                help='Run the checker and syncer in the same thread')
    parser.add_argument('--shell-cmds', action='store_true',
                help='Print the shell commands to perform the track syncing')

    parser.add_argument("-q", "--quiet", action="store_true",
            help="Minimize output to the console.")
    parser.add_argument("-s", "--silent", action="store_true",
            help="Minimize output to the console even more.")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="Maximize output to the console.")

    args = parser.parse_args()

    if args.verbose:
        debug_level = logging.DEBUG
    elif args.quiet:
        debug_level = logging.WARNING
    elif args.silent:
        debug_level = logging.ERROR
    else:
        debug_level = logging.INFO
    logging.basicConfig(level=debug_level, format='%(levelname)s\t%(message)s')

    showSkipped = args.show_skipped

    # if args.playlistprotocol:
    all_tracks = sync_playlists(args.test)

    sync(all_tracks, args.test, args.size, args.synchronous, args.shell_cmds)
    
if __name__ == '__main__':
    main()