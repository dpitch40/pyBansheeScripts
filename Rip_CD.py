import Util
import os
import os.path
from mutagen.mp3 import MP3
from EasyID3Custom import EasyID3Custom as EasyID3
import re
import ParseTables
import db_glue
import operator
import argparse
import Metadata
import Track
import Config

db = db_glue.new(db_glue.defaultLoc)

CD_DRIVE = Config.CDDriveLoc

def Rip(tracks, test, bitRate, number, inputLocs):
    inputDirMapping = dict()
    for c in Util.expandPath(inputLocs):
        m = Metadata.trackNumRe.match(os.path.basename(c))
        if m:
            g = m.groups()
            if g[0]:
                inputDirMapping[(int(g[0]), int(g[1]))] = c
            else:
                inputDirMapping[int(g[1])] = c
    matched = 0
    minDisc = min(track.get("Disc", 100) for track in tracks)
    if minDisc == 100:
        minDisc = None
    for track in tracks:
        if "TrackNumber" not in track:
            print "ERROR: Track %s must have a track number" % (track.name)
            continue
        else:
            if track.get("Disc", None) is not None:
                key = (track["Disc"], track["TrackNumber"])
                if minDisc is None or minDisc == 1:
                    altKey = None
                else:
                    altKey = (1, track["TrackNumber"])
            else:
                key = track["TrackNumber"]
                altKey = (1, track["TrackNumber"])
        if key in inputDirMapping:
            inputFile = inputDirMapping[key]
        elif altKey in inputDirMapping:
            inputFile = inputDirMapping[altKey]
        else:
            print "ERROR: Could not find input track %s" % str(key)
            continue
        print inputFile
        matched += RipTrack(track, test, bitRate, number, inputFile)

    print "%d/%d matched" % (matched, len(tracks))

    if not test:
        db.commit()

def RipTrack(track, test, bitRate, number, inputFile):

    fullName = track.getDestName(Metadata.musicDir)
    prevName = track.get("Location", None)
    if prevName is not None:
        prevName = prevName.encode(Config.UnicodeEncoding)

    matched = int(prevName is not None and prevName == fullName)
    if matched:
        actions = ["%-2d  >>>" % track["TrackNumber"]]
    else:
        actions = ["%-2d" % track["TrackNumber"]]
        print '\nExisting\t%s (%s) !=\nNew\t\t%s (%s)' % \
                (prevName, type(prevName).__name__, fullName, type(fullName).__name__)

    fullNameSQL = db_glue.pathname2sql(fullName)

    if track.matchedWithDB:
        rows = db.sql("SELECT BitRate, Uri FROM CoreTracks WHERE TrackID = ?", track["TrackID"])
        row = rows[0]
        changes = list()
        if row["BitRate"] != bitRate:
            changes.append(("BitRate", bitRate))
        if row["Uri"] != fullNameSQL:
            changes.append(("Uri", fullNameSQL))
        actions.append(', '.join(["%s = %s" % c for c in changes]))

    # if prevName is None:
    if inputFile:
        track["Location"] = inputFile
    print "%s\n    %s\n    Dest: %s" % ('\t'.join(actions), '\n'.join(str(track).split('\n')),
                fullName)

    if not test:
        track.encode(fullName, bitRate)

        if track.matchedWithDB:
            fsize = os.path.getsize(fullName)
            changes.append(("FileSize", fsize))
            changeNames, changeVals = zip(*changes)
            db.sql("UPDATE CoreTracks SET %s WHERE TrackID = ?" %
                    ', '.join(["%s = ?" % cn for cn in changeNames]),
                        *(tuple(changeVals) + (track["TrackID"],)))
            # print "Updated database\tBitrate=%d\tFileSize=%d\tUri=%s" % (bitrate, fsize, fullNameSQL)
    return matched


def main():
    parser = argparse.ArgumentParser(description="Encode a collection of lossless audio "
        "files (e.g. the contents of a CD), copying them to your music folder.")
    parser.add_argument("-b", "--bitrate", type=int, default=256,
                        help="The bitrate to encode to")
    parser.add_argument('-n', "--nonumber", action="store_false", dest="number",
                   help="Do not add track/disc numbers to encoded file names.")
    parser.add_argument("--input", default=CD_DRIVE,
        help="Specify the lossless files to encode from. (Defaults to your CD drive)")
    Metadata.addDefaultArguments(parser)

    args = parser.parse_args()

    fNames, tracks = Metadata.getTracks(parser, args, integrateChanges=True)

    Rip(tracks, args.test, args.bitrate, args.number, args.input)

if __name__ == "__main__":
    main()