import os
import os.path
import argparse
import operator
import re
import itertools
import collections

from config import DefaultDb

from core.util import convert_str_value, get_fnames
from core.track import Track

from db.db import MusicDb

from mfile.mfile import MusicFile

from parse.file import read_tracklist, tracklist_exts, write_tracklist
from parse.web import url_re, parse_tracklist_from_url

from match import match_metadata_to_tracks

# Edits tracks
# def Edit(tracks, destFiles, changes, test, matchWithDB, relocate, rebase=None,
#          suffix=None):
#     edited = 0

#     # Are we getting the metadata from a source apart from the files themselves
#     extSource = destFiles is not None
#     if extSource:
#         destTracks = [Track.Track.fromDB(f) for f in destFiles]
#         # trackMapping = CreateTrackMapping(destFiles)
#     elif rebase:
#         destTracks = [Track.Track([Track.FILE], rebase)]

#     # Remove album artist if it is equal to the artist for all tracks
#     firstArtist = tracks[0]["Artist"]
#     nullAlbumArtist = all(t["Artist"] == firstArtist for t in tracks) and \
#         all(t["AlbumArtist"] in (None, firstArtist) for t in tracks)

#     trackMapping = CreateTrackMapping(tracks)

#     # print "trackMapping keys =\n%s\n" % '\n'.join(map(str, sorted(trackMapping.keys())))

#     if extSource:
#         def matchTrack(track, index):
#             matchKeys = ExtractKeys(track, index)
#             for k in matchKeys:
#                 if k in trackMapping:
#                     # print 'MATCHED %s with %s on %r' % \
#                     #     (track['Location'], trackMapping[k]['Location'], k)
#                     return matchKeys, track, trackMapping[k]
#             return matchKeys, track, None
#         trackItr = itertools.imap(matchTrack, sorted(destTracks,
#                 key=lambda t: (t["Disc"], t["TrackNumber"], t["Artist"], t["Album"])),
#                     range(len(destTracks)))
#     elif rebase:
#         trackItr = [(None, destTracks[0], tracks[0])]
#     else:
#         trackItr = zip([None] * len(tracks), [None] * len(tracks), tracks)

#     totalCount = 0
#     overwritten = 0
#     for keys, destTrack, origTrack in trackItr:
#         totalCount += 1
#         if extSource:
#             if origTrack is None:
#                 print "*** ERROR on %s: could not match with track list keys=(%s)" \
#                                 % (destTrack.name, ', '.join(map(str, keys)))
#                 continue
#             audio = destTrack.audio
#             track = origTrack
#             track["Duration"] = int(audio.info.length * 1000)
#             Util.cautiousUpdate(track, destTrack, overwriteOnNone=True)
#         else:
#             audio = origTrack.audio
#             track = origTrack
        
#         fileChanges = dict()
#         dbChanges = dict()
#         relocated = None

#         if audio and not rebase:
#             fileChanges = SyncTrackToFile(track, changes, audio, nullAlbumArtist)
#         if not track.matchedWithDB:
#             if matchWithDB:
#                 print "* WARNING on %s: could not match with DB" % track.name
#             # continue
#         elif rebase:
#             dbChanges = SyncTrackToDB(destTrack, changes, curTrackID=origTrack["TrackID"])
#         elif matchWithDB:
#             dbChanges = SyncTrackToDB(track, changes)

#         # Relocate
#         if audio:
#             curName = audio.filename
#         elif extSource:
#             curName = destTrack["Location"]
#         else:
#             curName = track["Location"]
#         if isinstance(curName, str):
#             curName = curName.decode(Config.UnicodeEncoding)

#         # track.update(changes)

#         if "Location" in changes:
#             newName = changes["Location"]
#         elif rebase:
#             newName = rebase
#         # elif track["Location"] != curName:
#         #     newName = track["Location"]
#         else:
#             base, ext = os.path.splitext(os.path.basename(curName))
            
#             newName = track.getDestName(musicDir, ext, asUnicode=True)

#         if suffix:
#             newBase, newExt = os.path.splitext(newName)
#             newName = ''.join([newBase, suffix, newExt])

#         if curName != newName and (relocate or rebase):
#             relocated = (curName, newName)
#             oldBase, oldDiff = os.path.split(curName)
#             newBase, newDiff = os.path.split(newName)
#             while oldBase != newBase:
#                 oldBase, oldD = os.path.split(oldBase)
#                 oldDiff = os.path.join(oldD, oldDiff)
#                 newBase, newD = os.path.split(newBase)
#                 newDiff = os.path.join(newD, newDiff)

#             oldDiff = os.path.join("...", oldDiff).encode(Config.UnicodeEncoding)
#             newDiff = os.path.join("...", newDiff).encode(Config.UnicodeEncoding)

#             if track.matchedWithDB:
#                 oldUri = db.sql("SELECT Uri FROM CoreTracks WHERE TrackID = ?",
#                             track["TrackID"])[0]["Uri"]
#             else:
#                 oldUri = ''

#             newUri = db_glue.pathname2sql(newName.encode(Config.UnicodeEncoding))
#             # dbChanges["Uri"] = (db_glue.pathname2sql(oldDiff)[7:], db_glue.pathname2sql(newDiff)[7:])

#         if fileChanges or dbChanges or relocated:
#             print track.name

#             if rebase:
#                 dbChanges["Uri"] = (oldUri, newUri)
#                 print "  Rebasing from %s to %s" % (oldDiff, newDiff)
#             elif relocated:
#                 dbChanges["Uri"] = (oldUri, newUri)
#                 m = "  Relocating from %s to %s" % (oldDiff, newDiff)
#                 if os.path.exists(newName):
#                     m += " (overwriting existing file)"
#                     overwritten += 1
#                 print m

#             if fileChanges:
#                 print "  File: %s" % '\n\t'.join(["%s:\t%s -> %s" % (k, v[0], v[1]) for
#                             k, v in sorted(fileChanges.items())])
#             if dbChanges and track.matchedWithDB:
#                 print "  DB:   %s" % '\n\t'.join(["%s:\t%s -> %s" % (k, v[0], v[1]) for
#                             k, v in sorted(dbChanges.items())])

#             if "BitRate" in fileChanges:
#                 print "  Reencoding from %d to %d bps" % (fileChanges["BitRate"])
#             if dbChanges and matchWithDB and track.matchedWithDB:
#                 UpdateDB(dbChanges, track["TrackID"])
#             edited += 1

#             if not test:
#                 if audio:
#                     audio.save()

#                 if track.matchedWithDB:
#                     db.commit()
                
#                 if relocated and not rebase:
#                     curName, newName = relocated
#                     newDir = os.path.dirname(newName)
#                     if not os.path.exists(newDir):
#                         os.makedirs(newDir)
#                     if os.path.exists(newName):
#                         os.remove(newName)
#                     os.rename(curName, newName)
#                     try:
#                         os.removedirs(os.path.dirname(curName))
#                     except OSError:
#                         pass

#                 if "BitRate" in fileChanges:
#                     track.encode(track["Location"],
#                                  fileChanges["BitRate"][1] / 1000)

#     status = "\n%d/%d edited" % (edited, totalCount)
#     if overwritten:
#         status = "%s (%s overwritten)" % (status, overwritten)
#     print status

# # Converts a SQL/track list representation to a mutagen-style EasyMP3 object.
# def TrackToMutagenDict(d):
#     audio = dict()

#     for tag in ["Title", "Artist", "Album", "Genre", "Duration", "AlbumArtist", "Year"]:
#         value = d.get(tag, None)
#         if value is None:
#             continue
#         if not isinstance(value, unicode):
#             value = unicode(str(value))
#         audio[Track.SQLToMutagen[tag]] = value

#     countKeys = (("TrackNumber", "TrackCount"), ("Disc", "DiscCount"))
#     for numKey, countKey in countKeys:
#         if d.get(numKey, None) is not None:
#             numVal = d[numKey]
#             newKey = Track.SQLToMutagen[numKey]
#             if d[countKey] is not None:
#                 countVal = d[countKey]
#                 audio[newKey] = u"%d/%d" % (numVal, countVal)
#             else:
#                 audio[newKey] = unicode(str(numVal))

#     return audio

# # Evaluates changes to be made to an MP3
# def SyncTrackToFile(track, _changes, audio, nullAlbumArtist):
#     mDict = TrackToMutagenDict(track)
#     audio["length"] = str(int(audio.info.length * 1000))
#     _changes = TrackToMutagenDict(_changes)
#     changes = dict()
#     for k, v in mDict.items():
#         if k in _changes:
#             newVal = _changes[k]
#         else:
#             newVal = v
#         curVal = audio.get(k, [None])[0]
#         if k not in audio or curVal != newVal:
#             #Exceptions
#             if k == "length":
#                 continue # Can't change length in track
#             elif nullAlbumArtist and k == "albumartistsort":
#                 continue

#             changes[k] = (curVal, newVal)
#             audio[k] = v
#     for k, v in _changes.items():
#         if k not in changes:
#             changes[k] = (None, v)
#             audio[k] = v
#     if abs(track["BitRate"] * 1000 - audio.info.bitrate) > 1000:
#         changes["BitRate"] = (audio.info.bitrate, track["BitRate"] * 1000)
#     return changes

# # Evaluates changes to be made to a DB entry
# def SyncTrackToDB(track, _changes, curTrackID=None):
#     if curTrackID is None:
#         curTrackID = track["TrackID"]
#     curTrack = db.sql(Track.selectStmt % "TrackID = ?", curTrackID)[0]
#     changes = dict()
#     for k, v in track.items():
#         curVal = curTrack.get(k, None)
#         if k in _changes:
#             v = _changes[k]
#         if k not in curTrack or curVal != v:
#             #Exceptions
#             if k.startswith("Disc") and v is None and curVal == 0:
#                 continue
#             elif k == "Location":# or k == "Uri":
#                 continue
#             elif k == "Duration" and curVal is not None and v is not None:
#                 curValInt, newValInt = int(curVal), int(v)
#                 if abs(newValInt - curValInt) <= LENGTH_UPDATE_THRESHOLD_MS:
#                     continue

#             changes[k] = (curVal, v)
#     for k, v in _changes.items():
#         if k not in changes:
#             changes[k] = (None, v)
#     return changes

# # Updates the DB with the changes from SyncTrackToDB
# def UpdateDB(changes, trackID):
#     tracksChanges = {"TrackID": trackID}
#     for k, v in changes.items():
#         if k not in ("Album", "AlbumArtist", "Artist"):
#             tracksChanges[k] = v[1]

#     if "Title" in tracksChanges:
#         newTitle = tracksChanges["Title"]
#         titleSort, titleSortKey = KeyGen.nameToKey(newTitle)
#         tracksChanges["TitleLowered"] = newTitle.lower()
#         tracksChanges["TitleSort"] = titleSort
#         tracksChanges["TitleSortKey"] = titleSortKey

#     if "Album" in changes:
#         newAlbum = changes["Album"][1]
#         rows = db.sql("SELECT AlbumID FROM CoreAlbums WHERE Title = ?", newAlbum)
#         if len(rows) == 0:
#             print "* WARNING: Album %r not found. Adding new albums not currently supported. " \
#                     "Please change the album manually." % newAlbum
#         else:
#             tracksChanges["AlbumID"] = rows[0]["AlbumID"]

#     if "AlbumArtist" in changes:
#         print "* WARNING: Changing album artists is not currently supported. " \
#                 "Please change the album artist manually."

#     if "Artist" in changes:
#         newArtist = changes["Artist"][1]
#         rows = db.sql("SELECT ArtistID FROM CoreArtists WHERE Name = ?", newArtist)
#         if len(rows) == 0:
#             print "* WARNING: Artist %r not found. Adding new artists not currently supported. " \
#                     "Please change the artist manually." % newArtist
#         else:
#             tracksChanges["ArtistID"] = rows[0]["ArtistID"]
#     if len(tracksChanges) > 1:
#         db.sql("UPDATE CoreTracks SET %s WHERE TrackID = :TrackID" % 
#             ', '.join(["%s = :%s" % (k, k) for k in tracksChanges if k != "TrackID"]), **tracksChanges)

# # Views tracks
# def View(tracks, useRepr=False):
#     for audio in tracks:
#         if useRepr:
#             print repr(audio)
#         else:
#             print str(audio)

# def getTracks(parser, args, integrateChanges=False):

#     if args.help_tags:
#         print '\n'.join(sorted(EasyID3.valid_keys.keys()))
#         raise SystemExit
#     elif args.source is None:
#         print "ERROR: Must specify metadata data source"
#         parser.print_help()
#         raise SystemExit

#     if args.files:
#         fNames = list()
#         for f in args.files:
#             fNames.extend(Util.expandPath(f))
#     else:
#         if getattr(args, "action", '') == "edit":
#             print "ERROR: Must specify files to edit."
#             parser.print_help()
#             return
#         fNames = None

#     extraDict = dict(args.extra)
#     for k, v in extraDict.items():
#         extraDict[k] = Util.convertStrValue(v)
#     kwargs = {}
#     if integrateChanges:
#         kwargs.update(extraDict)

#     if args.source in ("db", "files", "dbonly", "filesonly"):
#         if not args.matchwithdb or args.source == "filesonly":
#             sources = [TRACKLIST, FILE]
#         elif args.source == "dbonly":
#             sources = [TRACKLIST, DB]
#         elif args.source == "files":
#             sources = [TRACKLIST, FILE, DB]
#         elif args.source == "db":
#             sources = [TRACKLIST, DB, FILE]
#         tracks = [Track.Track(sources, fn, **kwargs) for fn in fNames]
#         fNames = None
#     else:
#         tl = ParseTables.getAugmentedTrackList(args.source, **kwargs)
#         sources = [Track.TRACKLIST]
#         if args.matchwithdb:
#             sources.append(Track.DB)
#         tracks = [Track.Track(sources, None, **t) for t in tl]

#     tracks.sort(key=operator.itemgetter("Artist", "Album", "Disc", "TrackNumber"))

#     if integrateChanges:
#         return fNames, tracks
#     else:
#         return fNames, tracks, extraDict





def sync_tracks(source_tracks, dest_tracks, test):
    matched, unmatched_sources, unmatched_dests = match_metadata_to_tracks(source_tracks, dest_tracks)

    for source_track, dest_track in matched:
        if getattr(source_track, 'location') == dest_track.location:
            # Both tracks have the same base file--we are copying from the file to the db or vice versa
            source_md = source_track.default_metadata
            if isinstance(source_md, MusicFile):
                dest_mds = [(dest_track.db, 'db')]
            else:
                dest_mds = [(dest_track.mfile, 'mfile')]
        else:
            source_md = source_track
            dest_mds = list()
            for name in ('db', 'mfile'):
                md = getattr(dest_track, name)
                if md is not None:
                    dest_mds.append((md, name))

        track_changes = dict()
        for md, name in dest_mds:
            md.update(source_md)
            changes = md.changes()
            if changes:
                track_changes[name] = changes
        if track_changes:
            print(dest_track.location)
            for name, changes in sorted(track_changes.items()):
                md = getattr(dest_track, name)
                print('    %s' % name)
                for k, v in changes:
                    print('        %s: %s -> %s' % (k, getattr(md, name, None), v))

        if not test:
            dest_track.save()

    for track in unmatched_sources:
        print('%s NOT MATCHED' % track.location)
        print()

    print('%d/%d matched' % (len(matched), len(source_tracks)))

    if not test:
        DefaultDb().commit()

def copy_metadata(source_tracks, dest_strs, test):
    for dest_str in dest_strs:
        print('---\n%s\n---\n' % dest_str)
        if os.path.splitext(dest_str.lower())[1] in tracklist_exts:
            print('Saving tracks to %s' % (dest_str))
            if not test:
                write_tracklist(dest_str, source_tracks)
        else:
            dest_tracks, dest_type = parse_metadata_string(dest_str)
            if dest_type == 'web':
                raise ValueError('Cannot save tracks to a URL')

            sync_tracks(source_tracks, dest_tracks, test)

def parse_metadata_string(s):
    if url_re.match(s):
        metadatas = parse_tracklist_from_url(s)
        tracks = [Track(other=m) for m in metadatas]
        return tracks, 'web'

    default_metadata = None
    if s.startswith('db:' or 'mfile:'):
        default_metadata, s = s.split(':', 1)
    if os.path.exists(s):
        if os.path.isfile(s):
            if os.path.splitext(s.lower())[1] in tracklist_exts:
                metadatas = read_tracklist(s)
                tracks = [Track(other=m) for m in metadatas]
                return tracks, 'tracklist'
            else:
                fnames = [s]
        else: # Directory
            fnames = get_fnames(s)
    else: # Could be a glob
        fnames = get_fnames(s)

    return [Track.from_file(fname, default_metadata=default_metadata) for fname in fnames], 'files'

def main():
    progDesc = """Copy music metadata from one source to one or more destinations."""

    parser = argparse.ArgumentParser(description=progDesc)
    # parser.add_argument('-r', "--use-repr", action="store_true",
    #                     help="When viewing, use repr() to display rather than str().")
    # parser.add_argument("--noreloc", dest="reloc", action="store_false",
    #                     help="Disable automatic relocation of files.")
    # parser.add_argument("--rebase", help="Change a track's source to this location.")
    # parser.add_argument("--suffix")
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                        help="Specify extra data fields for tracks loaded from an external source.")
    parser.add_argument("source",
        help="The source to get metadata from (db, files, or a location of a track list).")
    parser.add_argument("dests", nargs='*', help="The files being edited, if any.")

    args = parser.parse_args()

    source_tracks, source_type = parse_metadata_string(args.source)

    extra_args = dict([(k, convert_str_value(v)) for k, v in args.extra])
    for t in source_tracks:
        for k, v in extra_args.items():
            setattr(t.default_metadata, k, v)

        print(t.format())

    # fNames, tracks, changes = getTracks(parser, args)
    # if args.rebase:
    #     assert len(tracks) == 1, "Can only rebase 1 track at a time"
    #     assert os.path.exists(args.rebase), "Must rebase to an existing file"

    if len(args.dests) > 0:
        print()
        copy_metadata(source_tracks, args.dests, args.test)

if __name__ == "__main__":
    main()