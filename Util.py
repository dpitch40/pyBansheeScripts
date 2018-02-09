# Module containing utility functions for use by other modules

import os
import string
import os.path
import subprocess
import operator
import glob
import re
import time

import six
from six.moves import range

import db_glue
import Config

forbiddenChars = ':;/\\!?*"<>|'
forbiddenDirChars = ':;\\!?*"<>|'
xmlEscapedChars = "'"
translatetable = [chr(i) for i in range(0, 256)]
for c in string.punctuation:
    translatetable[ord(c)] = '_'
translatetable = ''.join(translatetable)

forbiddentable = [chr(i) for i in range(0, 256)]
for c in forbiddenChars:
    forbiddentable[ord(c)] = '_'
forbiddentable = ''.join(forbiddentable)

vorbisQuals = {-1: 45, 0: 64, 1: 80, 2: 96, 3: 112, 4: 128, 5: 160,
               6: 192, 7: 224, 8: 256, 9: 320, 10: 500}

def debug(msg, debug):
    if debug:
        six.print_("DEBUG:\t%s" % msg)

# Takes the intersection of two lists of filenames: returns the files exclusive to the first,
# the common names, and the names exclusive to the second.
def compare_filesets(filelist1, filelist2, sort=False):
    #Turn all to lowercase and remove periods os.path.exists doesn't care about
    #these
    def demote(s):
        prevDir, fName = os.path.split(s)
        prevDir, artistDir = os.path.split(prevDir)
        albumDir = os.path.basename(prevDir)
        fName, ext = os.path.splitext(fName)
        return os.path.join(albumDir, artistDir, "%s%s" % (fName, ext)).lower().replace('.', '')
    
    translatedfiles1 = dict(zip(map(demote, filelist1), filelist1))
    translatedfiles2 = dict(zip(map(demote, filelist2), filelist2))
    set1 = set(translatedfiles1.keys())
    set2 = set(translatedfiles2.keys())
    on1not2 = [translatedfiles1[f] for f in set1 - set2]
    on2not1 = [translatedfiles2[f] for f in set2 - set1]
    common = [translatedfiles1[f] for f in set1 & set2]
    if sort:
        return sorted(on1not2), sorted(common), sorted(on2not1)
    else:
        return on1not2, common, on2not1

def convertStrValue(v, convertNumbers=True):
    if v == '' or v == "None" or v is None:
        return None
    elif isinstance(v, str):
        if convertNumbers and v.isdigit():
            return int(v)
        else:
            return unicode(v, Config.UnicodeEncoding)
    else:
        return v

def encode(fName, dest, title,
           artist=None, album=None, year=None, genre=None,
           trackno=None, trackcount=None, disc=None, disccount=None,
           bitrate=Config.DefaultBitrate):
    ext = os.path.splitext(dest)[1].lower()
    if ext == ".mp3":
        func = mp3encode
    elif ext == ".ogg":
        func = oggencode
    else:
        raise ValueError("No encoder defined for %s" % ext)
    
    destDir = os.path.dirname(dest)
    if not os.path.exists(destDir):
        os.makedirs(destDir)

    func(fName, dest, title, artist, album, year, genre,
         trackno, trackcount, disc, disccount, bitrate)

# Encodes the file at fname to an MP3 file at dest, using lame, at the specified bitrate.
# 0 <= qual <= 9; lower is better quality (but longer encode time)
def mp3encode(fname, dest, title,
              artist, album, year, genre,
              trackno, trackcount, disc, disccount,
              bitrate, qual=Config.MP3Qual):

    from mutagen.mp3 import MP3
    from EasyID3Custom import EasyID3Custom as EasyID3

    # Set up arguments
    args = ["--noreplaygain", #Disable replaygain (don't want to mess up automated dynamics)
              "--silent", #silent
              "-q", "%d" % qual, # defaults to third-best (most efficient) quality
              "-b", "%d" % bitrate, #set bitrate
              '--tt', title]
    if artist:
        args.extend(['--ta', artist])
    if album:
        args.extend(['--tl', album])
    if year:
        args.extend(['--ty', str(year)])
    if trackno:
        if trackcount:
            args.extend(['--tn', '%d/%d' % (trackno, trackcount)])
        else:
            args.extend(['--tn', str(trackno)])
    if genre:
        args.extend(['--tg', genre])

    if fname.lower().endswith(".flac"):
        decodedData, errs = createFlacDecoder(fname)
        encoder = subprocess.Popen(["lame"] + args + ['-', dest], stdin=subprocess.PIPE)
        encoder.communicate(decodedData)
    else:
        subprocess.call(["lame"] + args + [fname, dest])

    # lame doesn't accept disc number/count as arguments; edit them after encoding
    if disc:
        mp3 = MP3(dest, ID3=EasyID3)
        if disccount:
            mp3["discnumber"] = "%d/%d" % (disc, disccount)
        else:
            mp3["discnumber"] = "%d" % disc
        mp3.save()

# Encodes the file at fname to an OGG Vorbis file at dest, using oggenc
# 0 <= qual <= 9; lower is better quality (but longer encode time)
def oggencode(fname, dest, title,
              artist, album, year, genre,
              trackno, trackcount, disc, disccount,
              bitrate, qual=None):

    from mutagen.oggvorbis import OggVorbisHeaderError
    from mutagen.oggvorbis import OggVorbis

    if not qual:
        qual = bitrateToVorbisQual(bitrate)
    # Set up arguments
    args = [ "--quiet", # silent
             "-q", "%d" % qual,
             '-t', title,
             "-o", dest]
    if artist:
        args.extend(['-a', artist])
    if album:
        args.extend(['-l', album])
    if year:
        args.extend(['-d', str(year)])
    if trackno:
        args.extend(['-N', str(trackno)])
    if genre:
        args.extend(['-G', genre])

    if fname.lower().endswith(".flac"):
        decodedData, errs = createFlacDecoder(fname)
        encoder = subprocess.Popen(["oggenc"] + args + ['-'], stdin=subprocess.PIPE)
        encoder.communicate(decodedData)
    elif fname.lower().endswith(".ogg"):
        decodedData, errs = createOggDecoder(fname)
        encoder = subprocess.Popen(["oggenc"] + args + ['-r', '-B', '16', '-'],
                    stdin=subprocess.PIPE)
        encoder.communicate(decodedData)
        time.sleep(0.5)
    else:
        subprocess.call(["oggenc"] + args + [fname])

    # oggenc doesn't accept disc number/count of track count as arguments;
    # edit them after encoding
    if disc or trackcount:
        ogg = OggVorbis(dest)
        if disc:
            if disccount:
                ogg["discnumber"] = ["%d/%d" % (disc, disccount)]
            else:
                ogg["discnumber"] = ["%d" % disc]
        if trackcount:
            ogg["tracknumber"] = ["%d/%d" % (trackno, trackcount)]
        try:
            ogg.save()
        except OggVorbisHeaderError:
            pass

def createFlacDecoder(fName):
    # Special case for flac files
    decoder = subprocess.Popen(["flac", "--decode", "--silent", "--stdout", fName],
                    stdout=subprocess.PIPE)
    return decoder.communicate()

def createOggDecoder(fName):
    # Special case for flac files
    decoder = subprocess.Popen(["oggdec", "--quiet", "-o", '-', '-R', '-b', '16', fName],
                    stdout=subprocess.PIPE)
    return decoder.communicate()

def bitrateToVorbisQual(bitrate):
    return max([q for q, b in sorted(vorbisQuals.items()) if b <= bitrate])

# "Sanitizes" a filename: replaces forbidden characters and ending periods in directory names
def filterFname(f):
    dirName, fName = os.path.split(f)

    for c in forbiddenDirChars: # Replace characters in dirname
        dirName = dirName.replace(c, '_')
    if dirName != '' and dirName[-1] == '.': # Period at end of directory name?
        dirName = dirName[:-1] + '_'
    if fName.startswith('.'): # initial period in filename
        fName = '_' + fName[1:]
    for c in forbiddenChars: # Replace characters in filename
        fName = fName.replace(c, '_')
    return os.path.join(dirName, fName)

# Wrapper function for filterFname that also handles the artist/album/song title
# containing forward slashes
# basedir is the top-level directory (assumed not to contain forbidden characters)
# elements is the list of path elementst hat may contain slashes; artist, album, title, etc.
def filterPathElements(baseDir, elements):
    # Remove forward slashes in the path elements
    elements = [element.replace('/', '_') for element in elements]
    return os.path.join(baseDir, filterFname(os.path.join(*elements)))

# Returns the set of file names represented by the string path
# If path is a list of filenames, reads it and returns the list
# If a directory, returns the contents of that directory
# If a file mask, returns the matching files
# Otherwise, assumes path is a file path and returns it in a list of length 1
def expandPath(path):
    if path.lower().endswith(".txt"):
        return map(operator.methodcaller("strip"), open(path, 'r').readlines())
    elif os.path.isdir(path):
        return [os.path.join(path, f) for f in os.listdir(path)]
    elif not path.startswith("http"):
        return glob.glob(path)
    else:
        return [path]

# Updates d1 with d2 for keys not in d1 (or keys in d1 that map to None if
# overwriteOnNone is True)
def cautiousUpdate(d1, d2, overwriteOnNone=False):
    for k, v in d2.items():
        if k not in d1 or (overwriteOnNone and d1[k] is None):
            d1[k] = v

def escapeXMLChars(s):
    s = s.replace('&', "&amp;")
    s = s.replace('<', "&lt;")
    s = s.replace('>', "&gt;")
    for c in xmlEscapedChars:
        s = s.replace(c, "&#%d;" % ord(c))
    return s
# Similar to db_glue.pathname2sql, but converts a pathname for a VLC playlist
def pathname2xml(path):
    base = db_glue.pathname2sql(path)

    decodeChars = ';'

    base = escapeXMLChars(base)
    for c in decodeChars:
        base = base.replace("%%%02X" % ord(c), c)

    return base