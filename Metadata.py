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
import itertools
import collections
import KeyGen
import Config
Config.GroupArtists = False
import Track
from Track import TRACKLIST, DB, FILE

db = db_glue.new(db_glue.defaultLoc)
Track.db = db
musicDir = Config.MusicDir

trackNumRe = re.compile(r"^(?:(\d)\-)?(\d{1,2})(.+)\.(\w{2,4})$")

LENGTH_UPDATE_THRESHOLD_MS = 600

def ExtractKeys(track, discLens=None):
    keys = list()
    album, artist, title, tn, dn = track["Album"], track["Artist"], track["Title"], \
                                    track["TrackNumber"], track["Disc"]

    if track["Location"]:
        keys.append(track["Location"])

        audio = track.audio
        if audio:
            if tn is None and "tracknumber" in audio:
                tn = audio["tracknumber"][0]
                if '/' in tn:
                    tn = int(tn.split('/')[0])
                else:
                    tn = int(tn)
            if dn is None and "discnumber" in audio:
                dn = audio["discnumber"][0]
                if '/' in dn:
                    dn = int(dn.split('/')[0])
                else:
                    dn = int(dn)
            if title is None and "title" in audio:
                title = audio["title"][0]
            if artist is None and "artist" in audio:
                artist = audio["artist"][0]
            if album is None and "album" in audio:
                album = audio["album"][0]

        d, baseName = os.path.split(track["Location"])
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
        keys.append((dn, tn))
        if dn and discLens is not None:
            keys.append((None, tn + sum([c for d, c in discLens.items() if d < dn])))
    if title:
        keys.append((title, artist, album))

    if track.matchedWithDB:
        keys.append(track["TrackID"])

    return keys

# Creates mappings from TrackID/(dn, tn)/(title, artist, album) tuples to MP3s
def CreateTrackMapping(tracks):
    trackMapping = dict()
    dupKeys = set()

    # Make mapping from disc number to number of tracks on the disc
    discLens = collections.defaultdict(int)
    for track in tracks:
        dn = track["Disc"]
        if dn:
            discLens[dn] += 1

    for track in tracks:
        possKeys = ExtractKeys(track, discLens)
        
        # Ensure each mapping key is unique across all tracks
        for k in possKeys:
            if k in dupKeys:
                continue
            elif k in trackMapping:
                del trackMapping[k]
                dupKeys.add(k)
            else:
                trackMapping[k] = track

    return trackMapping

# Edits tracks
def Edit(tracks, destFiles, changes, test, matchWithDB, relocate, rebase=None):
    edited = 0

    # Are we getting the metadata from a source apart from the files themselves
    extSource = destFiles is not None
    if extSource:
        destTracks = [Track.Track.fromDB(f) for f in destFiles]
        # trackMapping = CreateTrackMapping(destFiles)
    elif rebase:
        destTracks = [Track.Track([Track.FILE], rebase)]

    # Remove album artist if it is equal to the artist for all tracks
    firstArtist = tracks[0]["Artist"]
    nullAlbumArtist = all(t["Artist"] == firstArtist for t in tracks) and \
        all(t["AlbumArtist"] in (None, firstArtist) for t in tracks)

    trackMapping = CreateTrackMapping(tracks)

    # print "trackMapping keys =\n%s\n" % '\n'.join(map(str, sorted(trackMapping.keys())))

    if extSource:
        def matchTrack(track):
            matchKeys = ExtractKeys(track)
            for k in matchKeys:
                if k in trackMapping:
                    return matchKeys, track, trackMapping[k]
            return matchKeys, track, None
        trackItr = itertools.imap(matchTrack, sorted(destTracks,
                key=lambda t: (t["Disc"], t["TrackNumber"], t["Artist"], t["Album"])))
    elif rebase:
        trackItr = [(None, destTracks[0], tracks[0])]
    else:
        trackItr = zip([None] * len(tracks), [None] * len(tracks), tracks)

    totalCount = 0
    overwritten = 0
    for keys, destTrack, origTrack in trackItr:
        totalCount += 1
        if extSource:
            if origTrack is None:
                print "*** ERROR on %s: could not match with track list keys=(%s)" \
                                % (destTrack.name, ', '.join(map(str, keys)))
                continue
            audio = destTrack.audio
            track = origTrack
            track["Duration"] = int(audio.info.length * 1000)
            Util.cautiousUpdate(track, destTrack, overwriteOnNone=True)
        else:
            audio = origTrack.audio
            track = origTrack
        
        fileChanges = dict()
        dbChanges = dict()
        relocated = None

        if audio and not rebase:
            fileChanges = SyncTrackToFile(track, changes, audio, nullAlbumArtist)
        if not track.matchedWithDB:
            if matchWithDB:
                print "* WARNING on %s: could not match with DB" % track.name
            # continue
        elif rebase:
            dbChanges = SyncTrackToDB(destTrack, changes, curTrackID=origTrack["TrackID"])
        elif matchWithDB:
            dbChanges = SyncTrackToDB(track, changes)

        # Relocate
        if audio:
            curName = audio.filename
        elif extSource:
            curName = destTrack["Location"]
        else:
            curName = track["Location"]
        if isinstance(curName, str):
            curName = curName.decode(Config.UnicodeEncoding)

        track.update(changes)

        if "Location" in changes:
            newName = changes["Location"]
        elif rebase:
            newName = rebase
        elif track["Location"] != curName:
            newName = track["Location"]
        else:
            base, ext = os.path.splitext(os.path.basename(curName))
            
            newName = track.getDestName(musicDir, ext, asUnicode=True)

        if curName != newName and (relocate or rebase):
            relocated = (curName, newName)
            oldBase, oldDiff = os.path.split(curName)
            newBase, newDiff = os.path.split(newName)
            while oldBase != newBase:
                oldBase, oldD = os.path.split(oldBase)
                oldDiff = os.path.join(oldD, oldDiff)
                newBase, newD = os.path.split(newBase)
                newDiff = os.path.join(newD, newDiff)

            oldDiff = os.path.join("...", oldDiff).encode(Config.UnicodeEncoding)
            newDiff = os.path.join("...", newDiff).encode(Config.UnicodeEncoding)

            if track.matchedWithDB:
                oldUri = db.sql("SELECT Uri FROM CoreTracks WHERE TrackID = ?",
                            track["TrackID"])[0]["Uri"]
            else:
                oldUri = ''

            newUri = db_glue.pathname2sql(newName.encode(Config.UnicodeEncoding))
            # dbChanges["Uri"] = (db_glue.pathname2sql(oldDiff)[7:], db_glue.pathname2sql(newDiff)[7:])

        if fileChanges or dbChanges or relocated:
            print track.name
            if fileChanges:
                print "  File: %s" % '\n\t'.join(["%s:\t%s -> %s" % (k, v[0], v[1]) for 
                            k, v in sorted(fileChanges.items())])
            if dbChanges and track.matchedWithDB:
                print "  DB:   %s" % '\n\t'.join(["%s:\t%s -> %s" % (k, v[0], v[1]) for 
                            k, v in sorted(dbChanges.items())])

            if rebase:
                dbChanges["Uri"] = (oldUri, newUri)
                print "  Rebasing from %s to %s" % (oldDiff, newDiff)
            elif relocated:
                dbChanges["Uri"] = (oldUri, newUri)
                m = "  Relocating from %s to %s" % (oldDiff, newDiff)
                if os.path.exists(newName):
                    m += " (overwriting existing file)"
                    overwritten += 1
                print m

            if "BitRate" in fileChanges:
                print "  Reencoding from %d to %d bps" % (fileChanges["BitRate"])
            if dbChanges and matchWithDB and track.matchedWithDB:
                UpdateDB(dbChanges, track["TrackID"])
            edited += 1

            if not test:
                if audio:
                    audio.save()

                if track.matchedWithDB:
                    db.commit()
                
                if relocated and not rebase:
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
                    track.encode(track["Location"],
                                 fileChanges["BitRate"][1] / 1000)

    status = "\n%d/%d edited" % (edited, totalCount)
    if overwritten:
        status = "%s (%s overwritten)" % (status, overwritten)
    print status

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
                    k = k.encode(Config.UnicodeEncoding)
                if v is not None and isinstance(v, unicode):
                    v = v.encode(Config.UnicodeEncoding)
                dl.append((k, v))
            writer.writerow(dict(dl))

# Converts a SQL/track list representation to a mutagen-style EasyMP3 object.
def TrackToMutagenDict(d):
    audio = dict()

    for tag in ["Title", "Artist", "Album", "Genre", "Duration", "AlbumArtist", "Year"]:
        value = d.get(tag, None)
        if value is None:
            continue
        if not isinstance(value, unicode):
            value = unicode(str(value))
        audio[Track.SQLToMutagen[tag]] = [value]

    countKeys = (("TrackNumber", "TrackCount"), ("Disc", "DiscCount"))
    for numKey, countKey in countKeys:
        if d.get(numKey, None) is not None:
            numVal = d[numKey]
            newKey = Track.SQLToMutagen[numKey]
            if d[countKey] is not None:
                countVal = d[countKey]
                audio[newKey] = [u"%d/%d" % (numVal, countVal)]
            else:
                audio[newKey] = [unicode(str(numVal))]

    return audio

# Evaluates changes to be made to an MP3
def SyncTrackToFile(track, _changes, audio, nullAlbumArtist):
    mDict = TrackToMutagenDict(track)
    audio["length"] = str(int(audio.info.length * 1000))
    _changes = TrackToMutagenDict(_changes)
    changes = dict()
    for k, v in mDict.items():
        if k in _changes:
            newVal = _changes[k]
        else:
            newVal = v[0]
        curVal = audio.get(k, [None])[0]
        if k not in audio or curVal != newVal:
            #Exceptions
            if k == "length":
                continue # Can't change length in track
            elif nullAlbumArtist and k == "albumartistsort":
                continue

            changes[k] = (curVal, newVal)
            audio[k] = v
    if abs(track["BitRate"] * 1000 - audio.info.bitrate) > 1000:
        changes["BitRate"] = (audio.info.bitrate, track["BitRate"] * 1000)
    return changes

# Evaluates changes to be made to a DB entry
def SyncTrackToDB(track, _changes, curTrackID=None):
    if curTrackID is None:
        curTrackID = track["TrackID"]
    curTrack = db.sql(Track.selectStmt % "TrackID = ?", curTrackID)[0]
    changes = dict()
    for k, v in track.items():
        curVal = curTrack.get(k, None)
        if k in _changes:
            v = _changes[k]
        if k not in curTrack or curVal != v:
            #Exceptions
            if k.startswith("Disc") and v is None and curVal == 0:
                continue
            elif k == "Location":# or k == "Uri":
                continue
            elif k == "Duration" and curVal is not None and v is not None:
                curValInt, newValInt = int(curVal), int(v)
                if abs(newValInt - curValInt) <= LENGTH_UPDATE_THRESHOLD_MS:
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
        rows = db.sql("SELECT AlbumID FROM CoreAlbums WHERE Title = ?", newAlbum)
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
        rows = db.sql("SELECT ArtistID FROM CoreArtists WHERE Name = ?", newArtist)
        if len(rows) == 0:
            print "* WARNING: Artist %r not found. Adding new artists not currently supported. " \
                    "Please change the artist manually." % newArtist
        else:
            tracksChanges["ArtistID"] = rows[0]["ArtistID"]
    if len(tracksChanges) > 1:
        db.sql("UPDATE CoreTracks SET %s WHERE TrackID = :TrackID" % 
            ', '.join(["%s = :%s" % (k, k) for k in tracksChanges if k != "TrackID"]), **tracksChanges)

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
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                        help="Specify extra data fields for tracks loaded from an external source.")
    parser.add_argument("source", nargs='?',
        help="The source to get metadata from (db, files, or a location of a track list).")
    parser.add_argument("files", nargs='*', help="The files being edited/viewed, if any.")

def getTracks(parser, args, integrateChanges=False):

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
        if getattr(args, "action", '') == "edit":
            print "ERROR: Must specify files to edit."
            parser.print_help()
            return
        fNames = None

    extraDict = dict(args.extra)
    for k, v in extraDict.items():
        extraDict[k] = Util.convertStrValue(v)
    kwargs = {}
    if integrateChanges:
        kwargs.update(extraDict)

    if args.source in ("db", "files", "dbonly", "filesonly"):
        if args.source == "db":
            sources = [TRACKLIST, DB, FILE]
        elif args.source == "dbonly":
            sources = [TRACKLIST, DB]
        elif args.source == "files":
            sources = [TRACKLIST, FILE, DB]
        elif args.source == "filesonly":
            sources = [TRACKLIST, FILE]
        tracks = [Track.Track(sources, fn, **kwargs) for fn in fNames]
        fNames = None
    else:
        tl = ParseTables.getAugmentedTrackList(args.source, **kwargs)
        tracks = [Track.Track([Track.TRACKLIST, Track.DB], None, **t) for t in tl]
    tracks.sort(key=operator.itemgetter("Artist", "Album", "Disc", "TrackNumber"))

    if integrateChanges:
        return fNames, tracks
    else:
        return fNames, tracks, extraDict

def main():
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
    parser.add_argument("--rebase", help="Change a track's source to this location.")
    parser.add_argument("action", nargs='?', choices=actionChoices, help="The action to take.")
    addDefaultArguments(parser)

    args = parser.parse_args()
    if not args.help_tags and args.action is None:
        print "ERROR: Must specify action"
        parser.print_help()
        return

    fNames, tracks, changes = getTracks(parser, args)
    if args.rebase:
        assert len(tracks) == 1, "Can only rebase 1 track at a time"
        assert os.path.exists(args.rebase), "Must rebase to an existing file"

    if args.action == "edit":
        Edit(tracks, fNames, changes, args.test, args.matchwithdb, args.reloc, args.rebase)
    elif args.action == "view":
        View(tracks, args.use_repr)
    else:
        Save(tracks)

if __name__ == "__main__":
    main()