import pprint
from core.mw import MappingWrapper
from core.fd import FormattingDictLike

class Metadata(MappingWrapper, FormattingDictLike):
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
                    '%(tn)s/%(tc)s, %(dn)s/%(dc)s\t%(year)s\t%(length)ss']

    def __init__(self, d=None):
        MappingWrapper.__init__(self, d)

    def update_changes(self, other, copy_none=True):
        changes = dict()
        for k, v in other.all_keys:
            if k in self.all_keys:
                if v is not None or copy_none:
                    changes[k] = v
        return changes

    def update(self, other, copy_none=True):
        for k, v in self.update_changes(other, copy_none).items():
            setattr(self, k, v)

    def to_dict(self):
        return dict([(k, getattr(self, k)) for k in self.all_keys])

    @classmethod
    def from_dict(cls, d):
        inst = cls()
        for k, v in d.items():
            if v is not None:
                setattr(inst, k, v)
        return inst

    def _format_length(self, value):
        return '%.3f' % (value / 1000)

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
