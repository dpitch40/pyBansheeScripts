import abc
import shutil
import os.path
import os

from core.file_based import FileBased

class MusicFile(FileBased):

    sigil = '%'
    ext = ''

    """Base class for metadata derived from a music file."""

    all_keys = FileBased.all_keys + ('bitrate', # Integer number of bits/second
                                     'location', # File location
                                     'fsize') # File size in bytes
    read_only_keys = ('length',
                      'location',
                      'bitrate',
                      'fsize')

    format_lines = [('title', 'album', 'album_artist', 'artist', 'performer', 'genre', 'grouping'),
                    ('tnc', 'dnc', 'year', 'length', 'bitrate', 'fsize'),
                    ('location',)]

    def __init__(self, fname, d):
        self.fname = fname
        super(MusicFile, self).__init__(d)

    # Functionality

    def refresh(self):
        """Refreshes this MusicFile from the file, e.g. if it has been modified
           by an external program."""
        self.rebase(self.fname)

    def move(self, new_fname):
        """Moves this MusicFile to a new location."""
        d = os.path.dirname(new_fname)
        if not os.path.exists(d):
            os.makedirs(d)
        shutil.move(self.fname, new_fname)
        self.rebase(new_fname)

    # Descriptor

    @property
    def location(self):
        return self.fname

    @property
    def fsize(self):
        try:
            return os.path.getsize(self.location)
        except FileNotFoundError:
            return None

    # To be overridden

    def rebase(self, new_fname):
        """Rebases this MusicFile on a new file location."""
        raise NotImplementedError

    def create_decoder(self):
        """Returns a subprocess for decoding this file, outputting to stdout."""
        raise NotImplementedError

    @classmethod
    def create_encoder(self, fname, metadata, bitrate):
        """Returns a subprocess for encoding data from stdin to the specified filename."""
        raise NotImplementedError
