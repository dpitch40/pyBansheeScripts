import os.path

from .mp3 import MP3File
from .ogg import OggFile
from .flac import FlacFile
from .m4a import M4AFile

mapping = dict([(f.ext, f) for f in (MP3File, OggFile, FlacFile, M4AFile)])

def open_music_file(fname):
    _, ext = os.path.splitext(fname)
    ext = ext.lower()
    if ext in mapping:
        return mapping[ext](fname)
    
    raise KeyError(ext)
