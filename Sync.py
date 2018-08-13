"""Meant to be run on/from a portable music player to sync files to a computer."""

import os
import shutil
import os.path
import argparse
import glob
import re
import subprocess

import config

# Set up default directories
artists_dir = config.MusicDir
playlists_dir = config.QLPlaylistsLoc

single_char_dir_re = re.compile(r"^([A-Z])(?=%s)" % re.escape(os.sep))

def sync(origin_dir, dest_dir, test):
    print("\nSYNCING FROM %s TO %s\n" % (origin_dir, dest_dir))
    files_synced, dirs_synced = 0, 0
    d_len = len(origin_dir)

    for dirpath, dirnames, fnames in os.walk(origin_dir):
        # File/directory names with special chaarcters show up as nonexistent files; weed them out
        fnames = list(filter(lambda f: os.path.isfile(os.path.join(dirpath, f)), fnames))

        if len(fnames) == 0:
            continue
        # If enabled and the relative path begins with a single-character directory, remove it
        try:
            partial_dir = dirpath[d_len:].lstrip(os.sep)
            if single_char_dir_re.match(partial_dir):
                partial_dir = partial_dir[2:]
        except IndexError:
            continue

        # Check if the destination directory exists
        dest_sub_dir = os.path.join(dest_dir, partial_dir)
        if not os.path.isdir(dest_sub_dir):
            # If not, sync the whole directory
            print("SYNCING DIRECTORY\t%s" % dest_sub_dir)
            dirs_synced += 1
            if not test:
                shutil.copytree(dirpath, dest_sub_dir)
        else:
            # Otherwise, check if any destination files don't exist
            dest_listing = os.listdir(dest_sub_dir)
            for fname in fnames:
                source = os.path.join(dirpath, fname)
                dest = os.path.join(dest_dir, partial_dir, fname)
                do_sync = False
                if fname not in dest_listing:
                    do_sync = True

                if do_sync:
                    print("SYNCING FILE\t\t%s" % dest)
                    files_synced += 1
                    if not test:
                        shutil.copyfile(source, dest)

    print("%d files, %d dirs synced" % (files_synced, dirs_synced))

def sync_playlists(source_dir, dest_dir, test):
    if not source_dir.endswith('/'):
        source_dir += '/'
    print("\nSYNCING PLAYLISTS FROM %s to %s\n" % (source_dir, dest_dir))

    args = ["rsync", "--dirs", '-u', "--times", '--info=name,del,copy,remove']
    if test:
        args.append("--dry-run")

    subprocess.call(args + [source_dir, dest_dir])

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--test", action="store_true", help="Only display changes, don't sync any files")

    args = parser.parse_args()

    media_dir = config.MediaDir
    devices = [os.path.join(media_dir, d) for d in os.listdir(media_dir)]

    if not os.path.isdir(artists_dir):
        os.makedirs(artists_dir)
    if not os.path.isdir(playlists_dir):
        os.makedirs(playlists_dir)

    for dev_dir in devices:
        sync(os.path.join(dev_dir, "MUSIC"), artists_dir, args.test)
        p_dir = os.path.join(dev_dir, config.PortablePLsDir)
        if os.path.isdir(p_dir):
            sync_playlists(p_dir, playlists_dir, args.test)

if __name__ == "__main__":
    main()