import os.path

from .mp3 import MP3File
from .ogg import OggFile
from .flac import FlacFile
from .m4a import M4AFile
from .wav import WaveFile

mapping = dict([(f.ext, f) for f in (MP3File, OggFile, FlacFile, M4AFile, WaveFile)])

def open_music_file(fname):
    if not os.path.exists(fname):
        return None

    _, ext = os.path.splitext(fname)
    ext = ext.lower()
    if ext in mapping:
        return mapping[ext](fname)
    
    raise KeyError(ext)
