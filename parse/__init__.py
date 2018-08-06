import os.path

from .file import read_tracklist
from .web import parse_tracklist_from_url

# Get a track list from a URL or file
def get_track_list(loc):
    if os.path.exists(loc):
        tl = read_tracklist(loc)
    else:
        tl = parse_tracklist_from_url(loc)

    return tl
