from mutagen.flac import FLAC

from mfile.mutagen_wrapper import MutagenFile
from core.util import int_descriptor

class FlacFile(MutagenFile):

    ext = '.flac'

    mapping = {'album_artist': 'albumartistsort',
               'album_artist_sort': 'albumartistsort',
               'album_sort': 'albumsort',
               'artist_sort': 'artistsort',
               'title_sort': 'titlesort',
               'tn': 'tracknumber',
               'tc': 'totaltracks',
               'dn': 'discnumber',
               'dc': 'totaldiscs'}

    def mutagen_class(self, fname):
        return FLAC(fname)

    year = int_descriptor('date')
    tn = int_descriptor('tracknumber')
    tc = int_descriptor('totaltracks')
    dn = int_descriptor('discnumber')
    dc = int_descriptor('totaldiscs')

def main():
    import sys
    flac = FlacFile(sys.argv[1])

    # del flac.dnc
    # flac.tn = 9
    # flac.tc = 13
    # del flac.album_artist
    # flac.genre = 'Pop/Electronic'
    # flac.year = 2018
    # flac.title = 'Heaven/Hell'
    print(flac.format())
    print(repr(flac))
    # flac.save()

if __name__ == '__main__':
    main()
