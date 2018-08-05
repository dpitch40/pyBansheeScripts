from mutagen.oggvorbis import OggVorbis

from mfile.mutagen_wrapper import MutagenFile

class OggFile(MutagenFile):

    ext = '.ogg'

    def mutagen_class(self, fname):
        return OggVorbis(fname)

def main():
    import sys
    ogg = OggFile(sys.argv[1])

    # del ogg.dnc
    # ogg.tn = 9
    # ogg.tc = 13
    # del ogg.album_artist
    # ogg.genre = 'Pop/Electronic'
    # ogg.year = 2018
    # ogg.title = 'Heaven/Hell'
    print(ogg)
    # ogg.save()

if __name__ == '__main__':
    main()
