from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

from mfile.mutagen_wrapper import MutagenFile
from core.util import int_descriptor, make_descriptor_func, make_numcount_descriptors

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

    ext = '.mp3'

    def mutagen_class(self, fname):
        return MP3(fname, ID3=EasyID3)

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

def main():
    import sys
    mp3 = MP3File(sys.argv[1])
    # mp3.dnc = (2, 2)
    # mp3.tn = 2
    # mp3.tc = 10
    # del mp3.album_artist
    # mp3.year = 2010
    # mp3.title = 'A Poem by Yeats'
    print(mp3.format())
    print(repr(mp3))
    # mp3.save()

if __name__ == '__main__':
    main()
