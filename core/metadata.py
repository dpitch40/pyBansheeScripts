import pprint
import abc
from core.mw import MappingWrapper

class Metadata(abc.ABC, MappingWrapper):
    """Base class for all objects that provide access to song metadata."""
    all_keys = ('album_artist',
                'album_artist_sort',
                'album',
                'album_sort',
                'artist',
                'artist_sort',
                'dc', # int
                'dn', # int
                'dnc', # (int, int)
                'genre',
                'tc', # int
                'title',
                'title_sort',
                'tn', # int
                'tnc', # (int, int)
                'year', # int,
                'bitrate', # Integer number of bits/second
                'length', # Float number of milliseconds
                'location',
                )

    read_only_keys = ('bitrate', 'length', 'location')

    @abc.abstractmethod
    def save(self):
        raise NotImplementedError

    def __repr__(self):
        d = dict([(k, getattr(self, k)) for k in self.all_keys])
        return pprint.pformat(d)