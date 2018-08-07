import abc
import shutil
import os.path

from core.file_based import FileBased

class MusicFile(FileBased):

    sigil = '%'
    ext = ''

    """Base class for metadata derived from a music file."""

    all_keys = FileBased.all_keys + ('bitrate', # Integer number of bits/second
                                     'location') # File location
    read_only_keys = ('length',
                      'location',
                      'bitrate')

    format_lines = ['%(title)s - %(artist)s - %(album)s (%(album_artist)s) - %(genre)s',
                    '%(tn)s/%(tc)s, %(dn)s/%(dc)s\t%(year)s\t%(length)ss\t%(bitrate)skbps',
                    '%(location)s']

    def __init__(self, fname, d):
        self.fname = fname
        super(MusicFile, self).__init__(d)

    # Formatting

    def _format_bitrate(self, bitrate):
        bitrate = bitrate / 1000
        if bitrate % 1 == 0:
            bitrate = int(bitrate)
        return bitrate

    # Functionality

    def refresh(self):
        """Refreshes this MusicFile from the file, e.g. if it has been modified
           by an external program."""
        self.rebase(self.fname)

    def move(self, new_fname):
        """Moves this MusicFile to a new location."""
        shutil.move(self.fname, new_fname)
        self.rebase(new_fname)

    # Descriptor

    @property
    def location(self):
        return self.fname

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
