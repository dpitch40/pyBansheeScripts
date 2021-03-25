import os.path

from .file import read_tracklist
from .web import parse_tracklist_from_url

# Get a track list from a URL or file
def get_track_list(loc, extra_args):
    if os.path.exists(loc):
        tl = read_tracklist(loc, extra_args)
    else:
        tl = parse_tracklist_from_url(loc, extra_args)

    return tl
