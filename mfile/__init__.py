import os.path

from .mp3 import MP3File
from .ogg import OggFile
from .flac import FlacFile

mapping = {'.mp3': MP3File,
           '.ogg': OggFile,
           '.flac': FlacFile}

def open_music_file(fname):
    _, ext = os.path.splitext(fname)
    ext = ext.lower()
    if ext in mapping:
        return mapping[ext](fname)
    
    raise KeyError(ext)
