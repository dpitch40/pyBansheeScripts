from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3, EasyID3KeyError

import Config

class MP3File(MusicFile):

    tag_mapping = {'album_artist': 'albumartistsort',
                   'album_artist_sort': 'albumartistsort',
                   'album_sort': 'albumsort',
                   'artist_sort': 'artistsort',
                   'title_sort': 'titlesort'}

    def __init__(self, fname):
        self.audio = MP3(fname, ID3=EasyID3)
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
        if key in self.all_keys:
            mapped_key = self._map_key(key)
            return self.audio.get(mapped_key, [None])[0]
        else:
            return super(MP3File, self).__getattr__(key)

    def __setattr__(self, key, value):
        if key in self.all_keys:
            # __setattr__ takes priority over descriptors, so we have to check if we need to use one
            if isinstance(getattr(self.__class__, key, None), property):
                super(MP3File, self).__setattr__(key, value)
            else:
                mapped_key = self._map_key(key)
                self.audio[mapped_key] = value
        else:
            super(MP3File, self).__setattr__(key, value)

    def __delattr__(self, key):
        if key in self.all_keys:
            # __delattr__ takes priority over descriptors, so we have to check if we need to use one
            if isinstance(getattr(self.__class__, key, None), property):
                super(MP3File, self).__delattr__(key, value)
            else:
                del self.audio[mapped_key]
        else:
            super(MP3File, self).__delattr__(key)

    @property
    def bitrate(self):
        return self.audio.info.bitrate

    @property
    def length(self):
        return self.audio.info.length

    @property
    def album_artist(self):
        aa = self.__getattr__('album_artist')
        if aa is None and Config.AlbumArtistDefault:
            aa = self.__getattr__('artist')
        return aa

    @album_artist.setter
    def album_artist(self, value):
        self.audio['albumartistsort'] = value

    @album_artist.deleter
    def album_artist(self, value):
        del self.audio['albumartistsort']

    @property
    def year(self):
        try:
            return int(self.audio['date'][0])
        except (EasyID3KeyError, IndexError):
            return None

    @year.setter
    def year(self, value):
        self.audio['date'] = str(value)

    @year.deleter
    def year(self):
        del self.audio['year']

    # Track number/count

    @property
    def tnc(self):
        try:
            tracknum = self.audio['tracknumber'][0]
            if '/' in tracknum:
                tn, tc = tracknum.split('/')
                return int(tn), int(tc)
            else:
                return int(tracknum), None
        except (EasyID3KeyError, IndexError):
            return None, None

    @tnc.setter
    def tnc(self, value):
        tn, tc = value
        if tc:
            self.audio['tracknumber'] = '%d/%d' % (tn, tc)
        else:
            self.audio['tracknumber'] = '%d' % tn

    @tnc.deleter
    def tnc(self):
        del self.audio['tracknumber']

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

    @tc.setter
    def tc(self, value):
        tn = self.tn
        if tn:
            self.audio['tracknumber'] = '%d/%d' % (tn, value)

    @tc.deleter
    def tc(self):
        tn = self.tn
        if tn:
            self.audio['tracknumber'] = '%d' % tn

    # Disc number/count

    @property
    def dnc(self):
        try:
            discnum = self.audio['discnumber'][0]
            if '/' in discnum:
                dn, dc = discnum.split('/')
                return int(dn), int(dc)
            else:
                return int(discnum), None
        except (EasyID3KeyError, IndexError):
            return None, None

    @dnc.setter
    def dnc(self, value):
        dn, dc = value
        if dc:
            self.audio['discnumber'] = '%d/%d' % (dn, dc)
        else:
            self.audio['discnumber'] = '%d' % dn

    @dnc.deleter
    def dnc(self):
        del self.audio['discnumber']

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

    @dc.setter
    def dc(self, value):
        dn = self.dn
        if dn:
            self.audio['discnumber'] = '%d/%d' % (dn, value)

    @dc.deleter
    def dc(self):
        dn = self.dn
        if dn:
            self.audio['discnumber'] = '%d' % dn

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
