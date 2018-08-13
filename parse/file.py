import os.path
import csv
from datetime import datetime
from io import StringIO
from collections import defaultdict
from core.metadata import Metadata
from .util import convert_to_tracks, parse_time_str
from core.util import convert_str_value, value_is_none, ts_fmt

strKeys = {'album_artist', 'album_artist_sort', 'album', 'album_sort', 'artist', 'artist_sort',
           'genre', 'title', 'title_sort'}

tracklist_exts = ('.tsv', '.csv', '.txt')

def to_str_value(v):
    if value_is_none(v):
        return ''
    elif isinstance(v, datetime):
        return v.strftime(ts_fmt)
    else:
        return str(v)

def read_simple_tracklist(fname):
    """Reads a tracklist consisting of a row of metadata followed
by rows of track data."""
    with open(fname, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        metadata_row = next(reader)
        if len(metadata_row) == 4:
            artist, album, year, genre = metadata_row
        else:
            artist, album, year = metadata_row
            genre = None
        year = int(year)
        track_info = list()
        for row in reader:
            title = row[0]
            length, discnum = 0, None
            if len(row) > 1:
                length = parse_time_str(row[1])
                if len(row) == 3:
                    discnum = int(row[2])
            track_info.append((title, length * 1000, discnum))
    return convert_to_tracks(track_info, artist=artist, album=album, year=year, genre=genre)

def write_simple_tracklist(fname, tracks):
    with open(fname, 'w') as f:
        writer = csv.writer(f, delimiter='\t')
        if tracks[0].genre:
            metadata_row = [tracks[0].artist, tracks[0].album, tracks[0].year, tracks[0].genre]
        else:
            metadata_row = [tracks[0].artist, tracks[0].album, tracks[0].year]
        writer.writerow(metadata_row)

        for track in tracks:
            mins, secs = divmod(track.length / 1000, 60)
            length_str = '%d:%02d' % (mins, secs)
            if track.dn:
                writer.writerow([track.title, length_str, track.dn])
            else:
                writer.writerow([track.title, length_str])

# Reads a track list from a file
def read_tracklist(fname):
    if fname.lower().endswith('.txt'):
        return read_simple_tracklist(fname)
    with open(fname, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t' if fname.lower().endswith('.tsv') else ',')
        tracks = list()
        for row in reader:
            for k, v in row.items():
                row[k] = convert_str_value(v, k not in strKeys)
            tracks.append(Metadata.from_dict(row))
    return tracks

# Writes a track list to a file
def write_tracklist(fname, tracks):
    if fname.lower().endswith('.txt'):
        return write_simple_tracklist(fname, tracks)
    with open(fname, 'w') as f:
        writer = csv.DictWriter(f, tracks[0].all_keys, delimiter='\t' if fname.lower().endswith('.tsv') else ',')
        writer.writeheader()
        for track in tracks:
            writer.writerow(dict([(k, to_str_value(v)) for k, v in track.to_dict().items()]))
