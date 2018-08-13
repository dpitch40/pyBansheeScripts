from collections import defaultdict
import pprint
import os.path

from mfile import open_music_file, mapping as mfile_mapping
from db import open_db, db_from_metadata
from db.db import MusicDb
from core.fd import FormattingDictLike
import config

class Track(FormattingDictLike):
    sigil = '+'

    format_lines = MusicDb.format_lines
    def __init__(self, mfile=None, db=None, other=None, default_metadata=None):
        if not any((mfile, db, other)):
            raise ValueError('mfile, db, and other cannot all be None')

        self.mfile = mfile
        self.db = db
        self.other = other
        if default_metadata is None:
            self._default_metadata = config.DefaultMetadataSource
        else:
            self._default_metadata = default_metadata

        self.all_keys = list()
        for metadata in self._metadata_ordering():
            if metadata:
                self.all_keys.extend([k for k in metadata.all_keys if k not in self.all_keys])

    def _metadata_ordering(self):
        if self._default_metadata == 'db':
            return (self.db, self.mfile, self.other)
        else:
            return (self.mfile, self.db, self.other)

    @property
    def default_metadata(self):
        m1, m2, m3 = self._metadata_ordering()
        return m1 or m2 or m3

    def __getattr__(self, key):
        if key in self.all_keys:
            value = None
            for metadata in self._metadata_ordering():
                if metadata is not None:
                    try:
                        value = getattr(metadata, key)
                        if value is not None:
                            break
                    except AttributeError:
                        pass
            return value
        else:
            return super(Track, self).__getattribute__(key)

    def to_dict(self, combine=True):
        if True:
            d = dict([(key, getattr(self, key)) for key in self.all_keys])
        else:
            d = defaultdict(dict)
            for name in ('mfile', 'db', 'other'):
                source = getattr(self, name)
                if source is not None:
                    subd = source.to_dict()
                    for k, v in subd.items():
                        if v is not None:
                            d[k][name] = v
            for k, source_dict in d.items():
                values_list = list(source_dict.values())
                if all((v == values_list[0] for v in values_list)):
                    d[k] = values_list[0]
            d.default_factory = lambda: ''

        return d

    def __repr__(self):
        return pprint.pformat(self.to_dict(False))

    @classmethod
    def from_file(cls, fname, **kwargs):
        return cls(open_music_file(fname), open_db(fname), **kwargs)

    @classmethod
    def from_metadata(cls, metadata, **kwargs):
        if getattr(metadata, 'location', None):
            return cls.from_file(metadata.location, **kwargs)

        for ext in mfile_mapping.keys():
            location = metadata.calculate_fname(ext=ext)
            if os.path.isfile(location):
                return cls.from_file(location, other=metadata, **kwargs)

        db = db_from_metadata(metadata)
        if db:
            return cls(open_music_file(db.location), db, other=metadata, **kwargs)
        return cls(other=metadata, **kwargs)

    def save(self):
        if self.mfile:
            self.mfile.save()
        if self.db:
            self.db.save()

    def commit(self):
        if self.db:
            self.db.commit()

    # def update(self, from_, to_):
    #     for name in (from_, to_):
    #         if getattr(self, name) is None:
    #             raise AttributeError('Track has no %s' % name)
    #     updater_name = '_update_%s_to_%s' % (from_, to_)
    #     if hasattr(self, updater_name):
    #         getattr(self, updater_name)()
    #     else:
    #         getattr(self, to_).update(getattr(self, from_))

    # def _update_mfile_to_db(self):
    #     self.db.update(self.mfile)

def main():
    import sys

    track = Track.from_file(sys.argv[1])
    print(track.format())
    print(repr(track))

if __name__ == '__main__':
    main()
