import abc
import shutil
import os.path

from core.metadata import Metadata

class MusicFile(Metadata):

    sigil = '%'
    ext = ''

    """Base class for metadata derived from a music file."""

    all_keys = Metadata.all_keys + ('bitrate', # Integer number of bits/second
                                    'location') # File location
    read_only_keys = ('length',
                      'location',
                      'bitrate')

    format_lines = ['%(title)s - %(artist)s - %(album)s (%(album_artist)s) - %(genre)s',
                    '%(tn)s/%(tc)s, %(dn)s/%(dc)s\t%(year)s\t%(length)ss\t%(bitrate)skbps',
                    '%(location)s']

    def __init__(self, fname, d):
        if os.path.splitext(fname)[1].lower() != self.ext:
            raise ValueError('Cannot open the file %s with %s' % (fname,
                                    self.__class__.__name__))
        self.fname = fname
        super(MusicFile, self).__init__(d)

    # Formatting

    def _format_bitrate(self, bitrate):
        bitrate = bitrate / 1000
        if bitrate % 1 == 0:
            bitrate = int(bitrate)
        return bitrate

    # Functionality

    def move(self, new_fname):
        """Moves this MusicFile to a new location."""
        shutil.move(self.fname, new_fname)
        self.rebase(new_fname)

    # Descriptor

    @property
    def location(self):
        return self.fname

    # To be overridden

    @abc.abstractmethod
    def rebase(self, new_fname):
        """Rebases this MusicFile on a new file location."""
        raise NotImplementedError

    @abc.abstractmethod
    def save(self):
        """Saves the metadata in described by this instance back to the music file."""
        raise NotImplementedError
