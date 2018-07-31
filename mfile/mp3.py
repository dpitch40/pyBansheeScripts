from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

from mfile.mutagen_wrapper import MutagenFile

"""EasyID3 tags:
   ['albumartistsort', 'musicbrainz_albumstatus', 'lyricist', 'musicbrainz_workid', 'releasecountry',
    'date', 'performer', 'musicbrainz_albumartistid', 'composer', 'catalognumber', 'encodedby',
    'tracknumber', 'musicbrainz_albumid', 'album', 'asin', 'musicbrainz_artistid', 'mood', 'copyright',
    'author', 'media', 'length', 'acoustid_fingerprint', 'version', 'artistsort', 'titlesort',
    'discsubtitle', 'website', 'musicip_fingerprint', 'conductor', 'musicbrainz_releasegroupid',
    'compilation', 'barcode', 'performer:*', 'composersort', 'musicbrainz_discid',
    'musicbrainz_albumtype', 'genre', 'isrc', 'discnumber', 'musicbrainz_trmid', 'acoustid_id',
    'replaygain_*_gain', 'musicip_puid', 'originaldate', 'language', 'artist', 'title', 'bpm',
    'musicbrainz_trackid', 'arranger', 'albumsort', 'replaygain_*_peak', 'organization',
    'musicbrainz_releasetrackid']"""

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
