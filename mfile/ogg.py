from mutagen.oggvorbis import OggVorbis

from mfile.mp3 import MP3File

class OggFile(MP3File): # Inherit from MP3 file, just to override a few things

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
    print(ogg.format())
    print(repr(ogg))
    # ogg.save()

if __name__ == '__main__':
    main()
