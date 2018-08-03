import pprint
from core.mw import MappingWrapper

class Metadata(MappingWrapper):
    sigil = '#'

    """Base class for all objects that provide access to song metadata."""
    all_keys = ('title',
                'title_sort',
                'artist',
                'artist_sort',
                'album',
                'album_sort',
                'album_artist',
                'album_artist_sort',
                'genre',
                'year', # int,
                'tn', # int
                'tc', # int
                'tnc', # (int, int)
                'dn', # int
                'dc', # int
                'dnc', # (int, int)
                'length', # Float/Int number of milliseconds
                )

    format_lines = ['%(title)s - %(artist)s - %(album)s (%(album_artist)s) - %(genre)s',
                    '%(tn)s/%(tc)s, %(dn)s/%(dc)s\t%(year)s\t%(length).3fs']

    def __init__(self, d=None):
        MappingWrapper.__init__(self, d)

    def to_dict(self):
        return dict([(k, getattr(self, k)) for k in self.all_keys])

    @classmethod
    def from_dict(cls, d):
        inst = cls()
        for k, v in d.items():
            if v is not None:
                setattr(inst, k, v)
        return inst

    def _format_dict(self):
        d = self.to_dict()
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
        return pprint.pformat(self.to_dict())

    # properties

    @property
    def tnc(self):
        return (self.tn, self.tc)

    @tnc.setter
    def tnc(self, value):
        if value is None:
            self.tn, self.tc = None, None
        else:
            self.tn, self.tc = value

    @tnc.deleter
    def tnc(self):
        del self.tn
        del self.tc

    @property
    def dnc(self):
        return (self.dn, self.dc)

    @dnc.setter
    def dnc(self, value):
        if value is None:
            self.dn, self.dc = None, None
        else:
            self.dn, self.dc = value

    @dnc.deleter
    def dnc(self):
        del self.dn
        del self.dc
