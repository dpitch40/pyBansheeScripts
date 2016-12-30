import os.path
import os
import urllib
import sys
import shutil
import threading
import argparse
import operator
from subprocess import call, Popen, PIPE

from mutagen.mp3 import MP3
from EasyID3Custom import EasyID3Custom as EasyID3

sys.path.append(os.path.expanduser(os.path.join('~', 'Programs', 'Python', 'Music')))
sys.path.append(os.path.abspath(os.pardir))
import Util
import Queue
import db_glue
import Track
import Config

global debugLevel
global unicodeEncoding

SYNC = 0
DELETE = 1
SKIP = 2
ENCODE = 3

lame_input_formats = ('.mp3', '.wav')

dbloc = os.path.expanduser(os.path.join('~', '.config', 'banshee-1', 'banshee.db'))

db = db_glue.new(dbloc)

stopEvent = threading.Event()

PLAYLIST_LOOKUP = Config.PlaylistsToSync
ORIG_SORTING_PLS = Config.OrigSortPlaylists

REVERSE_PLAYLIST_LOOKUP = dict()
for k, v in PLAYLIST_LOOKUP.items():
    for p in v:
        REVERSE_PLAYLIST_LOOKUP[p] = k
# DEFAULT_DEVICE = "6432-3634"

NONE = 0
ERRORS = 1
WARNINGS = 2
NOTES = 3
DEBUG = 4

baseDir = Config.MediaDir
baseDevice = Config.BaseDevice
PLAYLIST_DIR = os.path.join(baseDir, baseDevice, "Playlists")

debugLevel = DEBUG

def debug(s):
    if debugLevel >= DEBUG:
        print s

def note(s):
    if debugLevel >= NOTES:
        print s

def warn(s):
    if debugLevel >= WARNINGS:
        print s

def error(s):
    if debugLevel >= ERRORS:
        print s

# Returns a list of dicts, one for each playlist, with the keys "Name" and "PlaylistID"
def get_playlists(names):
    playlists = list()
    
    #Get the listings of playlists
    rows = db.sql("SELECT Name, PlaylistID FROM CorePlaylists WHERE Name IN (%s)"
                      % ','.join(['?' for n in names]), names)
    for r in rows:
        playlists.append(r)
        
    return playlists

def getTracksByPlaylistID(playlistID):
    db = db_glue.new(dbloc)
    rows = db.sql("""SELECT
        ct.TrackID AS TrackID,
        ct.Title AS Title,
        ca.Name AS Artist,
        cl.Title AS Album,
        cl.ArtistName AS AlbumArtist,
        ct.Genre AS Genre,
        ct.Year AS Year,
        ct.TrackNumber AS TrackNumber,
        ct.TrackCount AS TrackCount,
        ct.Disc AS Disc,
        ct.DiscCount AS DiscCount,
        ct.Uri AS Uri,
        ct.Duration AS Duration,
        ct.BitRate AS BitRate,
        ct.FileSize AS FileSize,
        cpe.EntryID AS entryID,
        cpe.ViewOrder AS ViewOrder
    FROM CorePlaylistEntries cpe
    JOIN CoreTracks ct ON cpe.TrackID = ct.TrackID,
          CoreAlbums cl ON ct.AlbumID = cl.AlbumID,
          CoreArtists ca ON ct.ArtistID = ca.ArtistID
    WHERE cpe.PlaylistID = ?""", (playlistID,))

    tracks = list()
    for r in rows:
        r["Location"] = db_glue.sql2pathname(str(r["Uri"]))
        if r['Artist'] is None:
            r['Artist'] = 'Unknown Artist'
        if r['Album'] is None:
            r['Album'] = 'Unknown Album'
        track = Track.Track([Track.TRACKLIST], unicodeEncoding=unicodeEncoding, **r)
        for k, v in r.items():
            if k not in track:
                track.extraData[k] = v
        tracks.append(track)

    return tracks

# Returns a fairly comprehensive listing of all the tracks whose IDs are supplied.
def get_tracks(dirsToIDs):
    tracks = list()
    trackIDsSeen = set()
    for artistDir, playlistIDs in sorted(dirsToIDs.items()):
        for playlistID in playlistIDs:
            for r in getTracksByPlaylistID(playlistID):
                trackID = r["TrackID"]
                if trackID in trackIDsSeen:
                    continue
                trackIDsSeen.add(trackID)
                r.extraData["PlaylistID"] = playlistID
                tracks.append(r)
    return tracks

# Create lists of destination filenames that will be synced to
def getDests(dirsToIDs, keyFunc):

    IDsToDirs = dict()
    for d, IDs in dirsToIDs.items():
        for ID in IDs:
            IDsToDirs[ID] = d

    # Get list of dicts containing information on the specified trackIDs
    tracksToSync = get_tracks(dirsToIDs)
    tracksToSync.sort(key=keyFunc)

    dests = list()
    for track in tracksToSync:
        if stopEvent.is_set():
            return
        ext = os.path.splitext(track["Location"])[1]
        dests.append(track.getDestName(IDsToDirs[track.extraData["PlaylistID"]], ext=ext))

    return tracksToSync, dests

# Threaded function that determines the actions to take with the tracks to sync
def get_changes(dirsToIDs, changes, bitrate):
    #Populates changes (a Queue) with a series of 4-tuples:
    #trackDict, filename, action, description string

    sortKeys = ["AlbumArtist", "Album", "Disc", "TrackNumber"]
    tracksToSync, dests = getDests(dirsToIDs, operator.itemgetter(*sortKeys))

    # Get list of files currently on player
    filesOnPlayer = list()
    for artistDir in dirsToIDs.keys():
        for dirpath, dirnames, filenames in os.walk(artistDir):
            for f in filenames:
                filesOnPlayer.append(os.path.join(dirpath, f))
    
    # Handle deletions first
    # Take the set difference of the two sets of filenames
    # with open("FNames.txt", 'w') as f:
    #     f.write("Dests:\n\n%s\n\n" % '\n'.join(sorted(["%s\t%s" % (d, type(d)) for d in dests])))
    #     f.write("Existing:\n\n%s" % '\n'.join(sorted(["%s\t%s" % (d, type(d)) for d in filesOnPlayer])))
    tosyncnew, common, filestoremove = Util.compare_filesets(dests, filesOnPlayer)
    # print len(tosyncnew), len(common), len(filestoremove)
    # raise SystemExit
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

                    if bitrate + 5 >= destBr:
                        action, reason = SKIP, "Dest bitrate low enough"
                    else:
                        action, reason = ENCODE, "Dest bitrate too high"
                else: # No encode needed
                    if os.path.getsize(dest) == track["FileSize"]:
                        action, reason = SKIP, "File sizes match"
                    else:
                        action, reason = SKIP, "Size %d != %d" % (os.path.getsize(dest), track["FileSize"])
            else: #File on disk has been modified more recently
                if encodeNeeded:
                    action, reason = ENCODE, "File has been modified; %.2f < %.2f" % (onPlayerTime, onDiskTime)
                else:
                    action, reason = SYNC, "File has been modified; %.2f < %.2f" % (onPlayerTime, onDiskTime)
        else:
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

def track_sync(changes, dryrun, bitrate):
    #Sync the tracks
    progress = 0
    synced = 0
    encoded = 0
    deleted = 0
    skipped = 0

    dirSizes = dict()
    createdDirs = set()
    
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
            debug("Deleting\t%s" % dest)

            if destDir in dirSizes:
                dirSizes[destDir] -= 1
            else:
                dirSizes[destDir] = len(os.listdir(destDir)) - 1
            if not dryrun:
                os.remove(dest)
            if dirSizes[destDir] == 0:
                note("Removing\t%s" % destDir)
                if not dryrun:
                    try:
                        os.removedirs(destDir)
                    except OSError:
                        error("***ERROR:\tCould not remove %s, it is not empty" % destDir)
            deleted += 1

        elif action == SYNC:
            loc = track["Location"]
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
                    debug("Re-tagging\t%s" % 
                            ', '.join(["%s: %s -> %s" % (tag, audio.get(tag, ['""'])[0], track[fieldName])
                                    for tag, fieldName in tagChanges]))

            if destDir not in createdDirs and not os.path.exists(destDir):
                note("Creating\t%s" % destDir)
                createdDirs.add(destDir)
                if not dryrun:
                    os.makedirs(destDir)
            debug("Syncing \t%s\t(%s)" % (dest, reason))
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
                    if track["AlbumArtist"] is not None and track["AlbumArtist"] != track["Artist"]:
                        trackChanges.append(("artist", track["AlbumArtist"]))
                    if len(trackChanges) > 0:
                        audio = MP3(dest, ID3=EasyID3)
                        for tag, value in trackChanges:
                            audio[tag] = value
                        # TrackFixup.fixTrack(dest, silent=True)
                        audio.save()
            synced += 1

        elif action == ENCODE:
            if destDir not in createdDirs and not os.path.exists(destDir):
                note("Creating\t%s" % destDir)
                createdDirs.add(destDir)
                if not dryrun:
                    os.makedirs(destDir)
            debug("Re-encoding\t%s to %d kbps\t(%s)" % (dest, bitrate, reason))
            if not dryrun:
                if track["AlbumArtist"] is not None:
                    artist = track["AlbumArtist"]
                else:
                    artist = track["Artist"]
                track.MP3Encode(dest, bitrate)
            encoded += 1

        else:
            skipped += 1

    print '%d synced\t%d encoded\t%d skipped\t %d deleted' % (synced, encoded, skipped, deleted)
    stopEvent.set()

# Syncs the specified track IDs to the device.
def sync(dirsToIDs, bitrate, dryrun=False):
    changes = Queue.Queue()
    checker = threading.Thread(target=get_changes, args=(dirsToIDs, changes, bitrate))
    checker.start()
    syncer = threading.Thread(target=track_sync, args=(changes, dryrun, bitrate))
    syncer.start()

def trackToPlaylistRow(dest, device):
    if device != baseDevice:
        dest = dest.replace(os.path.join(baseDir, device), "/<microSD1>")
    else:
        dest = dest.replace(os.path.join(baseDir, device), '')
    return dest#.encode("utf-8")

def playlistToText(playlist, trackIDsToTracks):
    device = playlist["Device"]
    playlistTracks = getTracksByPlaylistID(playlist["PlaylistID"])

    if playlist["Name"] in ORIG_SORTING_PLS:
        playlistTracks.sort(key=operator.itemgetter("ViewOrder", "Artist", "Album", "TrackNumber"))
    else:
        playlistTracks.sort(key=operator.itemgetter("Artist", "Album", "TrackNumber"))

    lines = list()
    for track in playlistTracks:
        track = trackIDsToTracks[track["TrackID"]]
        lines.append(trackToPlaylistRow(track.extraData["Dest"], device))
    return "%s\n" % '\n'.join(lines)

def syncPlaylists(playlists, dirsToIDs, dryrun):
    curPlaylists = os.listdir(PLAYLIST_DIR)
    if ".m3u" in curPlaylists:
        del curPlaylists[curPlaylists.index(".m3u")]
    curPlaylists = [os.path.join(PLAYLIST_DIR, pName) for pName in curPlaylists]
    
    destPlaylists = [os.path.join(PLAYLIST_DIR, "%s.m3u8" % p["Name"]) for p in playlists]
    namesToPlaylists = dict([(p["Name"], p) for p in playlists])

    tracks, dests = getDests(dirsToIDs, operator.itemgetter("entryID"))

    trackIDsToTracks = dict()
    for t, d in zip(tracks, dests):
        t.extraData["Dest"] = d
        trackIDsToTracks[t["TrackID"]] = t

    toSync, common, toRemove = Util.compare_filesets(destPlaylists, curPlaylists)
    
    toSyncTexts = list()

    for pName in toSync:
        playlist = namesToPlaylists[os.path.splitext(os.path.basename(pName))[0]]
        toSyncTexts.append(playlistToText(playlist, tracks, deststrackIDsToTracks))
        print "Syncing playlist\t%s" % pName

    for pName in common:
        playlist = namesToPlaylists[os.path.splitext(os.path.basename(pName))[0]]
        text = playlistToText(playlist, trackIDsToTracks)
        existing = open(pName, 'r').read()
        if text != existing:
            print "Updating playlist\t%s" % pName
            # print len(existing.split('\n')), len(text.split('\n'))
            toSync.append(pName)
            toSyncTexts.append(text)

    for pName in toRemove:
        print "Deleting playlist\t%s" % pName

    if not dryrun:
        for pName, pText in zip(toSync, toSyncTexts):
            with open(pName, 'w') as f:
                f.write(pText)

        for pName in toRemove:
            os.remove(pName)

def main():
    global debugLevel
    global unicodeEncoding

    parser = argparse.ArgumentParser(description="Sync specified playlists to a "
                    "portable music player. (Specify them in Config.py)")
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('-b', dest="bitrate", default=128,
            help="Specify the bit rate to encode files to. Any files with a higher "
                "bit rate will be converted down to save space.")
    parser.add_argument("-q", "--quiet", action="store_true",
            help="Minimize output to the console.")
    parser.add_argument("-s", "--silent", action="store_true",
            help="Don't print anything to the console.")
    parser.add_argument('-u', "--unicodeencoding", help="Specify a unicode encoding to use.",
                        default="utf-8")
    args = parser.parse_args()

    if args.silent:
        debugLevel = ERRORS
    elif args.quiet:
        debugLevel = NOTES
    else:
        debugLevel = DEBUG

    unicodeEncoding = args.unicodeencoding

    allDevices = os.listdir(baseDir)

    # Find the IDs of all the tracks to sync
    if len(args.playlists) == 0:
        args.playlists = list()
        for device in allDevices:
            args.playlists.extend(PLAYLIST_LOOKUP.get(device, []))

    playlists = get_playlists(args.playlists)
    for p in playlists:
        p["Device"] = REVERSE_PLAYLIST_LOOKUP.get(p["Name"], DEFAULT_DEVICE)

    dirsToIDs = dict() # Mapping from music file destination dirs to playlist IDs
    for p in playlists:
        device = p["Device"]
        d = os.path.join(baseDir, device, "MUSIC", "Artists")
        if d in dirsToIDs:
            dirsToIDs[d].append(p['PlaylistID'])
        else:
            dirsToIDs[d] = [p['PlaylistID']]

    syncPlaylists(playlists, dirsToIDs, args.test)

    sync(dirsToIDs, args.bitrate, args.test)
    
if __name__ == '__main__':
    main()