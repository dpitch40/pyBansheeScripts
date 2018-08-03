import abc

from core.metadata import Metadata

class MusicFile(Metadata):

    sigil = '%'

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
        self.fname = fname
        super(MusicFile, self).__init__(d)

    def _format_dict(self):
        d = super(MusicFile, self)._format_dict()
        if d['bitrate']:
            d['bitrate'] = d['bitrate'] / 1000
            if d['bitrate'] % 1 == 0:
                d['bitrate'] = int(d['bitrate'])
        return d

    @property
    def location(self):
        return self.fname

    @abc.abstractmethod
    def save(self):
        """Saves the metadata in described by this instance back to the music file."""
        raise NotImplementedError
