import os.path
import shutil
import os
import argparse

from core.util import compare_filesets
import config
from urllib.parse import quote

playlists_dir = os.path.join(os.path.dirname(config.QLSongsLoc), 'playlists')

def quick_sync(p_file, dest_dir, flat, delete, test):
    from mfile import open_music_file

    # Get list of files currently in the destination directory
    cur_files = list()
    for dirpath, dirnames, filenames in os.walk(dest_dir):
        cur_files.extend([os.path.join(dirpath, fname) for fname in filenames])

    locs = open(p_file, 'r').read().strip().split('\n')
    # Get a mapping from track destinations to their current locations
    dests_to_locs = dict()
    for loc in locs:
        mfile = open_music_file(loc)
        dest = mfile.calculate_fname(dest_dir, nested=not flat)
        dests_to_locs[dest] = loc

    _sync(dests_to_locs, cur_files, delete, test)

def _sync(dests_to_locs, cur_files, delete, test):
    # Take the intersection/differences of the two sets of files
    to_sync, current, to_remove = compare_filesets(dests_to_locs.keys(), cur_files)
    to_sync.sort()
    to_remove.sort()

    if to_sync:
        cur_album = None
        print("Syncing:\n")
        for dest in to_sync:
            album_path = os.path.dirname(dest)
            if album_path != cur_album:
                cur_album = album_path
                print(album_path)
            if not test:
                if not os.path.exists(album_path):
                    os.makedirs(album_path)
                shutil.copy(dests_to_locs[dest], dest)
            print('\t', dest)

    if delete:
        if to_remove:
            if to_sync:
                print('\n')
            cur_album = None
            print("Removing:\n\n")
            for fname in to_remove:
                album_path = os.path.dirname(fname)
                if album_path != cur_album:
                    cur_album = album_path
                    print(album_path)
                if not test:
                    os.remove(fname)
                    os.removedirs(album_path)
                print('\t', fname)
        print("\nSyncing %d, removing %d" % (len(to_sync), len(to_remove)))
    else:
        print("\nSyncing %d" % len(to_sync))


def main():
    parser = argparse.ArgumentParser(description="Sync the contents of a playlist to a "
                    "directory. (e.g. on a flash drive)")
    parser.add_argument("playlist", help="The name of the playlist to sync.")
    parser.add_argument("destdir", help="The directory to sync the playlist to.")
    parser.add_argument('-f', "--flat", action="store_true",
            help="Store the playlist contents in flat format, without nesting by artist "
                "and album.")
    parser.add_argument('-d', "--delete", action="store_true",
        help="Delete contents of the destination directory that isn't "
                             "part of the playlist being synced")
    parser.add_argument("-t", "--test", action="store_true", help="Only display changes; do not "
                            "sync any files.")

    args = parser.parse_args()

    p_file = os.path.join(playlists_dir, quote(args.playlist))
    print(p_file)
    if os.path.exists(p_file):
        quick_sync(p_file, args.destdir, args.flat, args.delete, args.test)
    else:
        raise NotImplementedError('Need to actually implement this')

if __name__ == '__main__':
    main()