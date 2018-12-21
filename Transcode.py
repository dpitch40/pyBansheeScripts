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
from mfile import open_music_file
from mfile.mfile import MusicFile
from parse import get_track_list
from core.track import Track

http_re = re.compile(r'^https?://', flags=re.IGNORECASE)

def convert(infile, outfile, metadata, out_ext, bitrate):
    # Sanity check for bitrate
    if bitrate > 2000:
        bitrate //= 1000
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
        output_tracks = [Track.from_file(fname, default_metadata='db') for fname in get_fnames(oom)]

    matched, unmatched_inputs, unmatched_outputs = match_metadata_to_files(input_files, output_tracks)

    for input_track, output_track in matched:
        fname = input_track.location
        dest = getattr(output_track, 'location', output_track.calculate_fname())

        if not test:
            ext = os.path.splitext(dest)[1]
            encoded = convert(fname, dest, output_track, ext, bitrate)
        else:
            encoded = Metadata.from_dict({'bitrate': bitrate * 1000,
                                          'fsize': int(input_track.length * bitrate / 8)})

        if output_track.db is not None:
            output_track.db.update(encoded, False)

        # Fancy string formatting
        stripped_fname, fname_ext = os.path.splitext(fname)
        stripped_dest, dest_ext = os.path.splitext(dest)
        max_fbase_length = max(len(stripped_fname), len(stripped_dest))

        print('Transcoded %s%s\n        to %s%s with the metadata\n%s' %
                            (stripped_fname.rjust(max_fbase_length), fname_ext,
                             stripped_dest.rjust(max_fbase_length), dest_ext,
                             output_track.format()))

        if output_track.db is not None:
            output_track.db.update(encoded, False)
            for k, v in sorted(output_track.db.changes().items()):
                print('%s\t%s -> %s' % (k, output_track.db.staged.get(k, None), v))
            if not test:
                output_track.db.save()
        print()

    for track in unmatched_inputs:
        print('%s NOT MATCHED' % track.location)
        print()

    if not test:
        config.DefaultDb().commit()

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