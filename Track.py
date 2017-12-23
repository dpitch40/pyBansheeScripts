# Defines a flexible wrapper class for a single audio track, pulling together metadata
# from multiple sources

import os
import os.path
import string

from mutagen.mp3 import MP3
from EasyID3Custom import EasyID3Custom as EasyID3
from mutagen.oggvorbis import OggVorbis

import db_glue
import Util
import Config

global db

groupArtists = Config.GroupArtists
numberTracks = Config.NumberTracks
ignoreThe = Config.IgnoreThe
groupSingletons = Config.GroupSingletons

# Statement template used to pull everything useful from the SQL database
selectStmt = """SELECT ct.TrackID AS TrackID, ct.Title AS Title, ca.Name AS Artist,
cl.Title AS Album, cl.ArtistName AS AlbumArtist, ct.Genre AS Genre, ct.Year AS Year,
ct.TrackNumber AS TrackNumber, ct.TrackCount AS TrackCount, ct.Disc AS Disc, ct.DiscCount AS DiscCount,
ct.Uri AS Uri, ct.Duration AS Duration, ct.BitRate AS BitRate, ct.FileSize AS FileSize
FROM CoreTracks ct
JOIN CoreAlbums cl ON ct.AlbumID = cl.AlbumID, CoreArtists ca ON ct.ArtistID = ca.ArtistID
WHERE %s"""

# Source codes
DB = 0
FILE = 1
TRACKLIST = 2

# Used for creating a string representation of the Track object
viewKeys = ["Title",
            "Artist",
            "Album",
            "AlbumArtist",
            "Genre",
            "Year"]
metaViewKeys = ["TrackID",
                "BitRate",
                "FileSize",
                "Location"]
# All keys in the Track object
allKeys = ["TrackID", # int
           "Title", # str
           "Artist", # str
           "Album", # str
           "AlbumArtist", # str
           "Genre", # str
           "Year", # int
           "TrackNumber", # int
           "TrackCount", # int
           "Disc", # int
           "DiscCount", # int
           "Uri", # str
           "Duration", # int
           "BitRate", # int
           "FileSize", # int
           "Location"] # str

# Mapping from mutagen EasyID3 tag names to SQLite ones
fieldNameMapping = [("title", "Title"),
                    ("artist", "Artist"),
                    ("album", "Album"),
                    ("albumartistsort", "AlbumArtist"),
                    ("genre", "Genre"),
                    ("date", "Year"),
                    ("tracknumber", "TrackNumber"),
                    ("discnumber", "Disc"),
                    ("length", "Duration")]
mutagenToSQL = dict(fieldNameMapping)
SQLToMutagen = dict([(t2, t1) for t1, t2 in fieldNameMapping])
# Correction for OGG Vorbis
mutagenToSQL["part of a set"] = "Disc"

moduleDebug = False

supportedExtensions = (".mp3", ".ogg")
def AudioFileInterface(fName):
    ext = os.path.splitext(fName)[1].lower()
    if ext == ".mp3":
        audio = MP3(fName, ID3=EasyID3)
    elif ext == ".ogg":
        audio = OggVorbis(fName)
    else:
        raise ValueError, "Unsupported extension: %s" % ext
    return audio

# class AudioFileInterface(dict):
#     supportedExtensions = (".mp3", ".ogg")

#     def __init__(self, fName):
#         dict.__init__(self)
#         ext = os.path.splitext(fName)[1].lower()
#         if ext == ".mp3":
#             audio = MP3(fName, ID3=EasyID3)
#         elif ext == ".ogg":
#             audio = OggVorbis(fName)
#         else:
#             raise ValueError, "Unsupported extension: %s" % ext
#         dict.__setattr__(self, "audio", audio)

#     def __getattr__(self, name):
#         try:
#             return getattr(self.audio, name)
#         except AttributeError:
#             raise

#     def __setattr__(self, name, val):
#         return setattr(self.audio, name)

class Track(object):
    _slots__ = ["audio",
                "matchedWithDB",
                "matchedWithFile",
                "name",

                "extraData"] + allKeys

    # Initializes the Track object.
    #   sources can contain any of the source codes enumerated above (DB, FILE, TRACKLIST).
    # It determines the sources from which this Track will attempt to draw metadata,
    # and their order of priority.
    #   fName is the full path to the file associated with this Track (if any).
    #   kwargs can contain any of the keys in allKeys
    def __init__(self, sources, fName=None, isSingleton=False, **kwargs):

        self.audio = None
        self.matchedWithDB = False
        self.matchedWithFile = False
        self.isSingleton = isSingleton
        self.extraData = dict()
        self.ext = None
        if fName is not None and os.path.exists(fName):
            self.ext = os.path.splitext(fName)[1].lower()

        # Disallow drawing from file for non-MP3 files (possible area of expansion?)
        if self.ext not in supportedExtensions and FILE in sources:
            sources.remove(FILE)

        for source in sources:
            resultDict = dict()
            if source == DB:
                trackID = kwargs.get("TrackID")
                # if fName is None and trackID is None:
                #     raise ValueError, "Cannot match track with DB without a file name " \
                #             "or TrackID"
                resultDict = self._fromDB(fName, trackID, kwargs)
            elif source == FILE:
                if fName is None:
                    raise ValueError, "Cannot pull data from file without a file name"
                resultDict = self._fromFile(fName)
            elif source == TRACKLIST:
                resultDict = self._fromTrackList(kwargs)
            Util.cautiousUpdate(self, resultDict, True)

        if TRACKLIST in sources:
            for k, v in kwargs.items():
                if k in allKeys and v is None:
                    self[k] = v

        if self.ext is None and self["Location"] is not None and \
            os.path.exists(self["Location"]):
            self.ext = os.path.splitext(self["Location"])[1]

        # Get name
        title = self["Title"]
        if title is not None:
            self.name = title
        else:
            self.name = "Unknown Track"

        # Fix disc numbers
        for k in ("TrackNumber", "TrackCount", "Disc", "DiscCount"):
            if k in self and self[k] in (0, None):
                del self[k]
        if self["AlbumArtist"] is None:
            self["AlbumArtist"] = self["Artist"]

    # Initializes from an MP3 file
    def _fromFile(self, fName):
        Util.debug("Initializing from fille: %s" % fName, moduleDebug)

        audio = AudioFileInterface(fName)

        # Converts a mutagen-style EasyMP3 object to the SQL/track list representation.
        resultDict = dict()
        for key, newKey in fieldNameMapping:
            if key in audio:
                resultDict[newKey] = audio[key][0]

        # Convert integer keys
        for key in ("Year", "Duration"):
            if resultDict.get(key, None) is not None and resultDict[key] != '':
                resultDict[key] = int(resultDict[key])

        # Convert count keys (with a number and count field)
        countKeys = (("TrackNumber", "TrackCount"), ("Disc", "DiscCount"))
        for numKey, countKey in countKeys:
            if resultDict.get(numKey, None) is not None:
                value = resultDict[numKey]
                if '/' in value:
                    resultDict[numKey], resultDict[countKey] = map(int, value.split('/'))
                else:
                    resultDict[numKey] = int(value)

        Util.cautiousUpdate(resultDict, BasicMetadata(audio))
        resultDict["Location"] = fName.decode(Config.UnicodeEncoding)
        self.matchedWithFile = True
        self.audio = audio
        return resultDict

    # Initializes from the SQL database
    def _fromDB(self, fName, trackID=None, kwargs=dict()):
        Util.debug("Initializing from DB (#%s): %s" % (trackID, fName), moduleDebug)
        audio = None
        resultDict = dict()
        if fName:
            ext = os.path.splitext(fName)[1].lower()
        else:
            ext = None
        
        # Find track in DB
        if trackID:
            rows = db.sql(selectStmt % "ct.TrackID = ?", trackID)
        else:
            rows = list()
            # First try to match by URI, then by artist/album/title
            if fName:
                uri = db_glue.pathname2sql(fName)
                rows = db.sql(selectStmt % "ct.Uri = ?", uri)
            if not rows:
                artist = kwargs.get("Artist", '')
                album = kwargs.get("Album", '')
                title = kwargs.get("Title", '')
                if fName and ext in supportedExtensions:
                    # Initialize MP3 object
                    audio = AudioFileInterface(fName)
                    if "artist" in audio:
                        artist = audio["artist"][0]
                    if "album" in audio:
                        album = audio["album"][0]
                    if "title" in audio:
                        title = audio["title"][0]
                rows = db.sql(selectStmt % "ca.Name = ? AND cl.Title = ? AND ct.Title = ?",
                            artist, album, title)

        self.matchedWithDB = len(rows) > 0
        if self.matchedWithDB:
            resultDict = rows[0]
            resultDict["Location"] = db_glue.sql2pathname(resultDict["Uri"].encode("ascii"))
            resultDict["Location"] = resultDict["Location"].decode(Config.UnicodeEncoding)
            Util.debug("Setting location from DB: %s" % resultDict["Location"], moduleDebug)
        else:
            if audio:
                resultDict = BasicMetadata(audio)
                if audio is None and ext in supportedExtensions:
                    audio = AudioFileInterface(fName)
            if fName:
                resultDict["Location"] = fName.decode(Config.UnicodeEncoding)
        self.audio = audio

        return resultDict

    # Initializes from a row in a track list from ParseTables
    def _fromTrackList(self, row):
        Util.debug("Initializing from tracklist: %r" % row, moduleDebug)

        newRow = dict()
        for k, v in row.items():
            # Duration is inaccurate from a track list
            if k in allKeys and k != "Duration":
                newRow[k] = v

        return newRow

    # Convenience methods to recreate the old API
    @classmethod
    def fromDB(cls, fName=None, **kwargs):
        return cls([DB, FILE, TRACKLIST], fName, **kwargs)
    @classmethod
    def fromFile(cls, fName=None, **kwargs):
        return cls([FILE, DB, TRACKLIST], fName, **kwargs)
    @classmethod
    def fromTrackList(cls, kwargs):
        return cls([TRACKLIST], None, **kwargs)

    # Dict mockup methods
    def _checkKey(self, key, allowExtraKeys=False):
        if key not in allKeys and (not allowExtraKeys or key not in self.extraData):
            raise KeyError, "Invalid Track key: %r" % key
    def __getitem__(self, key):
        self._checkKey(key, True)
        if key in self.extraData:
            return self.extraData.get(key, None)
        else:
            return getattr(self, key, None)
    def __setitem__(self, key, value):
        self._checkKey(key)
        return setattr(self, key, value)
    def __delitem__(self, key):
        self._checkKey(key)
        return delattr(self, key)
    def __contains__(self, key):
        # self._checkKey(key)
        return hasattr(self, key)

    def __len__(self):
        count = 0
        for key in allKeys:
            if hasattr(self, key):
                count += 1
    def __iter__(self):
        return iter(allKeys)

    def get(self, key, default):
        # self._checkKey(key)
        return getattr(self, key, default)
    def keys(self):
        return [k for k in allKeys if k in self]
    def value(self):
        return [getattr(self, key) for key in self.keys()]
    def items(self):
        return [(key, getattr(self, key)) for key in self.keys()]
    def update(self, d):
        for k, v in d.items():
            if k in allKeys:
                setattr(self, k, v)

    # Pretty-printing methods
    def __str__(self):
        viewStrs = list()
        viewList = list()
        for k in viewKeys:
            if self[k] is not None:
                viewList.append("%s: %s" % (k, self[k]))
        if len(viewList) > 0:
            row = '\t'.join(viewList)
            if isinstance(row, unicode):
                row = row.encode(Config.UnicodeEncoding)
            viewStrs.append(row)
            viewList[:] = []

        if self["Duration"] is not None:
            lengthMins, lengthSecs = divmod(self["Duration"] / 1000, 60)
            viewList.append("Length: %d:%02d" % (lengthMins, lengthSecs))
        if self["TrackNumber"] is not None:
            if self["TrackCount"] is not None:
                viewList.append("Track: %(TrackNumber)d/%(TrackCount)d" % self)
            else:
                viewList.append("Track: %(TrackNumber)s" % self)
        if self["Disc"] is not None:
            if self["DiscCount"] is not None:
                viewList.append("Disc: %(Disc)d/%(DiscCount)d" % self)
            else:
                viewList.append("Disc: %(Disc)s" % self)
        if len(viewList) > 0:
            row = '\t'.join(viewList)
            if isinstance(row, unicode):
                row = row.encode(Config.UnicodeEncoding)
            viewStrs.append(row)
            viewList[:] = [] 

        for k in metaViewKeys:
            if self[k] is not None:
                viewList.append("%s: %s" % (k, self[k]))
        if len(viewList) > 0:
            row = '\t'.join(viewList)
            if isinstance(row, unicode):
                row = row.encode(Config.UnicodeEncoding)
            viewStrs.append(row)
            viewList[:] = []

        s = '\n\t'.join(viewStrs)
        if self.matchedWithDB:
            s = "*** %s" % s

        return s

    def __repr__(self):
        maxKeyLen = max(len(k) for k in self.keys())

        valStrs = list()
        for k, v in sorted(self.items()):
            if isinstance(v, unicode):
                valStrs.append("%s: %r" % (k.ljust(maxKeyLen), v.encode(Config.UnicodeEncoding)))
            else:
                valStrs.append("%s: %r" % (k.ljust(maxKeyLen), v))

        if self.matchedWithDB:
            s = "*** %s\n   {%s}" % (self.name, '\n    '.join(valStrs))
        else:
            s = "%s\n{%s}" % (self.name, '\n '.join(valStrs))
        return s

    # Output name calculation
    def getDestName(self, baseDir, ext=Config.DefaultEncodeExt, nest=True,
                    ga=None, asUnicode=False):
        if self.ext:
            ext = self.ext

        title = self["Title"]

        if self["AlbumArtist"]:
             artist = self["AlbumArtist"]
        else:
             artist = self["Artist"]
        if artist is None:
             artist = "Unknown Artist"

        album = self["Album"]
        if album is None:
             album = "Unknown Album"

        if numberTracks:
            trackNum = self["TrackNumber"]
            discNum = self["Disc"]
            if trackNum:
                if discNum:
                    tn = "%d-%02d " % (discNum, trackNum)
                else:
                    tn = "%02d " % trackNum
            else:
                tn = ''
        else:
            tn = ''

        singleton = self.isSingleton and groupSingletons
        if ga is None:
            ga = groupArtists
        if ga and not singleton:
            sortArtist = artist
            if ignoreThe and sortArtist.startswith("The "):
                sortArtist = sortArtist[4:]
            firstChar = sortArtist[0]
            if firstChar in string.ascii_letters:
                firstChar = firstChar.upper()
            else:
                firstChar = '0'
            baseDir = os.path.join(baseDir, firstChar)

        if singleton:
            pathElements = ["Singletons"]
        elif not nest:
            pathElements = []
        else:
            pathElements = [artist, album]

        result = self.condenseDest(pathElements, title, tn, ext, baseDir)
        if not asUnicode:
            result = result.encode(Config.UnicodeEncoding)
        return result

    def condenseDest(self,pathElements, fBase, tn, ext, baseDir):
        newName = self.getDestReal(pathElements, fBase, tn, ext, baseDir)

        # Make sure the name isn't too long
        maxElLen = 64
        while len(newName) > 255:
             newName = self.getDestReal([e[:maxElLen].rstrip() for e in pathElements],
                                      fBase[:maxElLen].rstrip(), tn, ext, baseDir)
             maxElLen -= 8

        return newName

    def getDestReal(self, pathElements, title, tn, ext, baseDir):

        newBase = "%s%s%s" % (tn, title, ext)
        for c in '/\\':
            newBase = newBase.replace(c, '_')
        return Util.filterPathElements(baseDir, pathElements + [newBase])

    # SMART MP3 encoding function
    # dest can be a top-level directory (in which case the filename is calculated)
    # or a file name
    def encode(self, dest, bitRate):
        if not os.path.splitext(dest)[1]: # Dest is a directory
            dest = self.getDestName(dest, nest=False)
        ext = os.path.splitext(dest)[1]
        temp = os.path.join(os.path.dirname(dest), "Temp%s" % ext)
        kwargs = {"artist": self["Artist"],
                  "album": self["Album"],
                  "year": self["Year"],
                  "genre": self["Genre"],
                  "trackno": self["TrackNumber"],
                  "trackcount": self["TrackCount"],
                  "disc": self["Disc"],
                  "disccount": self["DiscCount"]}
        # print dest
        Util.encode(self["Location"], temp, self["Title"], bitrate=bitRate, **kwargs)
        os.rename(temp, dest)

        return dest

# Extracts some basic, tag-independent metadata from an MP3 file
def BasicMetadata(audio):
    return {"Duration": int(audio.info.length * 1000),
            "BitRate": audio.info.bitrate / 1000,
            "FileSize": os.path.getsize(audio.filename),
            "Location": audio.filename,
            "Uri": db_glue.pathname2sql(audio.filename)}