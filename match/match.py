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
    albumartist = metadata.album_artist
    albumartist = albumartist.lower() if albumartist else ''
    album = album.lower() if album else ''
    artist = artist.lower() if artist else ''
    title = title.lower() if title else ''

    if getattr(metadata, 'location', None):
        keys.append(metadata.location)

    if title or get_all_keys:

        if tn not in (0, None):
            keys.append((title, artist, album, tn, dn))
            if albumartist != '' and albumartist != artist:
                keys.append((title, albumartist, album, tn, dn))
            if dn is not None and len(disc_lens) == 1:
                keys.append((title, artist, album, tn, None))
                if albumartist != '' and albumartist != artist:
                    keys.append((title, albumartist, album, tn, None))
            if dn and disc_lens is not None:
                keys.append((title, artist, album, tn + sum([c for d, c in disc_lens.items() if d < dn])))
                if albumartist != '' and albumartist != artist:
                    keys.append((title, albumartist, album, tn + sum([c for d, c in disc_lens.items() if d < dn])))

    if not title or get_all_keys:
        if tn not in (0, None):
            keys.append((artist, album, tn, dn))
            if albumartist != '' and albumartist != artist:
                keys.append((albumartist, album, tn, dn))
            if dn is not None and len(disc_lens) == 1:
                keys.append((artist, album, tn, None))
                if albumartist != '' and albumartist != artist:
                    keys.append((albumartist, album, tn, None))
            if dn and disc_lens is not None:
                keys.append((artist, album, tn + sum([c for d, c in disc_lens.items() if d < dn])))
                if albumartist != '' and albumartist != artist:
                    keys.append((albumartist, album, tn + sum([c for d, c in disc_lens.items() if d < dn])))

        keys.append('Track#%d' % index)

    if title or get_all_keys:
        keys.append((title, artist, album))
        if albumartist != '' and albumartist != artist:
            keys.append((title, albumartist, album))

    return keys

# Creates mappings from TrackID/(dn, tn)/(title, artist, album) tuples to MP3s
def _create_track_mapping(metadatas):
    track_mapping = dict()
    dup_keys = set()

    # Make mapping from disc number to number of tracks on the disc
    disc_lens = generate_disc_lens(metadatas)

    for i, track in enumerate(metadatas):
        possKeys = _extract_keys(track, i, disc_lens, True)
        
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
    return match_metadata_to_tracks(tracks, metadatas)

def match_metadata_to_tracks(m1, m2, order_by_source=False):
    # tracks.sort(key=sort_key())

    # Enforce m1 being larger than m2
    switched = len(m1) < len(m2)
    track_key = 0
    if switched:
        m1, m2 = m2, m1
        track_key = 1

    track_mapping = _create_track_mapping(m1)
    # print('\n'.join(sorted(map(str, track_mapping.keys()))))

    matched = list()
    unmatched_2 = list()

    metadata_disc_lens = generate_disc_lens(m2)
    for i, metadata in enumerate(sorted(m2, key=sort_key())):
        keys = _extract_keys(metadata, i, metadata_disc_lens, True)
        # print(metadata)
        # for key in keys:
        #     print('\t', key)
        for key in keys:
            if key in track_mapping:
                if switched:
                    matched.append((metadata, track_mapping[key]))
                else:
                    matched.append((track_mapping[key], metadata))
                # print('--- MATCHED on %s' % str(key))
                break
        else:
            unmatched_2.append(metadata)

    if order_by_source:
        matched = sorted(matched, key=lambda x: m1.index(x[track_key]))

    unmatched_1 = [t for t in m1 if t not in map(operator.itemgetter(track_key), matched)]

    if switched:
        unmatched_1, unmatched_2 = unmatched_2, unmatched_1
    return matched, unmatched_1, unmatched_2

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
