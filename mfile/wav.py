import subprocess

from mutagen.wave import WAVE

import config
from mfile.mutagen_wrapper import MutagenFile
from core.util import int_descriptor

class WaveFile(MutagenFile):

    ext = '.wav'

    mapping = {
               # 'album_artist': 'albumartist',
               # 'album_artist_sort': 'albumartistsort',
               # 'album_sort': 'albumsort',
               # 'artist_sort': 'artistsort',
               # 'title_sort': 'titlesort',
               # 'tn': 'tracknumber',
               # 'tc': 'totaltracks',
               # 'dn': 'discnumber',
               # 'dc': 'totaldiscs'
              }

    def mutagen_class(self, fname):
        return WAVE(fname)

    def create_decoder(self):
        return None

    @classmethod
    def create_encoder(self, fname, metadata, bitrate):
        raise NotImplementedError

    # year = int_descriptor('date')
    # tn = int_descriptor('tracknumber')
    # tc = int_descriptor('totaltracks')
    # dn = int_descriptor('discnumber')
    # dc = int_descriptor('totaldiscs')

def main():
    import sys
    w = WaveFile(sys.argv[1])

    # del w.dnc
    # w.tn = 9
    # w.tc = 13
    # del w.album_artist
    # w.genre = 'Pop/Electronic'
    # w.year = 2018
    # w.title = 'Heaven/Hell'
    print(w.wrapped)
    print(w.format())
    print(repr(w))
    # w.save()

if __name__ == '__main__':
    main()
