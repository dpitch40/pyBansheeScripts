import ParseTables
from EasyID3Custom import EasyID3Custom as EasyID3
import db_glue
import os
import os.path
import argparse
import Util
import operator
import re
import csv
import KeyGen
import Track
from Track import TRACKLIST, DB, FILE
import Config

global unicodeEncoding

db = db_glue.new(db_glue.defaultLoc)
Track.db = db
musicDir = Config.MusicDir

trackNumRe = re.compile(r"^(?:(\d)\-)?(\d{1,2})(.+)\.(\w{2,4})$")

LENGTH_UPDATE_THRESHOLD_MS = 600

# Creates mappings from TrackID/(dn, tn)/(title, artist, album) tuples to MP3s
def CreateTrackMapping(destFiles):
    trackMapping = dict()
    for df in destFiles:
        track = Track.Track.fromDB(df, unicodeEncoding=unicodeEncoding)
        trackMapping[df] = track
        audio = track.audio

        if track.matchedWithDB:
            trackMapping[track["TrackID"]] = track

        tn = None
        dn = None
        title = None
        artist = None
        album = None
        if "tracknumber" in audio:
            tn = audio["tracknumber"][0]
            if '/' in tn:
                tn = int(tn.split('/')[0])
            else:
                tn = int(tn)
        if "discnumber" in audio:
            dn = audio["discnumber"][0]
            if '/' in dn:
                dn = int(dn.split('/')[0])
            else:
                dn = int(dn)
        if "title" in audio:
            title = audio["title"][0]
        if "artist" in audio:
            artist = audio["artist"][0]
        if "album" in audio:
            album = audio["album"][0]

        d, baseName = os.path.split(df)
        d, albumDir = os.path.split(d)
        artistDir = os.path.basename(d)
        m = trackNumRe.match(baseName)
        if m:
            dnF, tnF, titleF, ext = m.groups()
            if dnF:
                dnF = int(dnF)
            tnF = int(tnF)
            if not tn:
                tn = tnF
            if not dn:
                dn = dnF
        if not artist:
            artist = artistDir
        if not album:
            album = albumDir
        if not title:
            title = titleF

        if tn not in (0, None):
            trackMapping[(dn, tn)] = track
        trackMapping[(title, artist, album)] = track
    # print trackMapping.keys()
    return trackMapping

# Edits tracks
def Edit(tracks, destFiles, test, number, matchWithDB, relocate):
    edited = 0

    extSource = destFiles is not None
    if extSource:
        # Create a mapping from destFiles to tracks
        trackMapping = CreateTrackMapping(destFiles)

    # Remove album artist if it is equal to the artist for all tracks
    firstArtist = tracks[0]["Artist"]
    nullAlbumArtist = all(t["Artist"] == firstArtist for t in tracks) and \
        all(t["AlbumArtist"] in (None, firstArtist) for t in tracks)

    # dns = set(track["Disc"] for track in tracks)
    # oneDisc = len(dns) == 1
    discLens = {0: 0}
    for track in tracks:
        dn = track["Disc"]
        if dn in discLens:
            discLens[dn] += 1
        else:
            discLens[dn] = 1

    for track in tracks:
        if extSource:
            tnInfo = (track["Disc"], track["TrackNumber"])
            if track["Disc"] is not None:
                altTnInfo = (None, track["TrackNumber"] + 
                            sum([discLens.get(dn+1, 0) for dn in xrange(track["Disc"] - 1)]))
            else:
                altTnInfo = (None, track["TrackNumber"])
            titleInfo = (track["Title"], track["Artist"], track["Album"])
            if track.matchedWithDB and track["TrackID"] in trackMapping:
                destTrack = trackMapping[track["TrackID"]]
            elif track["Location"] in trackMapping:
                destTrack = trackMapping[track["Location"]]
            elif tnInfo in trackMapping:
                destTrack = trackMapping[tnInfo]
            # elif oneDisc and altTnInfo in trackMapping:
            elif altTnInfo in trackMapping:
                destTrack = trackMapping[altTnInfo]
            elif titleInfo in trackMapping:
                destTrack = trackMapping[titleInfo]
            else:
                print "*** ERROR on %s: could not match with destination file %s %s %s" % \
                    (track.name, tnInfo, titleInfo, altTnInfo)
                print '\n'.join(map(str, sorted(trackMapping.keys())))
                continue
            audio = destTrack.audio
            Util.cautiousUpdate(track, destTrack, overwriteOnNone=True)
        else:
            audio = track.audio

        fileChanges = dict()
        dbChanges = dict()
        relocated = None

        fileChanges = SyncTrackToFile(track, audio, nullAlbumArtist)
        if not track.matchedWithDB:
            if matchWithDB:
                print "* WARNING on %s: could not match with DB" % track.name
            # continue
        elif matchWithDB:
            dbChanges = SyncTrackToDB(track)

        # Relocate
        curName = audio.filename.decode(unicodeEncoding)
        if track["Location"] != curName:
            newName = track["Location"]
        else:
            base, ext = os.path.splitext(os.path.basename(curName))
            
            newName = track.getDestName(musicDir, ext, number)

        if curName != newName and relocate:
            relocated = (curName, newName)
            oldBase, oldDiff = os.path.split(curName)
            newBase, newDiff = os.path.split(newName)
            while oldBase != newBase:
                oldBase, oldD = os.path.split(oldBase)
                oldDiff = os.path.join(oldD, oldDiff)
                newBase, newD = os.path.split(newBase)
                newDiff = os.path.join(newD, newDiff)

            oldDiff = os.path.join("...", oldDiff).encode(unicodeEncoding)
            newDiff = os.path.join("...", newDiff).encode(unicodeEncoding)

            if track.matchedWithDB:
                oldUri = db.sql("SELECT Uri FROM CoreTracks WHERE TrackID = ?",
                            (track["TrackID"],))[0]["Uri"]
            else:
                oldUri = ''
            newUri = db_glue.pathname2sql(newName.encode(unicodeEncoding))
            dbChanges["Uri"] = (db_glue.pathname2sql(oldDiff)[7:], db_glue.pathname2sql(newDiff)[7:])

        if fileChanges or dbChanges or relocated:
            print track.name
            if fileChanges:
                print "  File: %s" % '\n\t'.join(["%s:\t%s -> %s" % (k, v[0], v[1]) for 
                            k, v in sorted(fileChanges.items())])
            if dbChanges and track.matchedWithDB:
                print "  DB:   %s" % '\n\t'.join(["%s:\t%s -> %s" % (k, v[0], v[1]) for 
                            k, v in sorted(dbChanges.items())])

            if relocated:
                dbChanges["Uri"] = (oldUri, newUri)
                m = "  Relocating from %s to %s" % (oldDiff, newDiff)
                if os.path.exists(newName):
                    m += " (overwriting existing file)"
                print m
            if "BitRate" in fileChanges:
                print "  Reencoding from %d to %d bps" % (fileChanges["BitRate"])
            if dbChanges and matchWithDB and track.matchedWithDB:
                UpdateDB(dbChanges, track["TrackID"])
            edited += 1

            if not test:
                audio.save()

                if track.matchedWithDB:
                    db.commit()
                
                if relocated:
                    curName, newName = relocated
                    newDir = os.path.dirname(newName)
                    if not os.path.exists(newDir):
                        os.makedirs(newDir)
                    if os.path.exists(newName):
                        os.remove(newName)
                    os.rename(curName, newName)
                    try:
                        os.removedirs(os.path.dirname(curName))
                    except OSError:
                        pass

                if "BitRate" in fileChanges:
                    track.MP3Encode(track["Location"],
                                    fileChanges["BitRate"][1] / 1000, number)

    print "\n%d/%d edited" % (edited, len(tracks))

# Saves a track list to Album.csv
def Save(tracks, outName="Album.csv"):
    headersPresent = [False for k in Track.allKeys]
    for track in tracks:
        for i, k in enumerate(Track.allKeys):
            if k in track:
                headersPresent[i] = True
    headers = [k for i, k in enumerate(Track.allKeys) if headersPresent[i]]
    with open(outName, 'w') as f:
        writer = csv.DictWriter(f, headers, lineterminator='\n')
        writer.writeheader()
        for track in tracks:
            dl = list()
            for k in headers:
                v = track[k]
                if k is not None and isinstance(k, unicode):
                    k = k.encode(unicodeEncoding)
                if v is not None and isinstance(v, unicode):
                    v = v.encode(unicodeEncoding)
                dl.append((k, v))
            writer.writerow(dict(dl))

# Converts a SQL/track list representation to a mutagen-style EasyMP3 object.
def TrackToMutagenDict(d):
    audio = dict()

    for tag in ["Title", "Artist", "Album", "Genre", "Duration", "AlbumArtist", "Year"]:
        value = d[tag]
        if value is None:
            continue
        if not isinstance(value, unicode):
            value = unicode(str(value))
        audio[Track.SQLToMutagen[tag]] = [value]

    countKeys = (("TrackNumber", "TrackCount"), ("Disc", "DiscCount"))
    for numKey, countKey in countKeys:
        if d[numKey] is not None:
            numVal = d[numKey]
            newKey = Track.SQLToMutagen[numKey]
            if d[countKey] is not None:
                countVal = d[countKey]
                audio[newKey] = [u"%d/%d" % (numVal, countVal)]
            else:
                audio[newKey] = [unicode(str(numVal))]

    return audio

# Evaluates changes to be made to an MP3
def SyncTrackToFile(track, audio, nullAlbumArtist):
    mDict = TrackToMutagenDict(track)
    audio["length"] = str(int(audio.info.length * 1000))
    changes = dict()
    for k, v in mDict.items():
        newVal = v[0]
        curVal = audio.get(k, [None])[0]
        if k not in audio or curVal != newVal:
            #Exceptions
            if k == "length" and curVal is not None and newVal is not None:
                curValInt, newValInt = int(curVal), int(newVal)
                if abs(newValInt - curValInt) <= LENGTH_UPDATE_THRESHOLD_MS:
                    continue
            elif nullAlbumArtist and k == "albumartistsort":
                continue

            changes[k] = (curVal, newVal)
            audio[k] = v
    if abs(track["BitRate"] * 1000 - audio.info.bitrate) > 1000:
        changes["BitRate"] = (audio.info.bitrate, track["BitRate"] * 1000)
    return changes

# Evaluates changes to be made to a DB entry
def SyncTrackToDB(track):
    curTrack = db.sql(Track.selectStmt % "TrackID = ?", (track["TrackID"],))[0]
    changes = dict()
    for k, v in track.items():
        curVal = curTrack.get(k, None)
        if k not in curTrack or curVal != v:

            #Exceptions
            if k.startswith("Disc") and v is None and curVal == 0:
                continue
            elif k == "Location":# or k == "Uri":
                continue

            changes[k] = (curVal, v)
    return changes

# Updates the DB with the changes from SyncTrackToDB
def UpdateDB(changes, trackID):
    tracksChanges = {"TrackID": trackID}
    for k, v in changes.items():
        if k not in ("Album", "AlbumArtist", "Artist"):
            tracksChanges[k] = v[1]

    if "Title" in tracksChanges:
        newTitle = tracksChanges["Title"]
        titleSort, titleSortKey = KeyGen.nameToKey(newTitle)
        tracksChanges["TitleLowered"] = newTitle.lower()
        tracksChanges["TitleSort"] = titleSort
        tracksChanges["TitleSortKey"] = titleSortKey

    if "Album" in changes:
        newAlbum = changes["Album"][1]
        rows = db.sql("SELECT AlbumID FROM CoreAlbums WHERE Title = ?", (newAlbum,))
        if len(rows) == 0:
            print "* WARNING: Album %r not found. Adding new albums not currently supported. " \
                    "Please change the album manually." % newAlbum
        else:
            tracksChanges["AlbumID"] = rows[0]["AlbumID"]

    if "AlbumArtist" in changes:
        print "* WARNING: Changing album artists is not currently supported. " \
                "Please change the album artist manually."

    if "Artist" in changes:
        newArtist = changes["Artist"][1]
        rows = db.sql("SELECT ArtistID FROM CoreArtists WHERE Name = ?", (newArtist,))
        if len(rows) == 0:
            print "* WARNING: Artist %r not found. Adding new artists not currently supported. " \
                    "Please change the artist manually." % newArtist
        else:
            tracksChanges["ArtistID"] = rows[0]["ArtistID"]
    if len(tracksChanges) > 1:
        db.sql("UPDATE CoreTracks SET %s WHERE TrackID = :TrackID" % 
            ', '.join(["%s = :%s" % (k, k) for k in tracksChanges if k != "TrackID"]), tracksChanges)

# Views tracks
def View(tracks, useRepr=False):
    for audio in tracks:
        if useRepr:
            print repr(audio)
        else:
            print str(audio)

def addDefaultArguments(parser):
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument("--help-tags", action="store_true",
                        help="Display the EasyID3 tags that can be viewed or edited.")
    parser.add_argument('-u', "--unicodeencoding", help="Specify a unicode encoding to use.",
                        default="utf-8")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                        help="Specify extra data fields for tracks loaded from an external source.")
    parser.add_argument("source", nargs='?',
        help="The source to get metadata from (db, files, or a location of a track list).")
    parser.add_argument("files", nargs='*', help="The files being edited/viewed, if any.")

def getTracks(parser, args):

    if args.help_tags:
        print '\n'.join(sorted(EasyID3.valid_keys.keys()))
        raise SystemExit
    elif args.source is None:
        print "ERROR: Must specify metadata data source"
        parser.print_help()
        raise SystemExit

    if args.files:
        fNames = list()
        for f in args.files:
            fNames.extend(Util.expandPath(f))
    else:
        if args.action == "edit":
            print "ERROR: Must specify files to edit."
            parser.print_help()
            return
        fNames = None

    unicodeEncoding = args.unicodeencoding
    extraDict = dict(args.extra)
    for k, v in extraDict.items():
        extraDict[k] = ParseTables.convertStrValue(v, unicodeEncoding)

    if args.source in ("db", "files"):
        if args.source == "db":
            tracks = [Track.Track([TRACKLIST, DB, FILE], fn, unicodeEncoding, **extraDict) for fn in fNames]
        elif args.source == "files":
            tracks = [Track.Track([TRACKLIST, FILE, DB], fn, unicodeEncoding, **extraDict) for fn in fNames]
        fNames = None
    else:
        tl = ParseTables.getAugmentedTrackList(args.source, args.unicodeencoding, **extraDict)
        tracks = [Track.Track.fromTrackList(t, unicodeEncoding) for t in tl]
    tracks.sort(key=operator.itemgetter("Artist", "Album", "Disc", "TrackNumber"))

    return fNames, tracks

def main():
    global unicodeEncoding

    actionChoices = ["view", "edit", "save"]

    progDesc = """View and edit the metadata of music files. Can be used to make changes
to files and/or synchronize metadata between files and the database."""

    parser = argparse.ArgumentParser(description=progDesc)
    parser.add_argument("--nodb", action="store_false", dest="matchwithdb",
                        help="Don't try to match tracks with the database.")
    parser.add_argument('-r', "--use-repr", action="store_true",
                        help="When viewing, use repr() to display rather than str().")
    parser.add_argument("--noreloc", dest="reloc", action="store_false",
                        help="Disable automatic relocation of files.")
    parser.add_argument('-n', "--nonumber", action="store_false", dest="number",
                        help="Do not use track/disc numbers when determining track names.")
    parser.add_argument("action", nargs='?', choices=actionChoices, help="The action to take.")
    addDefaultArguments(parser)

    args = parser.parse_args()
    if not args.help_tags and args.action is None:
        print "ERROR: Must specify action"
        parser.print_help()
        return

    unicodeEncoding = args.unicodeencoding
    fNames, tracks = getTracks(parser, args)

    if args.action == "edit":
        Edit(tracks, fNames, args.test, args.number, args.matchwithdb, args.reloc)
    elif args.action == "view":
        View(tracks, args.use_repr)
    else:
        Save(tracks)

if __name__ == "__main__":
    main()