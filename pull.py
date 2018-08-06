import csv
import argparse
import os.path

from parse import get_track_list
from parse.file import write_tracklist
from parse.util import convert_str_value

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Get a track list from an external source.")
    parser.add_argument("location", help="The location (URL or file) to get metadata from.")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                                help="Specify extra data fields for these tracks.")
    parser.add_argument('-o', "--out", help="Output to a file.")
    args = parser.parse_args()

    tl = get_track_list(args.location)

    extra_args = dict([(k, convert_str_value(v)) for k, v in args.extra])
    for track in tl:
        for k, v in extra_args.items():
            setattr(track, k, v)

    for track in tl:
        print(track)

    if args.out:
        write_tracklist(args.out, tl)
