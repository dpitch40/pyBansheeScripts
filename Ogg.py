from mutagen.oggvorbis import OggVorbis

from MutagenFileWrapper import MutagenFile

class OggFile(MutagenFile):

    def mutagen_class(self, fname):
        return OggVorbis(fname)

def main():
    import sys
    ogg = OggFile(sys.argv[1])

    # ogg.dnc = (1, 5)
    # ogg.tn = 1
    # ogg.tc = 2
    # ogg.album_artist_sort = 'agallach'
    # ogg.year = 2009
    # ogg.title = 'A Poem by Keats'
    print(repr(ogg))
    # ogg.save()

if __name__ == '__main__':
    main()
