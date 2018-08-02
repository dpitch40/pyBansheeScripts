from core.metadata import Metadata
import abc

class MusicFile(abc.ABC, Metadata):

    """Base class for metadata derived from a music file."""

    all_keys = Metadata.all_keys + ('location', # File location
                                    'bitrate') # Integer number of bits/second
    read_only_keys = ('length',
                      'location',
                      'bitrate')

    def __init__(self, fname, d):
        self.fname = fname
        super(MusicFile, self).__init__(d)

    @property
    def location(self):
        return self.fname

    @abc.abstractmethod
    def save(self):
        """Saves the metadata in described by this instance back to the music file."""
        raise NotImplementedError
