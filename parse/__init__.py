import csv
import argparse
import Config
import os.path

from .web import parse_tracklist_from_url

# Get a track list from a URL or file
def get_track_list(loc, **kwargs):
    if os.path.exists(loc):
        if loc.endswith(".csv"):
            tl = readAugmentedTrackList(loc)
        else:
            tl = readSimpleTrackList(loc)
    else:
        tl = parse_tracklist_from_url(loc)

    # Convert kwargs
    # for k, v in kwargs.items():
    #     kwargs[k] = Util.convertStrValue(v)
    # if isinstance(tl[0], dict):
    #     map(lambda r: r.update(kwargs), tl)
    # else:
    #     if "Genre" in kwargs and len(tl[0]) == 3:
    #         tl[0] = tl[0] + (kwargs["Genre"],)

    return tl

# # Gets a track list from the specified location; makes sure it is augmented
# def getAugmentedTrackList(loc, **kwargs):
#     tl = get_track_list(loc, **kwargs)
#     if not isinstance(tl[0], dict):
#         tl = augmentTrackList(tl)
#     return tl

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Get a track list from an external source.")
    parser.add_argument("location", help="The location (URL or file) to get metadata from.")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                                help="Specify extra data fields for these tracks.")
    parser.add_argument('-o', "--out", help="Output to a file.")
    parser.add_argument('-s', "--simple", action="store_true",
                help="Use the simple tracklist format.")
    args = parser.parse_args()

    tl = get_track_list(args.location, **dict(args.extra))
    for track in tl:
        print(track)
    # simpleTracklist = not isinstance(tl[0], dict)

    # if args.simple:
    #     if not simpleTracklist:
    #         tl = simplifyTrackList(tl)
    #     def encodeRowElement(r):
    #         if isinstance(r, unicode):
    #             return r.encode(Config.UnicodeEncoding)
    #         else:
    #             return r
    #     tl = map(lambda row: map(encodeRowElement, row), tl)
    #     if args.out:
    #         with open(args.out, 'w') as f:
    #             writer = csv.writer(f, delimiter='\t', lineterminator='\n')
    #             writer.writerows(tl)
    #     else:
    #         print '\n'.join(['\t'.join(map(str, l)) for l in tl])
    # else:
    #     if simpleTracklist: # Augment the tracklist
    #         tl = augmentTrackList(tl)

    #     if args.out:
    #         with open(args.out, 'w') as f:
    #             formatTrackList(tl, f)
    #     else:
    #         print formatTrackList(tl).strip()
