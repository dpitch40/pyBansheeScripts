import re

from core.metadata import Metadata

#regex for times
time_re = re.compile(r"(\d+):(\d{2})")
tuple_re = re.compile(r"\(([^\)]+)\)")

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

def convert_str_value(v, convertNumbers=True):
    if v == '' or v == "None" or v is None:
        return None
    elif isinstance(v, str) and convertNumbers and v.isdigit():
        return int(v)
    else:
        m = tuple_re.match(v)
        if m:
            return tuple(map(lambda x: convert_str_value(x.strip()), m.group(1).split(',')))

    return v

def convert_to_tracks(info_list, **kwargs):
    """Converts a list of (title, length, disc_num) tuples and extra metadata kwargs to a list of
       Metadata objects."""
    disc_num = None
    track_num = 1
    tracks_per_disc = dict()
    tracks = list()
    for track_info in info_list:
        if track_info[2] != disc_num:
            if disc_num is not None:
                tracks_per_disc[disc_num] = track_num - 1
            track_num = 1
        title, length, disc_num = track_info
        length = parse_time_str(length)
        if length is not None:
            length *= 1000

        d = {'title': title,
             'length': length,
             'tn': track_num,
             'dn': disc_num}
        d.update(kwargs)
        tracks.append(Metadata(d))
        track_num += 1

    tracks_per_disc[disc_num] = track_num - 1
    for track in tracks:
        track.tc = tracks_per_disc[track.dn]
        track.dc = disc_num

    return tracks
