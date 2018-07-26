import os.path
import os
import urllib
import sys
import shutil
import threading
import argparse
import operator
import datetime
import difflib
from subprocess import call, Popen, PIPE
import re

from mutagen.mp3 import MP3
from EasyID3Custom import EasyID3Custom as EasyID3

sys.path.append(os.path.expanduser(os.path.join('~', 'Programs', 'Python', 'Music')))
sys.path.append(os.path.abspath(os.pardir))
import Config
import Util
import Queue
import db_glue
import Track
import SyncPlaylist

global debugLevel
global showSkipped

# global playlistIDsToTracks
# global allTracks
# global trackIDsToTracks

SYNC = 0
DELETE = 1
SKIP = 2
ENCODE = 3

lame_input_formats = ('.mp3', '.wav')

dbloc = os.path.expanduser(os.path.join('~', '.config', 'banshee-1', 'banshee.db'))

db = db_glue.new(dbloc)
Track.db = db

stopEvent = threading.Event()

PLAYLISTS_TO_SYNC = Config.PlaylistsToSync

NONE = 0
ERRORS = 1
WARNINGS = 2
NOTES = 3
DEBUG = 4

BASE_DIR = Config.MediaDir
BASE_DEVICE = Config.BaseDevice

debugLevel = DEBUG

def debug(s):
    if debugLevel >= DEBUG:
        print "DEBUG  : %s" % s

def note(s):
    if debugLevel >= NOTES:
        print "NOTE   : %s" % s

def warn(s):
    if debugLevel >= WARNINGS:
        print "WARNING: %s" % s

def error(s):
    if debugLevel >= ERRORS:
        print "ERROR  : %s" % s

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
                onDiskS = onDiskStamp.strftime(Config.TsFmt)
                onPlayerS = onPlayerStamp.strftime(Config.TsFmt)
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
            note("Deleting\t!%s!" % dest)

            if destDir in dirSizes:
                dirSizes[destDir] -= 1
            else:
                dirSizes[destDir] = len(os.listdir(destDir)) - 1

            if size:
                sizeDelta -= os.path.getsize(dest)
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
                    debug("Re-tagging\t%s" % 
                            ', '.join(["%s: %s -> %s" % (tag, audio.get(tag, ['""'])[0], track[fieldName])
                                    for tag, fieldName in tagChanges]))

            if destDir not in createdDirs and not os.path.exists(destDir):
                note("Creating\t%s" % destDir)
                createdDirs.add(destDir)
                if not dryrun:
                    os.makedirs(destDir)
            note("Syncing \t%s\t(%s)" % (dest, reason))
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
                note("Creating\t%s" % destDir)
                createdDirs.add(destDir)
                if not dryrun:
                    os.makedirs(destDir)
            note("Re-encoding\t%s to %d kbps\t(%s)" % (dest, bitrate, reason))
            if not dryrun:
                track.encode(dest, bitrate)
            encoded += 1
        else:
            if showSkipped:
                note("Skipping\t%s\t(%s)" % (dest, reason))
            skipped += 1

    outStr = '%d synced\t%d encoded\t%d skipped\t %d deleted' % (synced, encoded, skipped, deleted)
    if size:
        sizeStr = "%d" % sizeDelta
        sizeStrMB = "%.2f" % (float(sizeDelta) / (2 ** 20))
        if sizeDelta > 0:
            sizeStr = '+' + sizeStr
            sizeStrMB = '+' + sizeStrMB
        outStr = "%s\t%s bytes (%s MB)" % (outStr, sizeStr, sizeStrMB)
    note(outStr)
    stopEvent.set()

#------------------------------------------------------------------------------
# BASE THREAD
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Initialization
#------------------------------------------------------------------------------

# Returns a list of dicts, one for each playlist, with the keys "Name" and "PlaylistID"
def get_playlists(names):
    playlists = list()
    
    for name in names:
        smart = False
        #Get the listings of playlists
        rows = db.sql("SELECT Name, PlaylistID FROM CorePlaylists WHERE Name = ?", name)
        if not rows:
            rows = db.sql("SELECT Name, SmartPlaylistID AS PlaylistID "
                          "FROM CoreSmartPlaylists WHERE Name = ?", name)
            smart = True
        # for r in sorted(rows, key=lambda r: names.index(r["Name"])):
        if not rows:
            raise ValueError, "Playlist not found: %s" % name
        r = rows[0]
        r["Smart"] = smart
        playlists.append(r)
        
    return playlists

def getTracksByPlaylist(playlist, useDB):
    # db = db_glue.new(dbloc)
    smart = playlist["Smart"]
    if smart:
        pl = "Smart"
        vo = ''
    else:
        pl = ''
        vo = ", cpe.ViewOrder as ViewOrder"
    rows = db.sql("""SELECT
        ct.TrackID AS TrackID,
        ct.Title AS Title,
        ca.Name AS Artist,
        ca.ArtistID as ArtistID,
        cl.Title AS Album,
        cl.AlbumID as AlbumID,
        cl.ArtistName AS AlbumArtist,
        cl.ArtistID AS AlbumArtistID,
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
        cpe.EntryID AS entryID%s
    FROM Core%sPlaylistEntries cpe
    JOIN CoreTracks ct ON cpe.TrackID = ct.TrackID,
          CoreAlbums cl ON ct.AlbumID = cl.AlbumID,
          CoreArtists ca ON ct.ArtistID = ca.ArtistID
    WHERE cpe.%sPlaylistID = ?
    ORDER BY Artist, Album, Disc, TrackNumber""" % (vo, pl, pl), playlist["PlaylistID"])

    albumArtists = dict()
    for r in rows:
        r["Location"] = db_glue.sql2pathname(str(r["Uri"]))
        if r['Artist'] is None:
            r['Artist'] = 'Unknown Artist'
        if r['Album'] is None:
            r['Album'] = 'Unknown Album'
        if r['AlbumArtist'] is None:
            r['AlbumArtist'] = r['Artist']

        if r['AlbumArtistID'] not in albumArtists:
            artistAlbums = albumArtists[r['AlbumArtistID']] = set()
        else:
            artistAlbums = albumArtists[r['AlbumArtistID']]
        if r['AlbumID'] not in artistAlbums:
            artistAlbums.add(r['AlbumID'])

    singletons = findSingletons(db, playlist, rows, albumArtists)

    tracks = list()
    for r in rows:
        sources = [Track.TRACKLIST]
        if useDB:
            sources.append(Track.DB)
        track = Track.Track(sources, isSingleton=r["TrackID"] in singletons, **r)
        for k, v in r.items():
            if k not in track:
                track.extraData[k] = v
        tracks.append(track)

    return tracks

# Returns a set containing TrackIDs of singleton tracks
def findSingletons(db, playlist, rows, albumArtists):
    singletons = set()
    playlistID = playlist["PlaylistID"]
    if playlist["Smart"]:
        pl = "Smart"
    else:
        pl = ''

    fullArtists = set()
    # countByAlbumArtist = dict()
    for albumArtistID, albumIDs in sorted(albumArtists.items()):
        c = 0
        for albumID in albumIDs:
            # Get info on all the tracks in this album and in the playlist
            byTrackInfo = db.sql("""SELECT ct.TrackID, ct.TrackCount, ct.Disc, ct.DiscCount
FROM CoreTracks ct JOIN Core%sPlaylistEntries cpe ON cpe.TrackID = ct.TrackID
WHERE ct.AlbumID = ? AND cpe.%sPlaylistID = ?""" % (pl, pl), albumID, playlistID)
            c += len(byTrackInfo)

            # Get album title
            # title = db.sql("SELECT Title from CoreAlbums where AlbumID = ?",
            #                 (albumID,))[0]["Title"]

            # full = False
            for r in byTrackInfo:
                disc = r["Disc"]
                tc = r["TrackCount"]
                dc = r["DiscCount"]
                # If multiple discs, select just this track's disc
                if not dc:
                    where = "ct.AlbumID = ? AND cpe.%sPlaylistID = ?" % pl
                    args = (albumID, playlistID)
                else:
                    where = "ct.AlbumID = ? AND ct.Disc = ? AND cpe.%sPlaylistID = ?" % pl
                    args = (albumID, disc, playlistID)
                # Check how many songs from this disc are in the playlist
                discCountOnPL = db.sql("""SELECT COUNT(*) as c FROM CoreTracks ct
JOIN Core%sPlaylistEntries cpe ON cpe.TrackID = ct.TrackID WHERE %s""" % (pl, where), *args)[0]['c']

                # Consider this album a "full album" if any of its discs has all its tracks
                # represented in the playlist, or it if the count is "close enough")
                if tc > 0 and (discCountOnPL == tc or 
                    (discCountOnPL >= 8 and discCountOnPL + 4 >= tc) or
                    (discCountOnPL >= 4 and discCountOnPL + 1 >= tc)):
                    # fullDiscs.add((albumID, disc, title))
                    # This artist has at least one "full" disc
                    fullArtists.add(albumArtistID)
                    break

        # countByAlbumArtist[albumArtistID] = c
        if c >= 5 and albumArtistID not in fullArtists:
            fullArtists.add(albumArtistID)
            # fullArtists |= set(albumIDs)

    for r in rows:
        if r['AlbumArtistID'] not in fullArtists:
            singletons.add(r["TrackID"])

    return singletons

# Returns a fairly comprehensive listing of all the tracks whose IDs are supplied.
def getTrackIDstoTracks(playlists):
    # tracks = list()
    # IDsToDirs = dict()
    trackIDsToTracks = dict()
    # Mapping from playlist ID to corresponding tracks
    # playlistIDsToTracks = dict()
    # List of all tracks to be synced
    for playlist in playlists:
        device = PLAYLISTS_TO_SYNC[playlist["Name"]][0]
        playlistID = playlist["PlaylistID"]
        artistDir = os.path.join(BASE_DIR, device, "MUSIC")

        for track in getTracksByPlaylist(playlist, False):
            if stopEvent.is_set():
                return
            trackID = track["TrackID"]
            if trackID in trackIDsToTracks:
                if track.isSingleton or not trackIDsToTracks[trackID].isSingleton:
                    continue
            trackIDsToTracks[trackID] = track

            track.extraData["PlaylistID"] = playlistID
            device = os.path.basename(os.path.dirname(artistDir))

            ext = os.path.splitext(track["Location"])[1]
            track.extraData["Dest"] = track.getDestName(artistDir, ext=ext)
            track.extraData["Device"] = device
            # print track["Title"], device
            # tracks.append(track)

    return trackIDsToTracks

#------------------------------------------------------------------------------
# Playlist syncing
#------------------------------------------------------------------------------

def genM3UPlaylist(playlist, baseDir, groupArtists, tracks):
    lines = ["#EXTM3U"]
    callBaseDir = callable(baseDir)
    for track in tracks:
        if callBaseDir:
            bd = baseDir(track)
        else:
            bd = baseDir
        lines.append("#EXTINF:%d,%s - %s" % (track["Duration"]/1000, track["Artist"], track["Title"]))
        lines.append(track.getDestName(bd, ga=groupArtists, asUnicode=True))
    return "%s\n" % '\n'.join(lines)

def genM3U8Playlist(playlist, baseDir, groupArtists, tracks):
    lines = ["#EXTM3U"]
    callBaseDir = callable(baseDir)
    for track in tracks:
        if callBaseDir:
            bd = baseDir(track)
        else:
            bd = baseDir
        lines.append(track.getDestName(bd, ga=groupArtists, asUnicode=True).replace('/', '\\'))
    return "%s\n" % '\n'.join(lines)

def genXSPFPlaylist(playlist, baseDir, groupArtists, tracks):
    return SyncPlaylist.exportAsXML(playlist["Name"], tracks, baseDir, groupArtists)

playlist_gens_by_ext = {".m3u": genM3UPlaylist,
                        ".m3u8": genM3U8Playlist,
                        ".xspf": genXSPFPlaylist}

def playlistToText(playlist, protocolName, pExt, baseDir, groupArtists,
                   sortOrder, trackIDsToTracks):
    # Get tracks for this playlist
    if playlist["Smart"]:
        pl = "Smart"
        vo = ''
    else:
        pl = ''
        vo = ", cpe.ViewOrder as ViewOrder"
    rows = db.sql("""SELECT ct.TrackID AS TrackID%s
FROM CoreTracks ct
JOIN Core%sPlaylistEntries cpe ON ct.TrackID = cpe.TrackID
WHERE cpe.%sPlaylistID = ?""" % (vo, pl, pl), playlist["PlaylistID"])
    if not rows:
        return ''

    playlistTracks = list()
    for r in rows:
        t = trackIDsToTracks[r["TrackID"]]
        if "ViewOrder" in r:
            t.extraData["ViewOrder"] = r["ViewOrder"]
        playlistTracks.append(t)

    playlistTracks.sort(key=operator.itemgetter(*sortOrder))

    return playlist_gens_by_ext[pExt](playlist, baseDir, groupArtists, playlistTracks)

def syncPlaylists(playlists, trackIDsToTracks, dryrun):
    # Mapping from destination playlist filenames to contents
    playlistTexts = dict()
    # Set of parent directories of the playlists
    playlistDirs = list()
    for playlist in playlists:
        pDevice, protocols = PLAYLISTS_TO_SYNC[playlist["Name"]]
        for protocol in protocols:
            protocolName, pExt, baseDir, groupArtists, sortOrder = protocol

            pDir = os.path.join(BASE_DIR, BASE_DEVICE, "Playlists%s" % protocolName)
            if pDir not in playlistDirs:
                playlistDirs.append(pDir)
            pDest = os.path.join(pDir, "%s%s" % (playlist["Name"], pExt))

            pText = playlistToText(playlist, protocolName, pExt, baseDir, groupArtists,
                                          sortOrder, trackIDsToTracks)

            if pText:
                pDest = pDest.encode(Config.UnicodeEncoding)
                playlistTexts[pDest] = pText

    # Get list of playlists already on drive
    curPlaylists = list()
    for playlistDir in playlistDirs:
        if not os.path.exists(pDir):
            os.makedirs(pDir)
        curPlaylistFiles = os.listdir(playlistDir)
        if ".m3u" in curPlaylistFiles:
            curPlaylistFiles.remove(".m3u")
        curPlaylists.extend([os.path.join(playlistDir, pName) for pName in curPlaylistFiles])

    toSync, common, toRemove = Util.compare_filesets(playlistTexts.keys(), curPlaylists, sort=True)

    # Playlists to add
    toSyncTexts = list()
    for pDest in toSync:
        text = playlistTexts[pDest]
        toSyncTexts.append(text)
        note("Syncing playlist\t%s" % pDest)

    # Playlists to update
    for pDest in common:
        text = playlistTexts[pDest]
        if isinstance(text, unicode):
            text = text.encode(Config.UnicodeEncoding)
        existing = open(pDest, 'rU').read()
        if text != existing:
            oldLines = existing.split('\n')
            newLines = text.split('\n')

            note("Updating playlist\t%s" % pDest)

            if "Transient" in pDest:#debugLevel == DEBUG:
                isJunk = lambda s: s.strip() == ''
                matcher = difflib.SequenceMatcher(isjunk=isJunk, a=oldLines, b=newLines)
                debug("Playlists are %.1f%% similar" % (matcher.ratio() * 100))

                d = difflib.Differ(isJunk)
                blockStarted = True
                for line in d.compare(oldLines, newLines):
                    if line.startswith(' '):
                        continue
                    l = line.strip()
                    if line.startswith('-'):
                        if not blockStarted:
                            blockStarted = True
                        debug(l)
                    else:
                        blockStarted = False
                        debug(l)


            toSync.append(pDest)
            toSyncTexts.append(text)
        elif showSkipped:
            note("Skipping playlist\t%s" % pDest)

    # Playlists to remove
    for pDest in toRemove:
        note("Deleting playlist\t!%s!" % pDest)

    # Execute changes
    if not dryrun:
        for pDest, pText in zip(toSync, toSyncTexts):
            with open(pDest, 'w') as f:
                if isinstance(pText, unicode):
                    pText = pText.encode(Config.UnicodeEncoding)
                f.write(pText)

        for pDest in toRemove:
            os.remove(pDest)

# Syncs the specified track IDs to the device.
def sync(allTracks, bitrate, dryrun=False, size=False):
    changes = Queue.Queue()
    checker = threading.Thread(target=get_changes, args=(allTracks, changes, bitrate))
    checker.start()
    syncer = threading.Thread(target=track_sync, args=(changes, dryrun, bitrate, size))
    syncer.start()

def main():
    global debugLevel
    global showSkipped

    parser = argparse.ArgumentParser(description="Sync specified playlists to a "
                    "portable music player. (Specify them in Config.py)")
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('-b', dest="bitrate", default=None, type=int,
            help="Specify the bit rate to encode files to. Any files with a higher "
                "bit rate will be converted down to save space. If not specified, does not "
                "convert files; copies them as-is.")
    parser.add_argument("-s", "--silent", action="store_true",
            help="Minimize output to the console.")
    parser.add_argument("-q", "--quiet", action="store_true",
            help="Minimize output to the console.")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="Maximize output to the console.")
    parser.add_argument("--size", action="store_true",
                help="Calculate the total data size (in bytes) added or removed")
    parser.add_argument("--show-skipped", action="store_true",
                help="Show files that were not synced or updated")

    args = parser.parse_args()

    if args.verbose:
        debugLevel = DEBUG
    elif args.quiet:
        debugLevel = WARNINGS
    elif args.silent:
        debugLevel = ERRORS
    else:
        debugLevel = NOTES
    showSkipped = args.show_skipped

    allDevices = os.listdir(BASE_DIR)
    allDevices.sort(key=lambda d: '' if d == BASE_DEVICE else d)

    # Find the IDs of all the tracks to sync
    plNames = list()
    for pName, pInfo in sorted(PLAYLISTS_TO_SYNC.items(),
                               key=lambda i: Config.DeviceOrder.index(i[1][0])):
        if pInfo[0] in allDevices:
            plNames.append(pName)
    playlists = get_playlists(plNames)

    # Populate playlistIDsToTracks
    trackIDsToTracks = getTrackIDstoTracks(playlists)

    # if args.playlistprotocol:
    syncPlaylists(playlists, trackIDsToTracks, args.test)

    sync(trackIDsToTracks.values(), args.bitrate, args.test, args.size)
    
if __name__ == '__main__':
    main()