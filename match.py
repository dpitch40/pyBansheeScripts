import operator
import argparse
import glob

from mfile import open_music_file
from core.util import sort_key, generate_disc_lens, get_fnames
from parse import get_track_list

def extract_keys(metadata, index, disc_lens=None):
    keys = ['Track#%d' % index]
    album, artist, title, tn, dn = metadata.album, metadata.artist, metadata.title, \
                                    metadata.tn, metadata.dn

    if getattr(metadata, 'location', None):
        keys.append(metadata.location)

    if tn not in (0, None):
        if dn and disc_lens is not None:
            keys.append((artist, album, tn + sum([c for d, c in disc_lens.items() if d < dn])))
        keys.append((artist, album, tn, dn))

    if title:
        keys.append((title, artist, album))

    return keys

# Creates mappings from TrackID/(dn, tn)/(title, artist, album) tuples to MP3s
def create_track_mapping(tracks):
    track_mapping = dict()
    dup_keys = set()

    # Make mapping from disc number to number of tracks on the disc
    disc_lens = generate_disc_lens(tracks)

    for i, track in enumerate(tracks):
        possKeys = extract_keys(track, i, disc_lens)
        
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

def match_metadata_to_files(metadatas, fnames):
    tracks = [open_music_file(fname) for fname in fnames]
    tracks.sort(key=sort_key)

    track_mapping = create_track_mapping(tracks)

    matched = list()
    unmatched_metadatas = list()

    metadata_disc_lens = generate_disc_lens(metadatas)
    for i, metadata in enumerate(sorted(metadatas, key=sort_key)):
        keys = extract_keys(metadata, i, metadata_disc_lens)
        for key in keys:
            if key in track_mapping:
                matched.append((metadata, track_mapping[key]))
                break
        else:
            unmatched_metadatas.append(metadata)

    unmatched_tracks = [t for t in tracks if t not in map(operator.itemgetter(1), matched)]

    return matched, unmatched_metadatas, unmatched_tracks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('metadata_source')
    parser.add_argument('music_dir')

    args = parser.parse_args()

    metadatas = get_track_list(args.metadata_source)
    fnames = get_fnames(args.music_dir)

    matched, unmatched_metadatas, unmatched_tracks = match_metadata_to_files(metadatas, fnames)

    for metadata, track in matched:
        print(track.format())

    print('%d/%d matched' % (len(matched), len(fnames)))

if __name__ == '__main__':
    main()
