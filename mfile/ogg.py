import subprocess
import string

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
    def create_encoder(self, fname, metadata, bitrate, infile=None):
        tags = list()
        for value, arg in [(metadata['title'], '-t'),
                           (metadata['album'], '-l'),
                           (metadata['artist'], '-a'),
                           (metadata['genre'], '-G'),
                           (metadata['year'], '-d')]:
            if value is not None:
                tags.extend([arg, str(value)])
        if metadata.get('tn', None) is not None:
            tags.extend(['-c', 'tracknumber=%s' % metadata['tn']])
            if metadata.get('tc', None) is not None:
                tags.extend(['-c', 'tracktotal=%d' % metadata['tc']])
        if metadata.get('dn', None) is not None:
            tags.extend(['-c', 'discnumber=%s' % metadata['dn']])
            if metadata.get('dc', None) is not None:
                tags.extend(['-c', 'disctotal=%d' % metadata['dc']])
        for value, arg in [
                           ('album_artist', 'ALBUMARTIST')
                          ]:
            if metadata.get(value, None) is not None:
                tags.extend(['-c', "%s=%s" % (arg, metadata[value])])
        func, kwargs, infile = (subprocess.Popen, {"stdin": subprocess.PIPE}, "") \
            if infile is None else subprocess.run, {}, infile
        args = ["oggenc", '-Q', '-b', '%d' % bitrate, '-o', fname]
        if infile is None:
            args.extend(['-r',
                         '--raw-bits=%d' % config.RawBitsPerSample,
                         '--raw-chan=%d' % config.RawChannels,
                         '--raw-rate=%d' % config.RawSampleRate,
                         '--raw-endianness', '%d' % (1 if config.RawEndianness == 'big' else 0)])
        args.extend(tags + [infile])
        encoder = func(args, **kwargs)
        return encoder

    year = int_descriptor('date')
    tn = int_descriptor('tracknumber')
    tc = int_descriptor('tracktotal')
    dn = int_descriptor('discnumber')
    dc = int_descriptor('disctotal')

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
    fname = ogg.calculate_fname()
    print(fname)
    for c in fname:
        if c in string.printable:
            continue
        print(c, repr(c), '%x' % ord(c), c.encode('utf8'))
    # ogg.save()

if __name__ == '__main__':
    main()
