import os
import os.path
import argparse

from mfile import mapping as mfile_mapping
import config

mfile_exts = set(mfile_mapping.keys())
art_exts = set(config.ArtExts)

def run(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        exts = set([os.path.splitext(fname)[1].lower() for fname in filenames])
        if (exts & mfile_exts) and not (exts & art_exts):
            print(dirpath)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('directory', help='The directory to work on.')

    args = parser.parse_args()

    run(args.directory)

if __name__ == '__main__':
    main()
