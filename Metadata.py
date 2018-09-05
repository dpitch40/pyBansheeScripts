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
from parse.web import url_re, parse_tracklist_from_url

from match import match_metadata_to_tracks

def copy_args_to_tracks(tracks, extra_args):
    for track in tracks:
        for k, v in sorted(extra_args.items()):
            setattr(track.default_metadata, k, v)

def sync_tracks(source_tracks, dest_tracks, copy_none, reloc, only_db_fields, extra_args, test):
    matched, unmatched_sources, unmatched_dests = match_metadata_to_tracks(source_tracks, dest_tracks)

    copy_args_to_tracks(source_tracks, extra_args)

    for source_track, dest_track in matched:
        sync_track(source_track, dest_track, copy_none, reloc, only_db_fields, extra_args, test)

    if unmatched_sources:
        print()
        for track in unmatched_sources:
            print('%s NOT MATCHED' % getattr(track, 'location', track))
            print()

    print('%d/%d matched' % (len(matched), len(source_tracks)))

    if not test:
        DefaultDb().commit()

def sync_track(source_track, dest_track, copy_none, reloc, only_db_fields, extra_args, test):
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
        if new_loc != dest_track.location:
            track_changes['db']['location'] = new_loc

    if track_changes:
        for name, changes in sorted(track_changes.items()):
            md = getattr(dest_track, name)
            print('    %s' % name)
            for k, v in sorted(changes.items()):
                print('        %s: %r -> %r' % (k, md.staged.get(k, None), v))

    if not test:
        dest_track.save()

    if reloc and new_loc != dest_track.location:
        print('    Relocating to %s' % new_loc)
        if dest_track.db:
            dest_track.db.location = new_loc
        if not test and dest_track.mfile:
            dest_track.mfile.move(new_loc)
        if not test:
            dest_track.save()

def copy_metadata(source_tracks, dest_strs, copy_none, reloc, only_db_fields, extra_args, test):
    extra_dests = list()
    for dest_str in dest_strs:
        dest_tracks, dest_type = parse_metadata_string(dest_str)
        if dest_type == 'web':
            raise ValueError('Cannot save tracks to a URL')
        elif dest_type == 'tracklist':
            extra_dests.append(dest_str)
        else:
            print('---\n%s\n---\n' % dest_str)
            sync_tracks(source_tracks, dest_tracks, copy_none, reloc, only_db_fields, extra_args, test)

    copy_args_to_tracks(source_tracks, extra_args)
    for dest_str in extra_dests:
        print('---\n%s\n---\n\nSaving tracks' % dest_str)
        if not test:
            write_tracklist(dest_str, source_tracks)

def parse_metadata_string(s):
    if url_re.match(s):
        metadatas = parse_tracklist_from_url(s)
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
                metadatas = read_tracklist(s)
                tracks = [Track(other=m) for m in metadatas]
                return tracks, 'tracklist'
            else:
                fnames = [s]
        else: # Directory
            fnames = get_fnames(s)
    else: # Could be a glob
        fnames = get_fnames(s)

    return [Track.from_file(fname, default_metadata=default_metadata) for fname in fnames], 'files'

def main():
    progDesc = """Copy music metadata from one source to one or more destinations."""

    parser = argparse.ArgumentParser(description=progDesc)
    parser.add_argument("--reloc", action="store_true",
                        help="Relocate files to standard filenames calculate from metadata.")
    parser.add_argument("--only-db-fields", action='store_true',
                        help="Only copy db-specific fields (play count, rating, etc.).")
    parser.add_argument('-c', '--copy-none', action='store_true')
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                        help="Specify extra data fields for tracks loaded from an external source.")
    parser.add_argument("source",
        help="The source to get metadata from (db, files, or a location of a track list).")
    parser.add_argument("dests", nargs='*', help="The files being edited, if any.")

    args = parser.parse_args()

    source_tracks, source_type = parse_metadata_string(args.source)

    extra_args = dict([(k, convert_str_value(v)) for k, v in args.extra])
    for t in source_tracks:
        print(t.format(**extra_args))

    if len(args.dests) > 0:
        print()
        copy_metadata(source_tracks, args.dests, args.copy_none, args.reloc,
                      args.only_db_fields, extra_args, args.test)

if __name__ == "__main__":
    main()