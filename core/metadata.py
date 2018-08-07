import pprint
import os.path
import string

import config
from core.mw import MappingWrapper
from core.fd import FormattingDictLike
from core.util import filter_path_elements

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

    format_lines = ['%(title)s - %(artist)s - %(album)s (%(album_artist)s) - %(genre)s',
                    '%(tn)s/%(tc)s, %(dn)s/%(dc)s\t%(year)s\t%(length)ss']

    def __init__(self, d=None):
        MappingWrapper.__init__(self, d)

    def update_changes(self, other, copy_none=True):
        changes = dict()
        for k in self.all_keys:
            if k in self.derived_keys or k in self.read_only_keys:
                continue
            v = getattr(other, k, NOT_FOUND)
            if v is NOT_FOUND:
                continue

            if v != getattr(self, k) and (v is not None or copy_none):
                changes[k] = v
        return changes

    def update(self, other, copy_none=True):
        for k, v in self.update_changes(other, copy_none).items():
            if k not in self.read_only_keys:
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

    def calculate_fname(self, base_dir=config.MusicDir, nested=True, ext=None, singleton=False,
                        group_artists=None):
        if ext is None:
            if getattr(self, 'location', None) is not None:
                ext = os.path.splitext(self.location)[1]
            else:
                ext = config.DefaultEncodeExt
        group_artists = group_artists or config.GroupArtists

        title = self.title or 'Unknown Song'
        artist = self.album_artist or self.artist or 'Unknown Artist'
        album = self.album or 'Unknown Album'

        tn = ''
        if config.NumberTracks:
            tn = self.tn
            if tn:
                dn = self.dn
                if dn:
                    tn = "%d-%02d " % (dn, tn)
                else:
                    tn = "%02d " % tn

        singleton = singleton and config.GroupSingletons
        if config.GroupArtists and not singleton:
            sort_artist = artist
            for word in config.IgnoreWords:
                if sort_artist.startswith(word + ' '):
                    sort_artist = sort_artist[len(word) + 1:]
            first_char = sort_artist[0]
            if first_char in string.ascii_letters:
                first_char = first_char.upper()
            else:
                first_char = '0'
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


    # Formatting

    def _format_length(self, value):
        return '%.3f' % (value / 1000)

    def __str__(self):
        return '%s<%s, %s, %s>' % (self.__class__.__name__, self.title, self.artist, self.album)

    # Properties/descriptors

    @property
    def album_artist(self):
        aa = self.get_item(self._map_key('album_artist'))
        if aa is None and config.AlbumArtistDefault:
            aa = self.artist
        return aa

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
