import os.path
import argparse
import collections
import config
from config import DefaultDb

from core.util import convert_str_value, get_fnames
from core.track import Track

from db.db import MusicDb

from mfile import mapping
from mfile.mfile import MusicFile

from parse.file import read_tracklist, tracklist_exts, write_tracklist
from parse.web import url_re, parse_tracklist_from_url, download_album_art, get_art_url

from match import match_metadata_to_tracks

def sync_tracks(source_tracks, dest_tracks, copy_none, reloc, only_db_fields, test):
    if dest_tracks or not reloc:
        matched, unmatched_sources, unmatched_dests = match_metadata_to_tracks(source_tracks, dest_tracks,
                                                                               True)
    else:
        matched = list(zip(source_tracks[:], source_tracks[:]))
        unmatched_sources, unmatched_dests = [], []

    mfiles_saved, dbs_saved = 0, 0
    for source_track, dest_track in matched:
        mfile_saved, db_saved = sync_track(source_track, dest_track, copy_none,
                                           reloc, only_db_fields, test)
        mfiles_saved += mfile_saved
        dbs_saved += db_saved

    if unmatched_sources:
        print()
        for track in unmatched_sources:
            print('%s NOT MATCHED' % getattr(track, 'location', track))
            print()

    print('%d/%d matched' % (len(matched), len(source_tracks)))

    if not test and dbs_saved:
        DefaultDb().commit()

def sync_track(source_track, dest_track, copy_none, reloc, only_db_fields, test):
    track_changes = collections.defaultdict(dict)
    dest_mds = list()
    for name in ('db', 'mfile'):
        md = getattr(dest_track, name)
        if md is not None:
            dest_mds.append((md, name))
    source_md = source_track

    if only_db_fields:
        allowed_fields = MusicDb.db_fields
    else:
        allowed_fields = None

    for md, name in dest_mds:
        md.update(source_md, copy_none=copy_none, allowed_fields=allowed_fields)
        changes = md.changes()
        if changes:
            track_changes[name].update(changes)

    print(dest_track.location)
    if reloc:
        new_loc = dest_track.default_metadata.calculate_fname()
        if new_loc != dest_track.location and 'db' in track_changes:
            track_changes['db']['location'] = new_loc

    if track_changes:
        for name, changes in sorted(track_changes.items()):
            md = getattr(dest_track, name)
            print('    %s' % name)
            for k, v in sorted(changes.items()):
                print('        %s: %r -> %r' % (k, md.staged.get(k, None), v))

    do_relocate = reloc and new_loc != dest_track.location
    if do_relocate:
        message = f'    Relocating to {new_loc}'
        if os.path.exists(new_loc):
            message = f'{message} (replacing existing file)'
        print(message)
        if dest_track.db:
            dest_track.db.location = new_loc

    mfile_saved, db_saved = 0, 0
    if not test:
        mfile_saved, db_saved = dest_track.save()
        if do_relocate and dest_track.mfile:
            dest_track.mfile.move(new_loc)

    return int(mfile_saved), int(db_saved)

def copy_metadata(source_tracks, dest_strs, copy_none, reloc, only_db_fields, test, append, apply_):
    extra_dests = list()
    if not dest_strs and reloc:
        sync_tracks(source_tracks, [], copy_none, reloc, only_db_fields, test)
    if not dest_strs and apply_:
        dest_tracks = [Track.from_file(t.location) for t in source_tracks]
        sync_tracks(source_tracks, dest_tracks, copy_none, reloc, only_db_fields, test)
    else:
        for dest_str in dest_strs:
            dest_tracks, dest_type = parse_metadata_string(dest_str)
            if dest_type == 'web':
                raise ValueError('Cannot save tracks to a URL')
            elif dest_type == 'tracklist':
                extra_dests.append(dest_str)
            else:
                print('---\n%s\n---\n' % dest_str)
                sync_tracks(source_tracks, dest_tracks, copy_none, reloc, only_db_fields, test)

    for dest_str in extra_dests:
        print('---\n%s\n---\n\nSaving tracks' % dest_str)
        if not test:
            write_tracklist(dest_str, source_tracks, append)

def parse_metadata_string(s, domain=None, extra_args=None):
    if extra_args is None:
        extra_args = dict()

    if url_re.match(s):
        metadatas = parse_tracklist_from_url(s, extra_args, domain)
        tracks = [Track(other=m) for m in metadatas]
        return tracks, 'web'

    default_metadata = None
    if s.startswith('db:') or s.startswith('mfile:'):
        default_metadata, s = s.split(':', 1)

    if os.path.exists(s):
        if os.path.isfile(s):
            ext = os.path.splitext(s.lower())[1]
            if ext == config.FileListExt:
                fnames = open(s).read().strip().split('\n')
            elif ext in tracklist_exts:
                metadatas = read_tracklist(s, extra_args)
                tracks = [Track(other=m) for m in metadatas]
                return tracks, 'tracklist'
            else:
                fnames = [s]
        else: # Directory
            fnames = get_fnames(s)
    elif s.lower().endswith(tracklist_exts):
        return None, 'tracklist'
    else: # Could be a glob
        fnames = get_fnames(s)

    tracks = [Track.from_file(fname, default_metadata=default_metadata) for fname in fnames]
    for t in tracks:
        for arg, v in extra_args.items():
            setattr(t, arg, v)
    return tracks, 'files'

def main():
    progDesc = """Copy music metadata from one source to one or more destinations."""

    parser = argparse.ArgumentParser(description=progDesc)
    parser.add_argument("--reloc", action="store_true",
                        help="Relocate files to standard filenames calculate from metadata.")
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes from a metadata source (with location) to matching tracks.")
    parser.add_argument("--only-db-fields", action='store_true',
                        help="Only copy db-specific fields (play count, rating, etc.).")
    parser.add_argument('-c', '--copy-none', action='store_true')
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                        help="Specify extra data fields for tracks loaded from an external source.")
    parser.add_argument('-d', '--domain', help="Manually set the domain for web parsing")
    parser.add_argument('-a', '--art', help="URL for album artwork")
    parser.add_argument('--append', action='store_true')
    parser.add_argument("source",
        help="The source to get metadata from (db, files, or a location of a track list).")
    parser.add_argument("dests", nargs='*', help="The files being edited, if any.")

    args = parser.parse_args()

    extra_args = dict([(k, convert_str_value(v)) for k, v in args.extra])
    source_tracks, source_type = parse_metadata_string(args.source, args.domain, extra_args)

    for t in source_tracks:
        print(t.format())

    if len(args.dests) > 0 or args.reloc or args.apply:
        if args.apply:
            dests = None
        else:
            dests = args.dests
        copy_metadata(source_tracks, dests, args.copy_none, args.reloc,
                      args.only_db_fields, args.test, args.append, args.apply)

    # If relocating, download album art
    if args.art:
        art_source = args.art
    elif source_type == 'web':
        art_source = args.source
    else:
        art_source = None

    if art_source and (args.reloc or args.art):
        art_url = get_art_url(art_source)
        if art_url:
            d = os.path.dirname(source_tracks[0].calculate_fname())
            print(f'Downloading album art from {art_url} to {d}')
            if not args.test:
                t = source_tracks[0]
                download_album_art(art_url, t.album_artist_or_artist, t.album)

if __name__ == "__main__":
    main()