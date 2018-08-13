import operator
import argparse
import glob

from mfile import open_music_file
from db import open_db
from core.util import sort_key, generate_disc_lens, get_fnames
from parse import get_track_list
from core.track import Track

def _extract_keys(metadata, index, disc_lens=None, get_all_keys=False):
    keys = list()
    album, artist, title, tn, dn = metadata.album, metadata.artist, metadata.title, \
                                    metadata.tn, metadata.dn
    album = album.lower() if album else ''
    artist = artist.lower() if artist else ''
    title = title.lower() if title else ''

    if getattr(metadata, 'location', None):
        keys.append(metadata.location)

    if title or get_all_keys:

        if tn not in (0, None):
            if dn and disc_lens is not None:
                keys.append((title, artist, album, tn + sum([c for d, c in disc_lens.items() if d < dn])))
            keys.append((title, artist, album, tn, dn))

        keys.append((title, artist, album))

    if not title or get_all_keys:
        keys.append('Track#%d' % index)

        if tn not in (0, None):
            if dn and disc_lens is not None:
                keys.append((artist, album, tn + sum([c for d, c in disc_lens.items() if d < dn])))
            keys.append((artist, album, tn, dn))

    return keys

# Creates mappings from TrackID/(dn, tn)/(title, artist, album) tuples to MP3s
def _create_track_mapping(tracks):
    track_mapping = dict()
    dup_keys = set()

    # Make mapping from disc number to number of tracks on the disc
    disc_lens = generate_disc_lens(tracks)

    for i, track in enumerate(tracks):
        possKeys = _extract_keys(track, i, disc_lens)
        
        # Ensure each mapping key is unique across all tracks
        for k in possKeys:
            if k in dup_keys:
                continue
            elif k in track_mapping:
                del track_mapping[k]
                dup_keys.add(k)
            else:
                track_mapping[k] = track

    return track_mapping

def match_metadata_to_files(fnames, metadatas, use_db=False):
    default_metadata = 'db' if use_db else 'mfile'
    tracks = [Track.from_file(fname, default_metadata=default_metadata) for fname in fnames]
    return match_metadata_to_tracks(metadatas, tracks)

def match_metadata_to_tracks(tracks, metadatas):
    tracks.sort(key=sort_key())

    track_mapping = _create_track_mapping(tracks)

    matched = list()
    unmatched_metadatas = list()

    metadata_disc_lens = generate_disc_lens(metadatas)
    for i, metadata in enumerate(sorted(metadatas, key=sort_key())):
        keys = _extract_keys(metadata, i, metadata_disc_lens, True)
        for key in keys:
            if key in track_mapping:
                matched.append((track_mapping[key], metadata))
                # print('--- MATCHED on %s' % str(key))
                break
        else:
            unmatched_metadatas.append(metadata)

    unmatched_tracks = [t for t in tracks if t not in map(operator.itemgetter(0), matched)]

    return matched, unmatched_tracks, unmatched_metadatas

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('metadata_source')
    parser.add_argument('music_dir')
    parser.add_argument('--use-db', action='store_true')

    args = parser.parse_args()

    metadatas = get_track_list(args.metadata_source)
    fnames = get_fnames(args.music_dir)

    matched, unmatched_metadatas, unmatched_files = match_metadata_to_files(metadatas, fnames, args.use_db)

    for metadata, track in matched:
        print(metadata.format())
        print(track.format())
        print()

    print('%d/%d matched' % (len(matched), len(fnames)))

if __name__ == '__main__':
    main()
