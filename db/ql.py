from quodlibet.formats import load_audio_files, dump_audio_files

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

    @property
    def songs(self):
        if self._songs is None:
            self._songs = self._load_songs()
        return self._songs

qls = QLSongs()


def main():
    qls.songs
    print(len(qls._locations_to_songs))

    # import sys
    # track = BansheeDb.from_trackid(int(sys.argv[1]))
    # track.tc = 13
    # print(repr(track))
    # track.save()

if __name__ == '__main__':
    main()
