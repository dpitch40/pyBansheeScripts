import operator

from quodlibet.formats import load_audio_files, dump_audio_files

from .db import MusicDb
import config
from core.util import date_descriptor, int_descriptor, make_descriptor_func, make_numcount_descriptors

songs_loc = config.QLSongsLoc

class QLSongs(object):
    def __init__(self):
        self._songs = None
        self._locations_to_songs = None
        self._metadata_to_songs = None

    def _load_songs(self):
        with open(songs_loc, 'rb') as fobj:
            data = fobj.read()
        songs = load_audio_files(data)
        songs.sort(key=lambda x: (x.get('albumartist', ''), x.get('artist', ''), x.get('album', ''),
                                  x.get('discnumber', ''), x.get('tracknumber', '')))
        self._load_indices(songs)

        return songs

    def _load_indices(self, songs):
        # Make sure to keep this updated if locations change
        self._locations_to_songs = dict()
        self._metadata_to_songs = dict()
        for song in songs:
            location = song['~filename']
            if location in self._locations_to_songs:
                assert False, "%s contains multiple songs with the filename %s" % (songs_loc, location)
            self._locations_to_songs[location] = song

            artist = song['artist']
            album = song['album']
            tn = None
            if song.get('tracknumber', ''):
                tn = song['tracknumber']
                if '/' in tn:
                    tn = tn.split('/')[0]
                tn = int(tn)
            dn = None
            if song.get('discnumber', ''):
                dn = song['discnumber']
                if '/' in dn:
                    dn = dn.split('/')[0]
                dn = int(dn)
            self._metadata_to_songs[(artist, album, tn, dn)] = song

    def location_to_song(self, loc):
        if self._songs is None:
            self._songs = self._load_songs()
        return self._locations_to_songs[loc]

    def lookup_song(self, key):
        if self._songs is None:
            self._songs = self._load_songs()
        return self._metadata_to_songs[key]

    @property
    def songs(self):
        if self._songs is None:
            self._songs = self._load_songs()
        return self._songs

    def save_songs(self):
        if self._songs is not None:
            data = dump_audio_files(self._songs)
            with open(songs_loc, 'wb') as fobj:
                fobj.write(data)

qls = QLSongs()

class QLDb(MusicDb):

    mapping = {'album_artist': 'albumartist',
               'album_artist_sort': 'albumartistsort',
               'album_sort': 'albumsort',
               'artist_sort': 'artistsort',
               'title_sort': 'titlesort',
               'year': 'date',
               'location': '~filename',
               'play_count': '~#playcount',
               'skip_count': '~#skipcount'
        }

    def __init__(self, song):
        super(MusicDb, self).__init__(song)

    # Overridden from MusicDb

    def _save(self, changes):
        pass

    @classmethod
    def commit(cls):
        qls.save_songs()

    @classmethod
    def load_all(cls):
        return qls.songs

    @classmethod
    def from_file(cls, loc):
        try:
            return cls(qls.location_to_song(loc))
        except KeyError as e:
            return None

    @classmethod
    def from_metadata(cls, md):
        try:
            return cls(qls.lookup_song((md.artist, md.album, md.tn, md.dn)))
        except KeyError as e:
            return None

    # Properties/descriptors

    date_added = date_descriptor('~#added')
    last_played = date_descriptor('~#lastplayed')
    last_skipped = date_descriptor('~#lastskipped')
    year = int_descriptor('date')
    rating = make_descriptor_func(lambda x: int(x * 5), lambda x: x / 5)('~#rating')
    length = make_descriptor_func(lambda x: int(x * 1000), lambda x: int(x / 1000))('~#length')
    bitrate = make_descriptor_func(lambda x: x * 1000, lambda x: int(x / 1000))('~#bitrate')

    tn, tc, tnc = make_numcount_descriptors('tn', 'tc', 'tracknumber')
    dn, dc, dnc = make_numcount_descriptors('dn', 'dc', 'discnumber')

def main():
    import sys
    import datetime
    track = QLDb.from_file(sys.argv[1])

    print(track.wrapped)
    print(track.format())
    print(repr(track))

    # del track.last_played
    # track.tnc = (1, 8)
    # track.dc = 2
    # del track.skip_count
    # track.year = 2008
    # track.genre = 'Progressive Metal'
    # track.date_added = datetime.datetime(2017, 8, 8, 11, 16, 31)
    # track.album = '01011001'
    # track.save()
    # track.commit()

if __name__ == '__main__':
    main()
