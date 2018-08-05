import abc

from core.metadata import Metadata
from core.mw import MappingWrapper

class MusicDb(Metadata):
    """Base class for metadata derived from a database/data file, e.g. one generated by a music player."""

    sigil = '*'

    all_keys = Metadata.all_keys + ('bitrate',
                                    'rating',
                                    'play_count',
                                    'skip_count',
                                    'last_played',
                                    'last_skipped',
                                    'date_added',
                                    'location')

    format_lines = ['%(title)s - %(artist)s - %(album)s (%(album_artist)s) - %(genre)s',
                    '%(tn)s/%(tc)s, %(dn)s/%(dc)s\t%(year)s\t%(length)ss\t%(bitrate)skbps\t'
                        '%(rating)s/5, %(play_count)s plays, %(skip_count)s skips',
                    'Added %(date_added)s, last played %(last_played)s, last skipped %(last_skipped)s',
                    '%(location)s']

    read_only_keys = ()

    def __init__(self, d):
        super(MusicDb, self).__init__(d)

    def _format_dict(self):
        d = super(MusicDb, self)._format_dict()
        for k in ('last_played',
                  'last_skipped',
                  'date_added'):
            if d[k]:
                d[k] = d[k].strftime('%Y-%m-%d %H:%M:%S')
        return d

    def _format_bitrate(self, bitrate):
        bitrate = bitrate / 1000
        if bitrate % 1 == 0:
            bitrate = int(bitrate)
        return bitrate

    # To be overridden

    @abc.abstractmethod
    def save(self):
        """Saves thhis object back to the database."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def commit(self):
        """Commits the object's database. Call this after saving all relevant
           objects to write the changes back to the databas file."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def load_all(self):
        """Returns a list of all instances of this object in the corresponding database."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_file(cls, loc):
        """Initializes and returns a new object of this class from a file."""
        raise NotImplementedError
