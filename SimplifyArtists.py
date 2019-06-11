import argparse
import os
import os.path

from mfile import mapping as mfile_mapping, open_music_file
import config

def run(directory, test):
    if not os.path.isdir(directory):
        print('%s does not exist.' % directory)
        raise SystemExit

    for dirpath, dirnames, filenames in os.walk(directory):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in mfile_mapping:
                path = os.path.join(dirpath, fname)
                try:
                    metadata = open_music_file(path)
                except Exception as ex:
                    print(path)
                    raise

                artist = metadata.artist
                album_artist = metadata.album_artist
                if album_artist is not None and album_artist != artist:
                    print('%s\t%s\t%s' % (path, artist, album_artist))
                    if not test:
                        metadata.artist = album_artist
                        metadata.save()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('directory', help='The directory to work on.')

    args = parser.parse_args()

    run(args.directory, args.test)

if __name__ == '__main__':
    main()
