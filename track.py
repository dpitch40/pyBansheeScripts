from collections import defaultdict
import pprint

from mfile import open_music_file
from db import open_db
from db.db import MusicDb
from core.fd import FormattingDictLike

class Track(FormattingDictLike):
    sigil = '+'

    format_lines = MusicDb.format_lines
    def __init__(self, mfile=None, db=None, other=None):
        if not any((mfile, db, other)):
            raise ValueError('mfile, db, and other cannot all be None')

        self.mfile = mfile
        self.db = db
        self.other = other

    def to_dict(self):
        d = defaultdict(dict)
        for name in ('mfile', 'db', 'other'):
            source = getattr(self, name)
            if source is not None:
                subd = source.to_dict()
                for k, v in subd.items():
                    d[k][name] = v
        for k, source_dict in d.items():
            values_list = list(source_dict.values())
            if all((v == values_list[0] for v in values_list)):
                d[k] = values_list[0]

        return d

    def _format_dict(self):
        d = self.to_dict()
        for k, v in d.items():
            if isinstance(v, dict):
                d[k] = '/'.join(['%s:%s' % (source, self._format_value(k, subv)) for source, subv in v.items()])
            else:
                d[k] = self._format_value(k, v)
        return d

    def _format_length(self, value):
        return '%.3f' % (value / 1000)

    @classmethod
    def from_file(cls, fname, other=None):
        return cls(open_music_file(fname), open_db(fname), other)

    def save(self):
        if self.mfile:
            self.mfile.save()
        if self.db:
            self.db.save()

    def update_changes(self, from_, to_):
        for name in (from_, to_):
            if getattr(self, name) is None:
                raise AttributeError('Track has no %s' % name)
        return getattr(self, to_).update_changes(getattr(self, from_))

    def update(self, from_, to_):
        for name in (from_, to_):
            if getattr(self, name) is None:
                raise AttributeError('Track has no %s' % name)
        getattr(self, to_).update(getattr(self, from_))

def main():
    import sys

    track = Track.from_file(sys.argv[1])
    print(track)

if __name__ == '__main__':
    main()
