from quodlibet.formats import load_audio_files, dump_audio_files

from db.db import MusicDb
import Config

songs_loc = Config.QLSongsLoc

class QLSongs(object):
    def __init__(self):
        self._songs = None
        self._locations_to_songs = None

    def _load_songs(self):
        with open(songs_loc, 'rb') as fobj:
            data = fobj.read()
        songs = load_audio_files(data)
        self._load_locations_to_songs(songs)

        return songs

    def _load_locations_to_songs(self, songs):
        # Make sure to keep this updated if locations change
        self._locations_to_songs = dict()
        for song in songs:
            location = song['~filename']
            if location in self._locations_to_songs:
                assert False, "%s contains multiple songs with the filename %s" % (songs_loc, location)
            self._locations_to_songs[location] = song

    def location_to_song(self, loc):
        if self._songs is None:
            self._load_songs()
        return self._locations_to_songs[loc]

    @property
    def songs(self):
        if self._songs is None:
            self._songs = self._load_songs()
        return self._songs

qls = QLSongs()

class QLDb(MusicDb):

    def __init__(self, song):
        super(MusicDb, self).__init__(song)
        self.song = song
        print(self.song)

    def save(self):
        raise NotImplementedError

    @classmethod
    def commit(cls):
        raise NotImplementedError

    @classmethod
    def load_all(cls):
        raise NotImplementedError

    @classmethod
    def from_location(cls, loc):
        try:
            return cls(qls.location_to_song(loc))
        except KeyError as e:
            raise KeyError('No song with liocation %r exists in the songs library' % loc) from e

def main():
    import sys
    track = QLDb.from_location(sys.argv[1])

if __name__ == '__main__':
    main()
