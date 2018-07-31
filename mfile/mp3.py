from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

from MutagenFileWrapper import MutagenFile

class MP3File(MutagenFile):

    def mutagen_class(self, fname):
        return MP3(fname, ID3=EasyID3)

def main():
    import sys
    mp3 = MP3File(sys.argv[1])
    # mp3.dnc = (1, 5)
    # mp3.tn = 1
    # mp3.tc = 2
    # mp3.album_artist_sort = 'agallach'
    # mp3.year = 2011
    # mp3.title = 'A Poem by Keats'
    print(repr(mp3))
    # mp3.save()

if __name__ == '__main__':
    main()
