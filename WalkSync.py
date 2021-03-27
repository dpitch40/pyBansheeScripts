import os.path
import os
import shutil
import threading
import argparse
import operator
import datetime
import logging
import enum
import glob
import collections
import itertools
from queue import Queue, Empty
import cProfile
import pstats
import time
import io

from mfile import open_music_file, mapping as mfile_mapping

import config
from core.util import compare_filesets, excape_xml_chars, pathname2xml, sort_key, \
        escape_fname

global showSkipped

class Action(enum.Enum):
    SYNC = 0
    UPDATE = 1
    DELETE = 2
    SKIP = 3

lame_input_formats = ('.mp3', '.wav')

stop_event = threading.Event()

PLAYLISTS_TO_SYNC = config.PlaylistsToSync
BASE_DIR = config.MediaDir
CONNECTED_DEVICES_ORDERED = [d for d in config.DeviceOrder if os.path.isdir(
                             os.path.join(BASE_DIR, d))]
CONNECTED_DEVICES = set(CONNECTED_DEVICES_ORDERED)
base_devices = list()
for device in config.BaseDevices:
    if device in CONNECTED_DEVICES:
        base_devices.append(device)
if not base_devices:
    print("No base device (can be %s) found. Make sure one is connected." %
          ', '.join(config.BaseDevices))
    raise SystemExit
elif len(base_devices) > 1:
    print("Multiple base devices (can be %s) found. Make sure only one is connected." %
          ', '.join(config.BaseDevices))
    raise SystemExit
else:
    BASE_DEVICE = base_devices[0]

loc_sizes = dict()
def getsize(f):
    # Caching wrapper around os.path.getsize
    if f in loc_sizes:
        return loc_sizes[f]
    else:
        size = loc_sizes[f] = os.path.getsize(f)
        return size

#------------------------------------------------------------------------------
# CHECKER THREAD
#------------------------------------------------------------------------------

# Threaded function that determines the actions to take with the tracks to sync
def get_changes(tracks, changes, synchronous, limit=None):
    #Populates changes (a Queue) with a series of 4-tuples:
    #track, dest, action, description string
    if synchronous:
        changes = list()
        put = changes.append
    else:
        put = changes.put

    tracks.sort(key=sort_key())
    dests = [t.calculate_fname(os.path.join(BASE_DIR, t.device, 'MUSIC'),
                                group_artists=config.GroupArtistsMedia)
                    for t in tracks]

    # Check for cover art
    cover_art_dests = set()
    art_locs = list()
    art_dests = list()
    for track, dest in zip(tracks, dests):
        if getattr(track, 'singleton', False):
            continue
        d = os.path.dirname(track.location)
        dest_dir = os.path.dirname(dest)

        arts = [os.path.join(d, f) for f in os.listdir(d) if
                os.path.splitext(f)[1].lower() in config.ArtExts]
        if arts:
            if len(arts) > 1:
                for art in arts:
                    if 'cover' in art.lower():
                        art_loc = art
                        break
                else:
                    art_loc = arts[0]
            else:
                art_loc = arts[0]
            art_base = os.path.basename(art_loc)
            art_dest = os.path.join(dest_dir, art_base)
            if art_dest in cover_art_dests:
                continue

            art_locs.append(art_loc)
            art_dests.append(art_dest)

            cover_art_dests.add(art_dest)

    dests.extend(art_dests)

    # Get list of files currently on player
    on_player = list()
    for device in CONNECTED_DEVICES_ORDERED:# dirsToPlaylistIDs.keys():
        artistDir = os.path.join(BASE_DIR, device, "MUSIC")
        for dirpath, dirnames, filenames in os.walk(artistDir):
            for f in filenames:
                on_player.append(os.path.join(dirpath, f))

    # Take the set difference of the two sets of filenames
    tosyncnew, common, filestoremove = compare_filesets(dests, on_player)
    logging.debug('%d to sync, %d common, %d to remove' %
        (len(tosyncnew), len(common), len(filestoremove)))
    to_sync_set = set(tosyncnew)

    # Handle deletions first
    for fname in filestoremove:
        if stop_event.is_set():
            return
        put((None, fname, Action.DELETE, None))

    synced = updated = 0
    for track_or_art, dest in zip(itertools.chain(tracks, art_locs), dests):
        if stop_event.is_set():
            return
        is_art = isinstance(track_or_art, str)
        if is_art:
            loc = track_or_art
        else:
            loc = track_or_art.location

        action, reason = Action.SKIP, None

        base, ext = os.path.splitext(dest)

        if dest not in to_sync_set:
            if config.SyncLevel == 0:
                # Skip updating files
                continue

            on_disk_time = os.path.getmtime(loc)
            on_player_time = os.path.getmtime(dest)
            if config.SyncLevel == 3:
                if on_disk_time != on_player_time:
                    action, reason = Action.UPDATE, "Modification times don't match"
            elif on_disk_time > on_player_time + 5:
                # Subtract 5 due to fluctuations
                if config.SyncLevel == 2:
                    on_disk_stamp = datetime.datetime.fromtimestamp(on_disk_time)
                    on_player_stamp = datetime.datetime.fromtimestamp(on_player_time)

                    days = (on_disk_stamp - on_player_stamp).days
                    # File on disk has been modified more recently
                    action, reason = Action.UPDATE, "File has been modified; %d days newer" % days
                else:
                    # Only sync if the file sizes differ (indicating a non-metadata change)
                    loc_size = getsize(loc)
                    dest_size = getsize(dest)
                    if loc_size != dest_size:
                        action, reason = Action.UPDATE, \
                            f'Sizes do not match: {loc_size/(2 ** 20):.2}MB != {dest_size/(2 ** 20):.2}MB'
            if action is Action.UPDATE:
                updated += 1
        else: # File does not exist on player
            action, reason = Action.SYNC, "Does not exist on player"
            synced += 1

        # print loc, dest, action, reason
        put((loc, dest, action, reason))

        if limit and (synced + updated) >= limit:
            break

    if synchronous:
        return changes
    else:
        # Add sentinel
        changes.put((None, None, None, None))

#------------------------------------------------------------------------------
# SYNCER THREAD
#------------------------------------------------------------------------------

def track_sync(changes, dryrun, size, shell_cmds, synchronous=False):
    #Sync the tracks
    synced = 0
    deleted = 0
    skipped = 0
    updated = 0

    dir_sizes = dict()
    created_dirs = set()

    size_deltas = collections.defaultdict(int)

    if synchronous:
        itr = changes
    else:
        class Itr(object):
            def __init__(self, q):
                self.q = q

            def __iter__(self):
                read = 0
                while True:
                    try:
                        timeout = 5 if read else None
                        loc, dest, action, reason = self.q.get(True, timeout)
                    except Empty:
                        break
                    if action is None:
                        logging.debug('Sentinel reached, stopping')
                        break
                    read += 1
                    yield loc, dest, action, reason

        itr = Itr(changes)

    for loc, dest, action, reason in itr:
        dest_dir = os.path.dirname(dest)
        # Find destination device
        dest_device = dest[len(BASE_DIR):].strip('/').split('/', 1)[0]

        if action == Action.DELETE:
            if shell_cmds:
                print('rm %s' % escape_fname(dest))
            else:
                logging.info("Deleting\t!%s!" % dest)

            if dest_dir in dir_sizes:
                dir_sizes[dest_dir] -= 1
            else:
                dir_sizes[dest_dir] = len(os.listdir(dest_dir)) - 1

            if size:
                size_deltas[dest_device] -= getsize(dest)
            if not dryrun:
                os.remove(dest)
            if dir_sizes[dest_dir] == 0:
                if shell_cmds:
                    print('rm -rf %s' % escape_fname(dest_dir))
                else:
                    logging.info("Removing\t%s" % dest_dir)
                if not dryrun:
                    try:
                        os.removedirs(dest_dir)
                    except OSError:
                        logging.error("***ERROR:\tCould not remove %s, it is not empty" % dest_dir)
            deleted += 1

        elif action == Action.SYNC or action == Action.UPDATE:
            if size:
                if action == Action.SYNC:
                    size_deltas[dest_device] += getsize(loc)
                else:
                    size_deltas[dest_device] += getsize(loc) - getsize(dest)

            if dest_dir not in created_dirs and not os.path.exists(dest_dir):
                if shell_cmds:
                    print('mkdir -p %s' % escape_fname(dest_dir))
                else:
                    logging.info("Creating\t%s" % dest_dir)
                created_dirs.add(dest_dir)
                if not dryrun:
                    os.makedirs(dest_dir)
            if shell_cmds:
                print('cp %s %s' % (escape_fname(loc), escape_fname(dest)))
            else:
                if action == Action.SYNC:
                    logging.info("Syncing \t%s\t(%s)" % (dest, reason))
                else:
                    logging.info("Updating \t%s\t(%s)" % (dest, reason))
            if not dryrun:     
                shutil.copy2(loc, dest)
                if config.SimplifyArtists:
                    ext = os.path.splitext(dest)[1].lower()
                    if ext in mfile_mapping:
                        metadata = open_music_file(dest)
                        artist = metadata.artist
                        album_artist = metadata.album_artist
                        if album_artist is not None and album_artist != artist:
                            metadata.artist = album_artist
                            metadata.save()

            if action == Action.SYNC:
                synced += 1
            else:
                updated += 1
        else:
            if showSkipped and not shell_cmds:
                logging.info("Skipping\t%s\t(%s)" % (dest, reason))
            skipped += 1

    out_str = '%d synced\t%d updated\t%d skipped\t %d deleted' % \
            (synced, updated, skipped, deleted)
    logging.info(out_str)
    if size:
        for dest_device, size_delta in sorted(size_deltas.items()):
            if size_delta == 0:
                size_str = '%s: No change' % (dest_device)
            else:
                sc = '+' if size_delta > 0 else '-'
                size_str = "%s: %s%d bytes (%s%.2f MB)" % \
                    (dest_device, sc, size_delta, sc, float(size_delta) / (2 ** 20))
            logging.info(size_str)
    stop_event.set()

#------------------------------------------------------------------------------
# BASE THREAD
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Initialization
#------------------------------------------------------------------------------

def add_extra_track_data(playlists):
    all_tracks = list()

    def sort_key(p):
        devices = sorted(PLAYLISTS_TO_SYNC[p].keys(), key=config.DeviceOrder.index)
        return (config.DeviceOrder.index(devices[0]), p)

    p_names_to_sync = sorted(playlists.keys(), key=sort_key)

    for p_name in p_names_to_sync:
        p_tracks = playlists[p_name]
        logging.debug('Found playlist %s, containing %d tracks', p_name, len(p_tracks))
        for track in p_tracks:
            if not hasattr(track, 'device'):
                devices = PLAYLISTS_TO_SYNC[p_name].keys()
                device = [d for d in devices if d in CONNECTED_DEVICES][0]
                track.device = device
                all_tracks.append(track)

    if config.GroupSingletons:
        # Singleton detection
        # An artist (along with all tracks associated with that artist) is
        # considered a 'singleton' on a particular device if it has fewer than 5 tracks
        # and no full albums on that device

        device_artists = collections.defaultdict(list)

        for device in config.DeviceOrder:
            for track in all_tracks:
                if track.device != device:
                    continue
                device_artists[track.album_artist_or_artist].append(track)

        for artist, tracks in sorted(device_artists.items()):
            album_disc_track_counts = dict()
            album_totals = collections.defaultdict(int)
            track_count = len(tracks)

            for track in tracks:
                key = (track.album, track.dn)
                if track.tc and track.album and key not in album_disc_track_counts:
                    album_disc_track_counts[key] = track.tc
                album_totals[key] += 1

            if track_count < 5 and all([tc > album_totals[key] for key, tc in
                                        album_disc_track_counts.items()]):
                for track in tracks:
                    track.singleton = True
                continue

    return all_tracks, p_names_to_sync

#------------------------------------------------------------------------------
# Playlist syncing
#------------------------------------------------------------------------------

def genM3UPlaylist(p_name, p_tracks, base_dir):
    lines = ["#EXTM3U"]
    call_base_dir = callable(base_dir)
    for track in p_tracks:
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        lines.append("#EXTINF:%d,%s - %s" % (track.length/1000, track.artist, track.title))
        lines.append(track.calculate_fname(bd, group_artists=config.GroupArtistsMedia))
    return "%s\n" % '\n'.join(lines)

def genM3U8Playlist(p_name, p_tracks, base_dir):
    lines = ["#EXTM3U"]
    call_base_dir = callable(base_dir)
    for track in p_tracks:
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        lines.append(track.calculate_fname(bd, group_artists=config.GroupArtistsMedia)
                    .replace('/', '\\'))
    return "%s\n" % '\n'.join(lines)

def genQLPlaylist(p_name, p_tracks, base_dir):
    lines = []
    call_base_dir = callable(base_dir)
    for track in p_tracks:
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        lines.append(track.calculate_fname(bd, group_artists=config.GroupArtistsMedia))
    return "%s\n" % '\n'.join(lines)

def genXSPFPlaylist(p_name, p_tracks, base_dir):
    app_data = list()
    track_str_list = list()
    call_base_dir = callable(base_dir)
    for idx, track in enumerate(p_tracks):
        if call_base_dir:
            bd = base_dir(track)
        else:
            bd = base_dir
        loc = track.calculate_fname(bd, group_artists=config.GroupArtistsMedia)
        xmlLoc = pathname2xml(loc)
        track_strs = ["\t\t<track>"]
        track_str_dict = [("location", xmlLoc),
                        ("title", excape_xml_chars(track.title)),
                        ("creator", excape_xml_chars(track.artist)),
                        ("album", excape_xml_chars(track.album)),
                        ("trackNum", "%d" % track.tn),
                       ]
        track_strs.extend(["\t<%s>%s</%s>" % (k, v, k) for k, v in track_str_dict])
        track_strs.append("</track>")

        track_str_list.append('\n\t\t'.join(track_strs))
        app_data.append('\t\t\t<vlc:item tid="%d"/>' % idx)

    fmt_dict = {"Name": p_name,
                "TrackList": '\n'.join(track_str_list),
                "AppData": '\n'.join(app_data)}
    fmt_str = """<?xml version="1.0" encoding="UTF-8"?>
<playlist xmlns="http://xspf.org/ns/0/" xmlns:vlc="http://www.videolan.org/vlc/playlist/ns/0/" version="1">
\t<title>%(Name)s</title>
\t<trackList>
%(TrackList)s
\t</trackList>
\t<extension application="http://www.videolan.org/vlc/playlist/0">
%(AppData)s
\t</extension>
</playlist>
"""
    return fmt_str % fmt_dict

def backupPlaylist(p_name, p_tracks, base_dir):
    return '%s\n' % '\n'.join([t.location for t in p_tracks])

playlist_gens_by_ext = {'': genQLPlaylist,
                        ".m3u": genM3UPlaylist,
                        ".m3u8": genM3U8Playlist,
                        ".xspf": genXSPFPlaylist,
                        '.bkp': backupPlaylist}

def sync_playlists(dryrun):
    # Mapping from destination playlist filenames to contents
    p_texts = dict()
    # Set of parent directories of the playlists
    p_dirs = list()

    playlists_to_sync = set([k for k, v in PLAYLISTS_TO_SYNC.items() if
        set(v.keys()) & CONNECTED_DEVICES])

    playlists = config.DefaultDb().load_playlists(playlists_to_sync)
    all_tracks, p_names_to_sync = add_extra_track_data(playlists)
    for p_name in p_names_to_sync:
        p_tracks = playlists[p_name]
        if not p_tracks:
            continue
        for device in PLAYLISTS_TO_SYNC[p_name]:
            if device in CONNECTED_DEVICES:
                protocols = PLAYLISTS_TO_SYNC[p_name][device]
                if isinstance(protocols, dict):
                    protocols = [protocols]

                for protocol in protocols:
                    sort_order = protocol['sort_order']
                    sort_reversed = protocol.get('sort_reversed', False)
                    p_ext = protocol['ext']

                    p_dir = os.path.join(BASE_DIR, BASE_DEVICE,
                                         "Playlists%s" % protocol['folder_suffix'])
                    if p_dir not in p_dirs:
                        p_dirs.append(p_dir)
                    dest_name = protocol.get('dest_name', None)
                    if not dest_name:
                        dest_name = p_name
                    p_dest = os.path.join(p_dir, "%s%s" % (dest_name, p_ext))

                    if sort_order:
                        p_tracks.sort(key=sort_key(*sort_order),
                                      reverse=sort_reversed)
                    p_text = playlist_gens_by_ext[p_ext](p_name, p_tracks,
                                                         protocol['base_dir'])

                    if p_text:
                        p_texts[p_dest] = p_text

    # Get list of playlists already on drive
    cur_playlists = list()
    for p_dir in p_dirs:
        if os.path.exists(p_dir):
            cur_pfiles = os.listdir(p_dir)
        else:
            cur_pfiles = []
            logging.info('Creating directory\t%s' % p_dir)

        if ".m3u" in cur_pfiles:
            cur_pfiles.remove(".m3u")
        cur_playlists.extend([os.path.join(p_dir, name) for name in cur_pfiles])

    to_sync, common, to_remove = compare_filesets(list(p_texts.keys()),
                                                cur_playlists, sort=True)

    # Playlists to add
    to_sync_texts = list()
    for p_dest in to_sync:
        text = p_texts[p_dest]
        to_sync_texts.append(text)
        logging.info("Creating playlist\t%s" % p_dest)

    # Playlists to update
    for p_dest in common:
        text = p_texts[p_dest]
        existing = open(p_dest, 'r').read()
        if text != existing:
            logging.info("Updating playlist\t%s" % p_dest)

            to_sync.append(p_dest)
            to_sync_texts.append(text)
        elif showSkipped:
            logging.info("Skipping playlist\t%s" % p_dest)

    # Playlists to remove
    for p_dest in to_remove:
        logging.info("Deleting playlist\t!%s!" % p_dest)

    # Execute changes
    if not dryrun:
        for p_dest in to_sync:
            p_dir = os.path.dirname(p_dest)
            if not os.path.exists(p_dir):
                os.makedirs(p_dir)

            p_text = p_texts[p_dest]
            with open(p_dest, 'w') as f:
                f.write(p_text)

        for p_dest in to_remove:
            os.remove(p_dest)

    return all_tracks

# Syncs the specified track IDs to the device.
def sync(allTracks, dryrun=False, size=False, synchronous=False, shell_cmds=False, limit=None):
    if synchronous:
        changes = get_changes(allTracks, None, synchronous, limit)
        logging.info('%d tracks found' % len(changes))
        track_sync(changes, dryrun, size, shell_cmds, synchronous)
    else:
        changes = Queue()
        checker = threading.Thread(target=get_changes, args=(allTracks, changes, synchronous, limit))
        checker.start()
        syncer = threading.Thread(target=track_sync, args=(changes, dryrun, size, shell_cmds, synchronous))
        syncer.start()

        syncer.join()

def main():
    global showSkipped

    parser = argparse.ArgumentParser(description="Sync specified playlists to a "
                    "portable music player. (Specify them in config/user.py)")
    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument("--size", action="store_true",
                help="Calculate the total data size (in bytes) added or removed")
    parser.add_argument("--show-skipped", action="store_true",
                help="Show files that were not synced or updated")
    parser.add_argument('--synchronous', action='store_true',
                help='Run the checker and syncer in the same thread')
    parser.add_argument('--shell-cmds', action='store_true',
                help='Print the shell commands to perform the track syncing')
    parser.add_argument('-l', '--limit', type=int)
    parser.add_argument('--profile', action='store_true')

    parser.add_argument("-q", "--quiet", action="store_true",
            help="Minimize output to the console.")
    parser.add_argument("-s", "--silent", action="store_true",
            help="Minimize output to the console even more.")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="Maximize output to the console.")

    args = parser.parse_args()

    if args.verbose:
        debug_level = logging.DEBUG
    elif args.quiet:
        debug_level = logging.WARNING
    elif args.silent:
        debug_level = logging.ERROR
    else:
        debug_level = logging.INFO
    logging.basicConfig(level=debug_level, format='%(levelname)s\t%(message)s')

    showSkipped = args.show_skipped

    now = time.time()
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()

    all_tracks = sync_playlists(args.test)

    sync(all_tracks, args.test, args.size, args.synchronous, args.shell_cmds, args.limit)

    if args.profile:
        pr.disable()
        for sortby in ('tottime', 'cumtime'):
            print(f'\n{sortby}:\n\n')
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats(50)
            print(s.getvalue())

    print(f'Done in {time.time() - now:.5} seconds')

if __name__ == '__main__':
    main()