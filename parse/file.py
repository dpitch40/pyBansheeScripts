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

tracklist_exclude_cols = ['tnc', 'dnc', 'length']
track_list_conditional_exclude_cols = ['title_sort', 'artist_sort', 'album_sort',
                                       'album_artist_sort', 'dn', 'dc', 'grouping', 'performer']

def to_str_value(v):
    if value_is_none(v):
        return ''
    elif isinstance(v, datetime):
        return v.strftime(ts_fmt)
    else:
        return str(v)

def read_simple_tracklist(fname, extra_args):
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
        year = int(year) if year != '' else None
        track_info = list()
        for row in reader:
            title = row[0]
            length, discnum = 0, None
            if len(row) > 1:
                length = parse_time_str(row[1])
                if len(row) == 3:
                    discnum = int(row[2])
            track_info.append({'title': title, 'length': length * 1000, 'dn': discnum})
    return convert_to_tracks(track_info, artist=artist, album=album, year=year, genre=genre,
        extra=extra_args)

def write_simple_tracklist(fname, tracks, append=False):
    mode = 'a' if append else 'w'
    with open(fname, 'w') as f:
        writer = csv.writer(f, delimiter='\t')
        if not append:
            if tracks[0].genre:
                metadata_row = [tracks[0].artist, tracks[0].album, tracks[0].year, tracks[0].genre]
            else:
                metadata_row = [tracks[0].artist, tracks[0].album, tracks[0].year]
            writer.writerow(metadata_row)

        for track in tracks:
            if track.length is not None:
                mins, secs = divmod(track.length / 1000, 60)
                length_str = '%d:%02d' % (mins, secs)
            else:
                length_str = '0:00'
            if track.dn:
                writer.writerow([track.title, length_str, track.dn])
            else:
                writer.writerow([track.title, length_str])

# Reads a track list from a file
def read_tracklist(fname, extra_args):
    if fname.lower().endswith('.txt'):
        return read_simple_tracklist(fname, extra_args)
    with open(fname, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t' if fname.lower().endswith('.tsv') else ',')
        tracks = list()
        for row in reader:
            for k, v in row.items():
                row[k] = convert_str_value(v, k not in strKeys)
            row.update(extra_args)
            tracks.append(Metadata.from_dict(row))
    return tracks

# Writes a track list to a file
def write_tracklist(fname, tracks, append):
    if fname.lower().endswith('.txt'):
        return write_simple_tracklist(fname, tracks, append)
    appending = append and os.path.isfile(fname) and os.path.getsize(fname) > 0
    if not appending:
        columns = [c for c in tracks[0].all_keys if c not in tracklist_exclude_cols]
        for c in track_list_conditional_exclude_cols:
            if all(getattr(t, c) is None for t in tracks):
                columns.remove(c)
    mode = 'a+' if appending else 'w'
    with open(fname, mode) as f:
        if appending:
            f.seek(0, 0)
            reader = csv.reader(f)
            columns = reader.__next__()
            f.seek(0, 2)

        writer = csv.DictWriter(f, columns, delimiter='\t' if fname.lower().endswith('.tsv') else ',')
        if not appending:
            writer.writeheader()
        for track in tracks:
            writer.writerow(dict([(k, to_str_value(v)) for k, v in track.to_dict().items() if k in columns]))
