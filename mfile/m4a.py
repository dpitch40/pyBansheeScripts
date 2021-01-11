import subprocess
from datetime import datetime

from mutagen.mp4 import MP4

import config
from mfile.mutagen_wrapper import MutagenFile
from core.util import int_descriptor, make_numcount_descriptors

class M4AFile(MutagenFile):

    ext = '.m4a'
    mapping = {'title': '\xa9nam',
               'title_sort': 'sonm',
               'artist': '\xa9ART',
               'artist_sort': 'soar',
               'album': '\xa9alb',
               'album_sort': 'soal',
               'album_artist': 'aART',
               'album_artist_sort': 'soaa',
               'genre': '\xa9gen',
               'tnc': 'trkn',
               'dnc': 'disk'}

    def mutagen_class(self, fname):
        return MP4(fname)

    @property
    def year(self):
        raw = self.get_item('\xa9day')
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return datetime.strptime(raw, '%Y-%m-%dT%H:%M:%SZ').year
        return int(self.get_item('\xa9day'))

    @year.setter
    def year(self, value):
        self.set_item('\xa9day', str(value))

    @year.deleter
    def year(self):
        self.del_item('\xa9day')

    @property
    def tn(self):
        trkn = self.get_item('trkn')
        if trkn is not None:
            return trkn[0]
        else:
            return None

    @tn.setter
    def tn(self, value):
        self.set_item('trkn', (value, self.get_item('trkn')[1]))

    @tn.deleter
    def tn(self):
        self.del_item('trkn')

    @property
    def tc(self):
        trkn = self.get_item('trkn')
        if trkn is not None:
            return trkn[1]
        else:
            return None

    @tc.setter
    def tc(self, value):
        self.set_item('trkn', (self.get_item('trkn')[0], value))

    @tc.deleter
    def tc(self):
        self.set_item('trkn', (self.get_item('trkn')[0], None))


    @property
    def dn(self):
        disk = self.get_item('disk')
        if disk is not None:
            return disk[0]
        else:
            return None

    @dn.setter
    def dn(self, value):
        self.set_item('disk', (value, self.get_item('disk')[1]))

    @dn.deleter
    def dn(self):
        self.del_item('disk')

    @property
    def dc(self):
        disk = self.get_item('disk')
        if disk is not None:
            return disk[1]
        else:
            return None

    @dc.setter
    def dc(self, value):
        self.set_item('disk', (self.get_item('disk')[0], value))

    @dc.deleter
    def dc(self):
        self.set_item('disk', (self.get_item('disk')[0], None))

    def create_decoder(self):
        raise NotImplementedError

    @classmethod
    def create_encoder(self, fname, metadata, bitrate):
        raise NotImplementedError

def main():
    import sys
    m4a = M4AFile(sys.argv[1])

    # del m4a.dnc
    # m4a.tn = 9
    # m4a.tc = 13
    # del m4a.album_artist
    # m4a.genre = 'Pop/Electronic'
    # m4a.year = 2018
    # m4a.title = 'Heaven/Hell'
    # print(m4a.wrapped)
    print(m4a.format())
    print(repr(m4a))
    print(m4a.calculate_fname())
    # m4a.save()

if __name__ == '__main__':
    main()
