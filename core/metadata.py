import pprint
from core.mw import MappingWrapper

class Metadata(MappingWrapper):
    sigil = '#'

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
                'length', # Float/Int number of milliseconds
                )

    format_lines = ['%(title)s - %(artist)s - %(album)s (%(album_artist)s) - %(genre)s',
                    '%(tn)s/%(tc)s, %(dn)s/%(dc)s\t%(year)s\t%(length).3fs']

    def __init__(self, d):
        MappingWrapper.__init__(self, d)

    def _to_dict(self):
        return dict([(k, getattr(self, k)) for k in self.all_keys])

    def _format_dict(self):
        d = self._to_dict()
        if d['length']:
            d['length'] = d['length'] / 1000
        return d

    def __str__(self):
        d = self._format_dict()
        for k, v in d.items():
            if v is None:
                d[k] = ''
        return (self.sigil * 3) + ' ' + '\n    '.join([l % d for l in self.format_lines])

    def __repr__(self):
        return pprint.pformat(self._to_dict())
