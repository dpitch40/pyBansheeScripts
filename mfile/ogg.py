import subprocess

from mutagen.oggvorbis import OggVorbis

import config
from mfile.mutagen_wrapper import MutagenFile
from core.util import int_descriptor, make_numcount_descriptors

class OggFile(MutagenFile):

    ext = '.ogg'

    def mutagen_class(self, fname):
        return OggVorbis(fname)

    def create_decoder(self):
        decoder = subprocess.Popen(["oggdec", "--quiet", "-o", '-', '-R',
                                    '-b', '%d' % config.RawBitsPerSample,
                                    '--endian=%d' % (1 if config.RawEndianness == 'big' else 0),
                                    '--sign=%d' % (1 if config.RawSigned == 'signed' else 0),
                                    self.fname],
                        stdout=subprocess.PIPE)
        return decoder

    @classmethod
    def create_encoder(self, fname, metadata, bitrate):
        tags = list()
        for value, arg in [(metadata.title, '-t'),
                           (metadata.album, '-l'),
                           (metadata.artist, '-a'),
                           (metadata.genre, '-G'),
                           (metadata.year, '-d')]:
            if value is not None:
                tags.extend([arg, str(value)])
        if metadata.tn:
            if metadata.tc:
                tags.extend(['-N', '%d/%d' % metadata.tnc])
            else:
                tags.extend(['-N', str(metadata.tn)])
        if metadata.dn:
            if metadata.dc:
                tags.extend(['-c', 'DISCNUMBER=%d/%d' % metadata.dnc])
            else:
                tags.extend(['-C', 'DISCNUMBER=%s' % metadata.dn])
        for value, arg in [
                           (metadata.album_artist, 'ALBUMARTIST')
                          ]:
            if value is not None:
                tags.extend(['-c', "%s=%s" % (arg, value)])
        encoder = subprocess.Popen(["oggenc", '-Q', '-r', '-b', '%d' % bitrate,
                                    '-o', fname,
                                    '--raw-bits=%d' % config.RawBitsPerSample,
                                    '--raw-chan=%d' % config.RawChannels,
                                    '--raw-rate=%d' % config.RawSampleRate,
                                    '--raw-endianness', '%d' % (1 if config.RawEndianness == 'big' else 0)] +
                                    tags + ['-'], stdin=subprocess.PIPE)
        return encoder

    year = int_descriptor('date')
    tn, tc, tnc = make_numcount_descriptors('tn', 'tc', 'tracknumber')
    dn, dc, dnc = make_numcount_descriptors('dn', 'dc', 'discnumber')

def main():
    import sys
    ogg = OggFile(sys.argv[1])

    # del ogg.dnc
    # ogg.tn = 9
    # ogg.tc = 13
    # del ogg.album_artist
    # ogg.genre = 'Pop/Electronic'
    # ogg.year = 2018
    # ogg.title = 'Heaven/Hell'
    print(ogg.wrapped)
    print(ogg.format())
    print(repr(ogg))
    print(ogg.calculate_fname())
    # ogg.save()

if __name__ == '__main__':
    main()
