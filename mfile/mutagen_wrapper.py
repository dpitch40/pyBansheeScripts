# from mutagen import MutagenError

import os.path

import config
from core.mw import MappingWrapper
from mfile.mfile import MusicFile

class MutagenFile(MusicFile):

    mapping = {'album_artist': 'albumartist',
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

    # To be overridden

    def mutagen_class(self, fname):
        raise NotImplementedError
