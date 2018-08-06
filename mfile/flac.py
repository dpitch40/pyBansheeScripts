import subprocess

from mutagen.flac import FLAC

import config
from mfile.mutagen_wrapper import MutagenFile
from core.util import int_descriptor

class FlacFile(MutagenFile):

    ext = '.flac'

    mapping = {'album_artist': 'albumartist',
               'album_artist_sort': 'albumartistsort',
               'album_sort': 'albumsort',
               'artist_sort': 'artistsort',
               'title_sort': 'titlesort',
               'tn': 'tracknumber',
               'tc': 'totaltracks',
               'dn': 'discnumber',
               'dc': 'totaldiscs'}

    def mutagen_class(self, fname):
        return FLAC(fname)

    def create_decoder(self):
        decoder = subprocess.Popen(["flac", '--force-raw-format',
                                    "--decode",
                                    "--silent",
                                    "--stdout",
                                    '--endian=%s' % config.RawEndianness,
                                    '--sign=%s' % config.RawSigned,
                                    self.fname],
                        stdout=subprocess.PIPE)
        return decoder

    @classmethod
    def create_encoder(self, fname, metadata, bitrate):
        # Ignores bitrate parameter
        tags = list()
        # See https://www.xiph.org/vorbis/doc/v-comment.html
        for value, fieldname in [(metadata.title, 'TITLE'),
                                 (metadata.tn, 'TRACKNUMBER'),
                                 (metadata.tc, 'TOTALTRACKS'),
                                 (metadata.dn, 'DISCNUMBER'),
                                 (metadata.dc, 'TOTALDISCS'),
                                 (metadata.album, 'ALBUM'),
                                 (metadata.artist, 'ARTIST'),
                                 (metadata.genre, 'GENRE'),
                                 (metadata.year, 'DATE'),
                                 (metadata.album_artist, 'ALBUMARTIST')]:
            if value is not None:
                tags.append('--tag=%s=%s' % (fieldname, value))
        encoder = subprocess.Popen(["flac", '--force-raw-format', '--silent',
                                    '-' + str(config.FlacCompLevel),
                                    '-o', fname,
                                    '--endian=%s' % config.RawEndianness,
                                    '--bps=%d' % config.RawBitsPerSample,
                                    '--sign=%s' % config.RawSigned,
                                    '--channels=%d' % config.RawChannels,
                                    '--sample-rate=%d' % config.RawSampleRate] +
                                    tags +
                                    ['-'], stdin=subprocess.PIPE)
        return encoder

    year = int_descriptor('date')
    tn = int_descriptor('tracknumber')
    tc = int_descriptor('totaltracks')
    dn = int_descriptor('discnumber')
    dc = int_descriptor('totaldiscs')

def main():
    import sys
    flac = FlacFile(sys.argv[1])

    # del flac.dnc
    # flac.tn = 9
    # flac.tc = 13
    # del flac.album_artist
    # flac.genre = 'Pop/Electronic'
    # flac.year = 2018
    # flac.title = 'Heaven/Hell'
    print(flac.wrapped)
    print(flac.format())
    print(repr(flac))
    # flac.save()

if __name__ == '__main__':
    main()
