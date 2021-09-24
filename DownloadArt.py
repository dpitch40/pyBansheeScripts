import argparse
import os.path

from core.util import convert_str_value

from parse.web import download_album_art, get_art_url
from Metadata import parse_metadata_string

def main():
    progDesc = """Download album artwork."""

    parser = argparse.ArgumentParser(description=progDesc)
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                        help="Specify extra data fields for tracks loaded from an external source.")
    parser.add_argument('-d', '--domain', help="Manually set the domain for web parsing")
    parser.add_argument("sources", nargs='+',
        help="The source(s) to get metadata from (db, files, or a location of a track list).")
    args = parser.parse_args()

    extra_args = dict([(k, convert_str_value(v)) for k, v in args.extra])

    for art_source in args.sources:
        source_tracks, source_type = parse_metadata_string(art_source, args.domain, extra_args)
        art_url = get_art_url(art_source)
        if art_url:
            d = os.path.dirname(source_tracks[0].calculate_fname())
            if os.path.isdir(d):
                print(f'Downloading album art from {art_url} to {d}')
                if not args.test:
                    t = source_tracks[0]
                    download_album_art(art_url, t.album_artist_or_artist, t.album)
            else:
                print(f'{art_url}: {d} does not exist')

if __name__ == "__main__":
    main()