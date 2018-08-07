import os
import os.path
import argparse
import re
from mfile import open_music_file

# from mutagen.mp3 import MP3
# from EasyID3Custom import EasyID3Custom as EasyID3

from core.util import get_fnames
import config
from parse import get_track_list
from track import Track

http_re = re.compile(r'^https?://', flags=re.IGNORECASE)

# def Rip(tracks, test, bitRate, number, inputLocs):
#     inputDirMapping = dict()
#     for c in Util.expandPath(inputLocs):
#         m = Metadata.trackNumRe.match(os.path.basename(c))
#         if m:
#             g = m.groups()
#             if g[0]:
#                 inputDirMapping[(int(g[0]), int(g[1]))] = c
#             else:
#                 inputDirMapping[int(g[1])] = c
#     matched = 0
#     minDisc = min(track.get("Disc", 100) for track in tracks)
#     if minDisc == 100:
#         minDisc = None
#     for track in tracks:
#         if "TrackNumber" not in track:
#             print "ERROR: Track %s must have a track number" % (track.name)
#             continue
#         else:
#             if track.get("Disc", None) is not None:
#                 key = (track["Disc"], track["TrackNumber"])
#                 if minDisc is None or minDisc == 1:
#                     altKey = None
#                 else:
#                     altKey = (1, track["TrackNumber"])
#             else:
#                 key = track["TrackNumber"]
#                 altKey = (1, track["TrackNumber"])
#         if key in inputDirMapping:
#             inputFile = inputDirMapping[key]
#         elif altKey in inputDirMapping:
#             inputFile = inputDirMapping[altKey]
#         else:
#             print "ERROR: Could not find input track %s" % str(key)
#             continue
#         print inputFile
#         matched += RipTrack(track, test, bitRate, number, inputFile)

#     print "%d/%d matched" % (matched, len(tracks))

#     if not test:
#         db.commit()

# def RipTrack(track, test, bitRate, number, inputFile):

#     fullName = track.getDestName(Metadata.musicDir)
#     prevName = track.get("Location", None)
#     if prevName is not None:
#         prevName = prevName.encode(Config.UnicodeEncoding)

#     matched = int(prevName is not None and prevName == fullName)
#     if matched:
#         actions = ["%-2d  >>>" % track["TrackNumber"]]
#     else:
#         actions = ["%-2d" % track["TrackNumber"]]
#         print '\nExisting\t%s (%s) !=\nNew\t\t%s (%s)' % \
#                 (prevName, type(prevName).__name__, fullName, type(fullName).__name__)

#     fullNameSQL = db_glue.pathname2sql(fullName)

#     if track.matchedWithDB:
#         rows = db.sql("SELECT BitRate, Uri FROM CoreTracks WHERE TrackID = ?", track["TrackID"])
#         row = rows[0]
#         changes = list()
#         if row["BitRate"] != bitRate:
#             changes.append(("BitRate", bitRate))
#         if row["Uri"] != fullNameSQL:
#             changes.append(("Uri", fullNameSQL))
#         actions.append(', '.join(["%s = %s" % c for c in changes]))

#     # if prevName is None:
#     if inputFile:
#         track["Location"] = inputFile
#     print "%s\n    %s\n    Dest: %s" % ('\t'.join(actions), '\n'.join(str(track).split('\n')),
#                 fullName)

#     if not test:
#         track.encode(fullName, bitRate)

#         if track.matchedWithDB:
#             fsize = os.path.getsize(fullName)
#             changes.append(("FileSize", fsize))
#             changeNames, changeVals = zip(*changes)
#             db.sql("UPDATE CoreTracks SET %s WHERE TrackID = ?" %
#                     ', '.join(["%s = ?" % cn for cn in changeNames]),
#                         *(tuple(changeVals) + (track["TrackID"],)))
#             # print "Updated database\tBitrate=%d\tFileSize=%d\tUri=%s" % (bitrate, fsize, fullNameSQL)
#     return matched

def convert():
    infile = sys.argv[1]
    in_md = mfile.open_music_file(infile)
    decoder = in_md.create_decoder()

    out_ext = sys.argv[2]
    base, in_ext = os.path.splitext(infile)
    outfile = '%s%s' % (base, out_ext)
    if in_ext.lower() == out_ext.lower() and os.path.exists(outfile):
        outfile = '%s-1%s' % (base, out_ext)
    if os.path.exists(outfile):
        os.remove(outfile)
    encoder = mfile.mapping[out_ext].create_encoder(outfile, in_md, 128)

    decodedData, errs = decoder.communicate()
    encoder.communicate(decodedData)

    encoded = mfile.open_music_file(outfile)
    print(encoded.wrapped)
    print(encoded.format())
    print(repr(encoded))


def main():
    parser = argparse.ArgumentParser(description="Transcode a set of music files.")
    parser.add_argument("-b", "--bitrate", type=int, default=config.DefaultCDBitrate,
                        help="The bitrate to encode to")
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument("input", help="Specify the files/directory of files to encode from.")
    parser.add_argument('output_or_metadata', help='Either the files/directory of files to overwrite, '
                            'or the location of metadata describing the tracks.')

    args = parser.parse_args()

    input_files = [open_music_file(fname) for fname in get_fnames(args.input)]

    output_tracks = list()
    oom = args.output_or_metadata
    if os.path.isfile(oom) or http_re.match(oom):
        output_tracks = [Track.from_metadata(m) for m in get_track_list(oom)]
    else:
        output_tracks = [Track.from_file(fname) for fname in get_fnames(oom)]

    for f in input_files:
        print(f.format())
    print()
    for t in output_tracks:
        print(t.format())

    # Rip(input_files, args.test, args.bitrate, args.input)

if __name__ == "__main__":
    main()