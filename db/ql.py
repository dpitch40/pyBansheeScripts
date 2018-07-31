import pickle

import Config

songs_loc = Config.QLSongsLoc

class QLSongs(object):
    def __init__(self):
        self._songs = None

    def _load_songs(self):
        with open(songs_loc, 'rb') as fobj:
            songs = pickle.load(fobj)
        return songs

    @property
    def songs(self):
        if self._songs is None:
            self._songs = self._load_songs()
        return self._songs

qls = QLSongs()


def main():
    print(len(qls.songs))

    # import sys
    # track = BansheeDb.from_trackid(int(sys.argv[1]))
    # track.tc = 13
    # print(repr(track))
    # track.save()

if __name__ == '__main__':
    main()

import pickle
with open('songs', 'rb') as fobj:
    songs = pickle.load(fobj)
    print(len(songs))
