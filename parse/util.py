import re
from datetime import datetime

from bs4.element import NavigableString

from core.metadata import Metadata

#regex for times
time_re = re.compile(r"(\d+):(\d{2})")

year_fmts = ['%Y', '%d %b %Y', '%b %d, %Y', '%b %Y', '%m/%d/%Y']

def parse_time_str(time_str):
    if not isinstance(time_str, str):
        return time_str
    elif time_str.isdigit():
        return int(time_str)

    m = time_re.match(time_str)
    if m:
        return 60 * int(m.group(1)) + int(m.group(2))
    else:
        return None

def parse_date_str(s):
    if s:
        for fmt_str in year_fmts:
            try:
                year = datetime.strptime(s, fmt_str)
            except ValueError:
                pass
            else:
                return year.year
    return None

def convert_to_tracks(info_list, **kwargs):
    """Converts a list of (title, artist, length, disc_num) tuples and extra metadata kwargs to a list of
       Metadata objects."""
    kwargs = dict([(k, str(v) if isinstance(v, NavigableString) else v) for k, v in kwargs.items()])
    # Fill in artist/album artist
    album_artist = kwargs.get('albumartist', None)
    if album_artist is None:
        album_artist = kwargs['artist']
    artists = [t.get('artist', None) for t in info_list]
    if any(artists):
        if all([a == album_artist for a in artists]):
            kwargs['artist'] = album_artist
            kwargs.pop('albumartist', None)
        else:
            kwargs['albumartist'] = album_artist
    else:
        kwargs['artist'] = album_artist
        kwargs.pop('albumartist', None)
    disc_num = None
    track_num = 1
    tracks_per_disc = dict()
    tracks = list()
    for track_info in info_list:
        dn = track_info.get('dn', None)
        if dn != disc_num:
            if disc_num is not None:
                tracks_per_disc[disc_num] = track_num - 1
            disc_num = dn
            track_num = 1
        length = parse_time_str(track_info.get('length', 0))
        if length is not None:
            length *= 1000

        track_info.update({'length': length,
                           'tn': track_num})
        track_info.update(kwargs)
        tracks.append(Metadata(track_info))
        track_num += 1

    tracks_per_disc[disc_num] = track_num - 1
    for track in tracks:
        track.tc = tracks_per_disc[track.dn]
        track.dc = disc_num

    return tracks
