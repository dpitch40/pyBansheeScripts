import os
import os.path
import argparse
import re
from concurrent.futures import ProcessPoolExecutor
import operator
from itertools import repeat

# from mutagen.mp3 import MP3
# from EasyID3Custom import EasyID3Custom as EasyID3

from mfile import open_music_file, mapping as mfile_mapping
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

def convert(infile, outfile, metadata, out_ext, bitrate, test):
    if not test:
        # Sanity check for bitrate
        if bitrate > 2000:
            bitrate //= 1000
        in_md = open_music_file(infile)
        decoder = in_md.create_decoder()

        if os.path.exists(outfile):
            os.remove(outfile)

        if decoder is None:
            mfile_mapping[out_ext].create_encoder(outfile, metadata, bitrate, infile=infile)
        else:
            encoder = mfile_mapping[out_ext].create_encoder(outfile, metadata, bitrate)

            decodedData, errs = decoder.communicate()
            encoder.communicate(decodedData)

    return outfile

def transcode(input_files, oom, bitrate, test):

    input_files = get_fnames(input_files)

    output_tracks = list()
    if os.path.isfile(oom) or http_re.match(oom):
        output_tracks = [Track.from_metadata(m, match_to_existing=False) for m in get_track_list(oom, {})]
    else:
        output_tracks = [Track.from_file(fname, default_metadata='db') for fname in get_fnames(oom)]

    matched, unmatched_inputs, unmatched_outputs = match_metadata_to_files(input_files, output_tracks)

    matched_inputs, matched_outputs = list(zip(*matched))
    metadatas = [o.to_dict() for o in matched_outputs]
    sources = list(map(operator.attrgetter('location'), matched_inputs))
    dests = list()
    for o in matched_outputs:
        if getattr(o, 'location', None) is None or not o.location.startswith(config.MusicDir):
            dests.append(o.calculate_fname(ext=config.DefaultEncodeExt))
        else:
            dests.append(o.location)
    output_dir = os.path.dirname(dests[0])
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    exts = [os.path.splitext(dest)[1] for dest in dests]

    with ProcessPoolExecutor() as executor:
        for (input_track, output_track), fname, dest, _ in \
            zip(matched, sources, dests, executor.map(convert, sources, dests, metadatas,
                                                      exts, repeat(bitrate), repeat(test))):

            if not test:
                encoded = open_music_file(dest)
            else:
                encoded = Metadata.from_dict({'bitrate': bitrate * 1000,
                                              'fsize': int(input_track.length * bitrate / 8)})

            if output_track.db is not None:
                output_track.db.update(encoded, False)

            # Fancy string formatting
            stripped_fname, fname_ext = os.path.splitext(fname)
            stripped_dest, dest_ext = os.path.splitext(dest)
            replace_str = ' (replacing)' if os.path.isfile(dest) else ''
            max_fbase_length = max(len(stripped_fname), len(stripped_dest))

            print('Transcoded %s%s\n        to %s%s%s with the metadata\n%s' %
                                (stripped_fname.rjust(max_fbase_length), fname_ext,
                                 stripped_dest.rjust(max_fbase_length), dest_ext,
                                 replace_str, output_track.format()))

            if output_track.db is not None:
                output_track.db.update(encoded, False)
                for k, v in sorted(output_track.db.changes().items()):
                    print('%s\t%s -> %s' % (k, output_track.db.staged.get(k, None), v))
                if not test:
                    output_track.db.save()
            print()

    for track in unmatched_inputs:
        print('Input %s NOT MATCHED' % track.location)
        print()

    for track in unmatched_outputs:
        print('Output %s NOT MATCHED' % track.title)
        print()

    if not test:
        config.DefaultDb().commit()

    print('%d out of %d/%d matched' % (len(matched), len(input_files), len(output_tracks)))

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