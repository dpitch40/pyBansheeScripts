from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3, EasyID3KeyError

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

class MusicFile(object):
    def __init__(self, fname):
        super(MusicFile, self).__setattr__('fname', fname)

class MP3File(MusicFile):
    """
        http://id3.org/id3v2.4.0-structure
    """

    tag_mapping = {'album_artist': 'albumartistsort',
                   'album_artist_sort': 'albumartistsort',
                   'album_sort': 'albumsort',
                   'artist_sort': 'artistsort',
                   'year': 'date',
                   'title_sort': 'titlesort'}

    def __init__(self, fname):
        super(MP3File, self).__setattr__('audio', MP3(fname, ID3=EasyID3))
        super(MP3File, self).__setattr__('changes', dict())
        super(MP3File, self).__init__(fname)

    def save(self):
        self.audio.save()

    def _delete(self, key):
        del self.audio[key]

    def _set(self, key, value):
        if not isinstance(value, list):
            value = [value]
        self.audio[key] = value

    def _map_key(self, key):
        return self.tag_mapping.get(key, key)

    def __getattr__(self, key):
        mapped_key = self._map_key(key)
        if mapped_key in self.audio:
            return self.audio[mapped_key]
        else:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        mapped_key = self._map_key(key)
        self.audio[mapped_key] = value

    def __delattr__(self, key):
        mapped_key = self._map_key(key)
        del self.audio[mapped_key]

    # Track number

    @property
    def tn(self):
        try:
            return int(self.audio['tracknumber'][0].split('/')[0])
        except (EasyID3KeyError, IndexError):
            return None

    @tn.setter
    def tn(self, value):
        tc = self.tc
        if tc:
            self.audio['tracknumber'] = '%d/%d' % (value, tc)
        else:
            self.audio['tracknumber'] = '%d' % value

    @tn.deleter
    def tn(self):
        del self.audio['tracknumber']

    # Track count

    @property
    def tc(self):
        try:
            return int(self.audio['tracknumber'][0].split('/')[1])
        except (EasyID3KeyError, IndexError):
            return None

    @tn.setter
    def tn(self, value):
        tn = self.tn
        if tn:
            self.audio['tracknumber'] = '%d/%d' % (tn, value)

    @tn.deleter
    def tn(self):
        tn = self.tn
        if tn:
            self.audio['tracknumber'] = '%d' % tn

    # Disc number

    @property
    def dn(self):
        try:
            return int(self.audio['discnumber'][0].split('/')[0])
        except (EasyID3KeyError, IndexError):
            return None

    @dn.setter
    def dn(self, value):
        dc = self.dc
        if dc:
            self.audio['discnumber'] = '%d/%d' % (value, dc)
        else:
            self.audio['discnumber'] = '%d' % value

    @dn.deleter
    def dn(self):
        del self.audio['discnumber']

    # Disc count

    @property
    def dc(self):
        try:
            return int(self.audio['discnumber'][0].split('/')[1])
        except (EasyID3KeyError, IndexError):
            return None

    @dn.setter
    def dn(self, value):
        dn = self.dn
        if dn:
            self.audio['discnumber'] = '%d/%d' % (dn, value)

    @dn.deleter
    def dn(self):
        dn = self.dn
        if dn:
            self.audio['discnumber'] = '%d' % dn

def main():
    import sys
    mp3 = MP3File(sys.argv[1])
    print(mp3.audio)
    print(mp3.tn, mp3.tc)
    print(mp3.dn, mp3.dc)

if __name__ == '__main__':
    main()
