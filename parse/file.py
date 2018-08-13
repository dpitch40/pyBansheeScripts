import os.path
import csv
from io import StringIO
from collections import defaultdict
from collections.abc import Iterable
from core.metadata import Metadata
from .util import convert_to_tracks, parse_time_str
from core.util import convert_str_value

strKeys = {'album_artist', 'album_artist_sort', 'album', 'album_sort', 'artist', 'artist_sort',
           'genre', 'title', 'title_sort'}

def to_str_value(v):
    if v is None or (isinstance(v, Iterable) and all(sv is None for sv in v)):
        return ''
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
def read_tracklist(fName):
    if fName.lower().endswith('.txt'):
        return read_simple_tracklist(fName)
    with open(fName, 'r') as f:
        reader = csv.DictReader(f)
        tracks = list()
        for row in reader:
            for k, v in row.items():
                row[k] = convert_str_value(v, k not in strKeys)
            tracks.append(Metadata.from_dict(row))
    return tracks

# Writes a track list to a file
def write_tracklist(fName, tracks):
    if fName.lower().endswith('.txt'):
        return write_simple_tracklist(fName, tracks)
    with open(fName, 'w') as f:
        writer = csv.DictWriter(f, tracks[0].all_keys)
        writer.writeheader()
        for track in tracks:
            writer.writerow(dict([(k, to_str_value(v)) for k, v in track.to_dict().items()]))
    return tracks
