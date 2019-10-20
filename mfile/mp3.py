import subprocess

from mutagen.mp3 import MP3
import mutagen.id3 as id3
from mfile.mutagen_wrapper import MutagenFile

import config
from core.util import make_numcount_descriptors, int_descriptor

"""See https://mutagen.readthedocs.io/en/latest/api/id3_frames.html#id3v2-3-4-frames
"""

encoding = id3.Encoding.UTF8

class MP3File(MutagenFile):

    ext = '.mp3'

    def mutagen_class(self, fname):
        return MP3(fname)

    def get_item(self, key):
        value = super(MutagenFile, self).get_item(key)
        if value:
            value = value.text
            if isinstance(value, list) and value:
                value = value[0]
        return value

    def set_item(self, key, value):
        if key in self.wrapped:
            self.wrapped[key].text = [value]
        else:
            frame = getattr(id3, key)(encoding=encoding, text=[value])
            self.wrapped[key] = frame

    def create_decoder(self):
        # decoder = subprocess.Popen(['lame', '--decode', '-t', '--mp3input',
        #                             '--silent',
        #                             self.fname, '-'],
        #                 stdout=subprocess.PIPE)
        # return decoder
        raise NotImplementedError

    @classmethod
    def create_encoder(self, fname, metadata, bitrate):
        tags = list()
        if metadata.title:
            tags.extend(['--tt', metadata.title])
        if metadata.artist:
            tags.extend(['--ta', metadata.artist])
        if metadata.album:
            tags.extend(['--tl', metadata.album])
        if metadata.year:
            tags.extend(['--ty', str(metadata.year)])
        if metadata.tn:
            if metadata.tc:
                tags.extend(['--tn', '%d/%d' % metadata.tnc])
            else:
                tags.extend(['--tn', str(metadata.tn)])
        if metadata.dn:
            if metadata.dc:
                tags.extend(['--tv', 'TPOS=%d/%d' % metadata.dnc])
            else:
                tags.extend(['--tv', 'TPOS=%d' % metadata.dn])
        if metadata.genre:
            tags.extend(['--tg', metadata.genre])

        encoder = subprocess.Popen(["lame", '-r',
                                    '-s', '%s' % (config.RawSampleRate / 1000),
                                    '--bitwidth', str(config.RawBitsPerSample),
                                    '--%s' % config.RawSigned,
                                    '--%s-endian' % config.RawEndianness,
                                    '--silent',
                                    '--noreplaygain',
                                    '-q', '%d' % config.MP3Qual,
                                    '-b', '%d' % bitrate] + tags + ['-', fname], stdin=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL)
        return encoder

    @property
    def album_artist(self):
        choices = [self.get_item('TXXX:QuodLibet::albumartist'),
                   self.get_item('TSO2')]
        if config.AlbumArtistDefault:
            choices.append(self.artist)
        for c in choices:
            if c:
                return c
        return choices[-1]

    @album_artist.setter
    def album_artist(self, value):
        self.set_item('TXXX:QuodLibet::albumartist', value)

    @album_artist.deleter
    def album_artist(self):
        self.del_item('TXXX:QuodLibet::albumartist')
        self.del_item('TSO2')

    tn, tc, tnc = make_numcount_descriptors('tn', 'tc', 'TRCK')
    dn, dc, dnc = make_numcount_descriptors('dn', 'dc', 'TPOS')

    @property
    def year(self):
        return self.get_item('TDRC').year

    @year.setter
    def year(self):
        self.set_item('TDRC', value)

    @year.deleter
    def year(self):
        self.del_item('TDRC')

    mapping = {'title': 'TIT2',
               'title_sort': 'TSOT',
               'artist': 'TPE1',
               'artist_sort': 'TSO2',
               'album': 'TALB',
               'album_sort': 'TSOA',
               'album_artist_sort': 'TSO2',
               'genre': 'TCON'}


def main():
    import sys
    mp3 = MP3File(sys.argv[1])
    # mp3.dnc = (2, 2)
    # mp3.tn = 2
    # mp3.tc = 10
    # del mp3.album_artist
    # mp3.year = 2010
    # mp3.title = 'A Poem by Yeats'
    if 'APIC:' in mp3.wrapped:
        del mp3.wrapped['APIC:']
    if 'APIC:cover' in mp3.wrapped:
        del mp3.wrapped['APIC:cover']
    print(mp3.wrapped, type(mp3.wrapped))
    print(mp3.format())
    print(repr(mp3))
    # mp3.save()

if __name__ == '__main__':
    main()
