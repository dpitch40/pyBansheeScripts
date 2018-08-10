import os.path
import sys
import sqlite3
import db_glue
import urllib
import shutil
import os
import argparse
import Track
import Util
import Config

dbLoc = os.path.expanduser(os.path.join('~', '.config', 'banshee-1', 'banshee.db'))

db = db_glue.new(dbLoc)

def SyncPlaylist(trackListing, destDir, flat, delete, test):

    # Get list of files currently in the destination directory
    curFiles = list()
    for dirpath, dirnames, filenames in os.walk(destDir):
        curFiles.extend([os.path.join(dirpath, fName) for fName in filenames])

    # Get a mapping from track destinations to their current locations
    destsToLocs = dict()
    for track in trackListing:
        loc = db_glue.sql2pathname(str(track['Uri']))
        ext = os.path.splitext(loc)[1]

        dest = track.getDestName(destDir, ext, ga=False)

        destsToLocs[dest] = loc

    # Take the intersection/differences of the two sets of files
    toSync, current, toRemove = Util.compare_filesets(destsToLocs.keys(), curFiles)
    toSync.sort()
    toRemove.sort()

    if toSync:
        curAlbum = None
        print "Syncing:\n\n"
        for dest in toSync:
            albumPath = os.path.dirname(dest)
            if albumPath != curAlbum:
                curAlbum = albumPath
                print albumPath
            if not test:
                if not os.path.exists(albumPath):
                    os.makedirs(albumPath)
                shutil.copy(destsToLocs[dest], dest)
            # print '\t', destsToLocs[dest]
            print '\t', dest

    if delete:
        if toSync:
            print '\n'
        if toRemove:
            curAlbum = None
            print "Removing:\n\n"
            for fName in toRemove:
                albumPath = os.path.dirname(fName)
                if albumPath != curAlbum:
                    curAlbum = albumPath
                    print albumPath
                if not test:
                    os.remove(fName)
                    os.removedirs(albumPath)
                print '\t', fName
        print "\n\nSyncing %d, removing %d" % (len(toSync), len(toRemove))
    else:
        print "\n\nSyncing %d" % len(toSync)


def main():
    parser = argparse.ArgumentParser(description="Sync the contents of a playlist to a "
                    "directory. (e.g. on a flash drive)")
    parser.add_argument("playlist", help="The name (in Banshee) of the playlist to sync.")
    parser.add_argument("destdir", help="The directory to sync the playlist to.")
    parser.add_argument('-f', "--flat", action="store_true",
            help="Store the playlist contents in flat format, without nesting by artist "
                "and album.")
    parser.add_argument('-d', "--delete", action="store_true",
        help="Delete contents of the destination directory that isn't "
                             "part of the playlist being synced")
    parser.add_argument("-t", "--test", action="store_true", help="Only display changes; do not "
                            "sync any files.")

    # parser.add_argument("--xml", action="store_true")
    args = parser.parse_args()

    playlists = db.sql("SELECT Name, PlaylistID FROM CorePlaylists")
    playlistsDict = dict([(p["Name"].lower(), p["PlaylistID"]) for p in playlists])

    if args.playlist.lower() not in playlistsDict:
        print "No playlist named %s" % args.playlist
        return

    if not os.path.exists(args.destdir) and not test:
        os.makedirs(args.destdir)

    ID = playlistsDict[args.playlist.lower()]
    trackListing = db.sql("""SELECT ct.TrackID, ct.Title, ct.Uri, ca.Name as Artist,
                                    cl.Title as Album, cl.ArtistName as AlbumArtist,
                                    ct.TrackNumber, ct.Disc, ct.Duration AS Duration
FROM CoreTracks ct
JOIN CorePlaylistEntries cpe ON cpe.TrackID = ct.TrackID
JOIN CoreArtists ca ON ca.ArtistID = ct.ArtistID
JOIN CoreAlbums cl ON cl.AlbumID = ct.AlbumID
WHERE cpe.PlaylistID = %d
ORDER BY ca.Name, cl.Title, ct.TrackNumber""" % ID)

    tracks = list()
    for trackDict in trackListing:
        t = Track.Track([Track.TRACKLIST], None, **trackDict)
        # Force adding duration
        t["Duration"] = trackDict["Duration"]
        tracks.append(t)

    SyncPlaylist(tracks, args.destdir, args.flat, args.delete, args.test)

if __name__ == '__main__':
    main()