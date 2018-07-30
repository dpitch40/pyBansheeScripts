from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3, EasyID3KeyError

delete = object()

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
        if self.changes:
            for key, change in sorted(self.changes.items()):
                if change is delete:
                    self._delete(key)
                else:
                    self._set(key, change)
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
            raise AttributeError, key

    def __setattr__(self, key, value):
        mapped_key = self._map_key(key)
        if mapped_key in self.audio:
            self.changes[key] = value
        else:
            raise AttributeError, key

    def __delattr__(self, key):
        mapped_key = self._map_key(key)
        if mapped_key in self.audio:
            self.changes[mapped_key] = delete
        else:
            raise AttributeError, key

    # Track number

    @property
    def tn(self):
        try:
            return int(self.audio['tracknumber'][0].split('/')[0])
        except EasyID3KeyError:
            return None

    @tn.setter
    def tn(self, value):
        try:
            tn = self.audio['tracknumber']
        except EasyID3KeyError:
            return None
        else:
            if '/' in tn[0]:
                tn, tc = tn[0].split('/')
                new_tn = '%d/%s' % (value, tc)
            else:
                new_tn = '%d' % value
            self.changes['tracknumber'] = new_tn

    @tn.deleter
    def tn(self):
        if 'tracknumber' in self.audio:
            self.changes['tracknumber'] = delete
        else:
            pass

    # Track count

    @property
    def tc(self):
        try:
            tracknum = self.audio['tracknumber'][0]
        except EasyID3KeyError:
            return None
        else:
            try:
                return int(tracknum.split('/')[1])
            except IndexError:
                return None

    # Disc number

    @property
    def dn(self):
        try:
            return int(self.audio['discnumber'][0].split('/')[0])
        except EasyID3KeyError:
            return None

    # Disc count

    @property
    def dc(self):
        try:
            tracknum = self.audio['discnumber'][0]
        except EasyID3KeyError:
            return None
        else:
            try:
                return int(tracknum.split('/')[1])
            except IndexError:
                return None

def main():
    import sys
    mp3 = MP3File(sys.argv[1])
    print(mp3.audio)
    print(mp3.tn, mp3.tc)
    print(mp3.dn, mp3.dc)

if __name__ == '__main__':
    main()
