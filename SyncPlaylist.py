import os.path
import shutil
import os
import argparse

from core.util import compare_filesets
import config
from urllib.parse import quote
from core.track import Track

from Transcode import convert

playlists_dir = os.path.join(os.path.dirname(config.QLSongsLoc), 'playlists')

def quick_sync(p_file, dest_dir, flat, delete, test, transcode=None):
    from mfile import open_music_file

    # Get list of files currently in the destination directory
    cur_files = list()
    for dirpath, dirnames, filenames in os.walk(dest_dir):
        cur_files.extend([os.path.join(dirpath, fname) for fname in filenames])

    locs = open(p_file, 'r').read().strip().split('\n')
    # Get a mapping from track destinations to their current locations
    dests_to_locs = dict()
    ext = None if transcode is None else ('.' + transcode)
    for loc in locs:
        mfile = open_music_file(loc)
        dest = mfile.calculate_fname(dest_dir, nested=not flat, ext=ext)
        dests_to_locs[dest] = loc

    _sync(dests_to_locs, cur_files, delete, test, transcode)

def _sync(dests_to_locs, cur_files, delete, test, transcode=None):
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

                loc = dests_to_locs[dest]
                if transcode is None or \
                   os.path.splitext(loc)[1].lower() == '.' + transcode.lower():
                    shutil.copy(loc, dest)
                else:
                    metadata = Track.from_file(loc, default_metadata='db')
                    convert(loc, dest, metadata, '.' + transcode, metadata.bitrate // 1000)
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
    parser.add_argument("--transcode", help="Transcode to this format",
                        choices=['mp3', 'ogg'], default=None)

    args = parser.parse_args()

    p_file = os.path.join(playlists_dir, quote(args.playlist))
    print(p_file)
    if os.path.exists(p_file):
        quick_sync(p_file, args.destdir, args.flat, args.delete, args.test, args.transcode)
    else:
        raise NotImplementedError('Need to actually implement this')

if __name__ == '__main__':
    main()