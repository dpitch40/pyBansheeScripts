import os
import os.path
import argparse
import re
from mfile import open_music_file, mapping as mfile_mapping

# from mutagen.mp3 import MP3
# from EasyID3Custom import EasyID3Custom as EasyID3

import config
from core.metadata import Metadata
from core.util import get_fnames
from db.db import MusicDb
from match import match_metadata_to_files
from mfile.mfile import MusicFile
from parse import get_track_list
from track import Track

http_re = re.compile(r'^https?://', flags=re.IGNORECASE)

def convert(infile, outfile, metadata, out_ext, bitrate):
    in_md = open_music_file(infile)
    decoder = in_md.create_decoder()

    if os.path.exists(outfile):
        os.remove(outfile)
    encoder = mfile_mapping[out_ext].create_encoder(outfile, metadata, bitrate)

    decodedData, errs = decoder.communicate()
    encoder.communicate(decodedData)

    encoded = open_music_file(outfile)
    return encoded

def transcode(input_files, oom, bitrate, test):

    input_files = get_fnames(input_files)

    output_tracks = list()
    if os.path.isfile(oom) or http_re.match(oom):
        output_tracks = [Track.from_metadata(m) for m in get_track_list(oom)]
    else:
        output_tracks = [Track.from_file(fname) for fname in get_fnames(oom)]
    output_metadatas = [t.db or t.mfile or t.other for t in output_tracks]

    matched, unmatched_tracks, unmatched_files = match_metadata_to_files(output_metadatas, input_files)

    for fname in input_files:
        if fname in matched:
            metadata = matched[fname]
            dest = getattr(metadata, 'location', metadata.calculate_fname())
            print('Transcoding %s\n         to %s with the metadata\n%s' %
                                (fname, dest, metadata.format()))

            if not test:
                ext = os.path.splitext(dest)[1]
                encoded = convert(fname, dest, metadata, ext, bitrate)
            else:
                encoded = MusicFile(dest, {'bitrate': bitrate * 1000})

            if isinstance(metadata, MusicDb):
                metadata.update(encoded, False)
                for k, v in sorted(metadata.changes().items()):
                    print('%s\t-> %s' % (k, v))
                if not test:
                    metadata.save()
        else:
            print('%s NOT MATCHED' % fname)
        print()
    if not test:
        config.DefaultDb.commit()

    print('%d/%d matched' % (len(matched), len(input_files)))

def main():
    parser = argparse.ArgumentParser(description="Transcode a set of music files.")
    parser.add_argument("-b", "--bitrate", type=int, default=config.DefaultCDBitrate,
                        help="The bitrate to encode to")
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument("input", help="Specify the files/directory of files to encode from.")
    parser.add_argument('output_or_metadata', help='Either the files/directory of files to overwrite, '
                            'or the location of metadata describing the tracks.')

    args = parser.parse_args()

    transcode(args.input, args.output_or_metadata, args.bitrate, args.test)

if __name__ == "__main__":
    main()