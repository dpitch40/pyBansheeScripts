import pprint
import os.path

import config
from core.mw import MappingWrapper
from core.fd import FormattingDictLike
from core.util import filter_path_elements, value_is_none, get_sort_char

NOT_FOUND = object()

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

    derived_keys = {'tnc', 'dnc'}

    format_lines = [('title', 'album', 'album_artist', 'artist', 'genre'),
                    ('tnc', 'dnc', 'year', 'length')]

    def __init__(self, d=None):
        MappingWrapper.__init__(self, d)

    def update_changes(self, other, copy_none=True, allowed_fields=None):
        changes = dict()
        for k in self.all_keys:
            if k in self.derived_keys or k in self.read_only_keys:
                continue
            if allowed_fields is not None and k not in allowed_fields:
                continue
            v = getattr(other, k, NOT_FOUND)
            if v is NOT_FOUND:
                continue

            # Special case for length--only update length if the new value is based on an actual file
            if k == 'length' and not hasattr(other, 'location'):
                continue

            if v != getattr(self, k) and (v is not None or copy_none):
                changes[k] = v
        return changes

    def update(self, other, copy_none=True, allowed_fields=None):
        self.update_from_dict(self.update_changes(other, copy_none, allowed_fields))

    def update_from_dict(self, d):
        # Reverse sort so dn/tn get set before dc/tc
        for k, v in sorted(d.items(), reverse=True):
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

    def calculate_fname(self, base_dir=config.MusicDir, nested=True, ext=None,
                        group_artists=None):
        if ext is None:
            if getattr(self, 'location', None) is not None:
                ext = os.path.splitext(self.location)[1]
            else:
                ext = config.DefaultEncodeExt
        if group_artists is None:
            group_artists = config.GroupArtists

        title = self.title or 'Unknown Song'
        artist = self.album_artist or self.artist or 'Unknown Artist'
        album = self.album or 'Unknown Album'

        tn = ''
        if config.NumberTracks:
            tn_num = self.tn
            if tn_num not in (0, None):
                dn = self.dn
                if dn:
                    tn = "%d-%02d " % (dn, tn_num)
                else:
                    tn = "%02d " % tn_num

        singleton = getattr(self, 'singleton', False) and config.GroupSingletons
        if group_artists and not singleton:
            first_char = get_sort_char(artist)
            base_dir = os.path.join(base_dir, first_char)

        if singleton:
            path_elements = ["Singletons"]
        elif not nested:
            path_elements = []
        else:
            path_elements = [artist, album]

        result = self._condense_dest(path_elements, title, tn, ext, base_dir)

        return result

    def _condense_dest(self, path_elements, fBase, tn, ext, base_dir):
        new_name = self._get_dest_real(path_elements, fBase, tn, ext, base_dir)

        # Make sure the name isn't too long
        max_el_len = 64
        while len(new_name) > 255:
             new_name = self._get_dest_real([e[:max_el_len].rstrip() for e in path_elements],
                                      fBase[:max_el_len].rstrip(), tn, ext, base_dir)
             max_el_len -= 8

        return new_name

    def _get_dest_real(self, path_elements, title, tn, ext, base_dir):

        new_base = "%s%s%s" % (tn, title, ext)
        return os.path.join(base_dir, filter_path_elements(path_elements + [new_base]))

    def __str__(self):
        return '%s<%s, %s, %s>' % (self.__class__.__name__, self.title, self.artist, self.album)

    # Properties/descriptors

    @property
    def album_artist(self):
        aa = self.get_item('albumartist')
        if aa is None and config.AlbumArtistDefault:
            aa = self.artist
        return aa

    @property
    def album_artist_or_artist(self):
        return self.get_item('albumartist') or self.artist

    @album_artist.setter
    def album_artist(self, value):
        self.set_item('albumartist', value)

    @album_artist.deleter
    def album_artist(self):
        self.del_item('albumartist')

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
