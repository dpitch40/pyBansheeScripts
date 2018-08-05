# from mutagen import MutagenError

import os.path

import config
from core.mw import MappingWrapper
from core.util import date_descriptor, int_descriptor, make_descriptor_func, make_numcount_descriptors
from mfile.mfile import MusicFile

class MutagenFile(MusicFile):

    mapping = {'album_artist': 'albumartistsort',
               'album_artist_sort': 'albumartistsort',
               'album_sort': 'albumsort',
               'artist_sort': 'artistsort',
               'title_sort': 'titlesort'}

    def __init__(self, fname):
        if os.path.splitext(fname)[1].lower() != self.ext:
            raise ValueError('Cannot open the file %s with %s' % (fname,
                                    self.__class__.__name__))
        audio = self.mutagen_class(fname)
        MusicFile.__init__(self, fname, audio)

    # MappingWrapper methods overridden

    def get_item(self, key):
        value = super(MutagenFile, self).get_item(key)
        if isinstance(value, list) and value:
            value = value[0]
        return value

    def set_item(self, key, value):
        super(MutagenFile, self).set_item(key, [value])

    # MusicFile methods overridden

    def _save(self):
        self.wrapped.save()

    def rebase(self, new_fname):
        self.fname = new_fname
        self.wrapped = self.mutagen_class(new_fname)
        self.set_dict(self.wrapped)

    # Properties/descriptors

    @property
    def bitrate(self):
        return self.wrapped.info.bitrate

    @property
    def length(self):
        return self.wrapped.info.length * 1000

    @property
    def album_artist(self):
        aa = self.__getattr__('album_artist')
        if aa is None and config.AlbumArtistDefault:
            aa = self.__getattr__('artist')
        return aa

    @album_artist.setter
    def album_artist(self, value):
        self.wrapped['albumartistsort'] = value

    @album_artist.deleter
    def album_artist(self):
        del self.wrapped['albumartistsort']

    year = int_descriptor('date')
    tn, tc, tnc = make_numcount_descriptors('tn', 'tc', 'tracknumber')
    dn, dc, dnc = make_numcount_descriptors('dn', 'dc', 'discnumber')

    # To be overridden

    def mutagen_class(self, fname):
        raise NotImplementedError
