import operator
import os.path
import os
import subprocess

from quodlibet.formats import load_audio_files, dump_audio_files

from .db import MusicDb
import config
from core.util import date_descriptor, int_descriptor, make_descriptor_func, make_numcount_descriptors

songs_loc = config.QLSongsLoc
lists_dir = os.path.join(os.path.dirname(songs_loc), 'lists')
playlists_dir = os.path.join(os.path.dirname(songs_loc), 'playlists')

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
                                  x.get('discnumber', ''), int(x.get('tracknumber', '0').split('/')[0])))
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

            try:
                artist = song['artist']
            except KeyError:
                print(song['~filename'] + ' lacks an artist tag')
                continue
            try:
                album = song['album']
            except KeyError:
                print(song['~filename'] + ' lacks an album tag')
                continue
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
                try:
                    dn = int(dn)
                except ValueError:
                    print(song)
                    raise
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
               'skip_count': '~#skipcount',
               'fsize': '~#filesize'
        }

    def __init__(self, song):
        super(MusicDb, self).__init__(song)

    # Overridden from MusicDb

    def _save(self, changes):
        # No need for any action, self.wrapped is already a song in qls._songs that will be saved
        # when commit is called
        pass

    @classmethod
    def commit(cls):
        qls.save_songs()

    @classmethod
    def load_all(cls):
        return [cls(song) for song in qls.songs]

    @classmethod
    def _ql_query(cls, query):
        try:
            sp = subprocess.run(['quodlibet', '--print-query=%s' %
                        query], stdout=subprocess.PIPE, check=True,
                        universal_newlines=True)
        except subprocess.CalledProcessError as ex:
            raise SystemExit
        returned_lines = sp.stdout.strip()
        return sorted(returned_lines.split('\n'))

    @classmethod
    def load_playlists(cls):
        """Returns: {playlist_name (string):
                     [QLDb()]}
        """
        locations_to_tracks = dict()

        def _from_file(loc):
            if loc in locations_to_tracks:
                return locations_to_tracks[loc]
            else:
                track = locations_to_tracks[loc] = cls.from_file(loc)
                return track

        playlists = dict()
        for pl_file in os.listdir(playlists_dir):
            pl_list = list()
            with open(os.path.join(playlists_dir, pl_file), 'r') as fobj:
                for line in fobj.readlines():
                    line = line.strip()
                    pl_list.append(_from_file(line))
            playlists[pl_file] = pl_list

        # Smart playlists

        queries_file = os.path.join(lists_dir, 'queries.saved')
        if os.path.isfile(queries_file):
            with open(queries_file, 'r') as fobj:
                query = fobj.readline().strip()
                while query != '':
                    name = cur_line = fobj.readline().strip()
                    pl_list = list()
                    for line in cls._ql_query(query):
                        pl_list.append(_from_file(line))
                    playlists[name] = pl_list
                    query = fobj.readline().strip()

        return playlists

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
    length = make_descriptor_func(lambda x: int(x * 1000), lambda x: x / 1000)('~#length')
    bitrate = make_descriptor_func(lambda x: x * 1000, lambda x: int(x / 1000))('~#bitrate')

    tn, tc, tnc = make_numcount_descriptors('tn', 'tc', 'tracknumber')
    dn, dc, dnc = make_numcount_descriptors('dn', 'dc', 'discnumber')

def main():
    import sys
    import datetime
    track = QLDb.from_file(os.path.abspath(sys.argv[1]))

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
