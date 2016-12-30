# Module containing utility functions for use by other modules

import os
import string
import os.path
import subprocess
import operator
import glob
import re

from mutagen.mp3 import MP3
from EasyID3Custom import EasyID3Custom as EasyID3

forbiddenChars = ':;/\\!?*"<>|'
forbiddenDirChars = ':;\\!?*"<>|'
translatetable = [chr(i) for i in xrange(0, 256)]
for c in string.punctuation:
    translatetable[ord(c)] = '_'
translatetable = ''.join(translatetable)

forbiddentable = [chr(i) for i in xrange(0, 256)]
for c in forbiddenChars:
    forbiddentable[ord(c)] = '_'
forbiddentable = ''.join(forbiddentable)

# Takes the intersection of two lists of filenames: returns the files exclusive to the first,
# the common names, and the names exclusive to the second.
def compare_filesets(filelist1, filelist2):
    #Turn all to lowercase and remove periods os.path.exists doesn't care about
    #these
    def demote(s):
        prevDir, fName = os.path.split(s)
        prevDir, artistDir = os.path.split(prevDir)
        albumDir = os.path.basename(prevDir)
        fName, ext = os.path.splitext(fName)
        return os.path.join(albumDir, artistDir, fName).lower().replace('.', '')
    
    translatedfiles1 = dict(zip(map(demote, filelist1), filelist1))
    translatedfiles2 = dict(zip(map(demote, filelist2), filelist2))
    on1not2 = [translatedfiles1[f] for f in 
        set(translatedfiles1.keys()) - set(translatedfiles2.keys())]
    on2not1 = [translatedfiles2[f] for f in 
        set(translatedfiles2.keys()) - set(translatedfiles1.keys())]
    common = [translatedfiles1[f] for f in 
        set(translatedfiles1.keys()) & set(translatedfiles2.keys())]
    return on1not2, common, on2not1

# Encodes the file at fname to an MP3 file at dest, using lame, at the specified bitrate.
# 0 <= qual <= 9; lower is better quality (but longer encode time)
def mp3encode(fname, dest, title,
              artist=None, album=None, year=None, genre=None,
              trackno=None, trackcount=None, disc=None, disccount=None,
              bitrate=128, qual=2):
    
    destDir = os.path.dirname(dest)
    if not os.path.exists(destDir):
        os.makedirs(destDir)

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
        # Special case for flac files
        decoder = subprocess.Popen(["flac", "--decode", "--silent", "--stdout", fname],
                        stdout=subprocess.PIPE)
        decodedData, errs = decoder.communicate()
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
# basedir is the top-level directory (assumed not to contain slashes)
# elements is the list of path elementst hat may contain slashes; artist, album, title, etc.
def filterPathElements(baseDir, elements):
    # Remove forward slashes in the path elements
    elements = [element.replace('/', '_') for element in elements]
    return filterFname(os.path.join(baseDir, *elements))

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