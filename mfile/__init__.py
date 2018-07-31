import os.path

from .mp3 import MP3File
from .ogg import OggFile

mapping = {'.mp3': MP3File,
           '.ogg': OggFile}

def mfile(fname):
    _, ext = os.path.splitext(fname)
    ext = ext.lower()
    if ext in mapping:
        return mapping[ext](fname)
    
    raise KeyError(ext)
