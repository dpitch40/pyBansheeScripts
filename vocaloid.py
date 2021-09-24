from datetime import datetime
import os
import os.path
import glob

from core.track import Track
from db.ql import QLDb
from config import DefaultDb
from core.util import filter_fname

ART_DIR = '/data/Pictures/Anime/Vocaloid'
TIME_CUTOFF_FILE = 'vocaloid_art_last_linked.txt'
DT_FMT = '%Y-%m-%dT%H:%M:%S'

def get_all_vocaloid_songs():
    vocaloid_songs = list()
    for qldb in QLDb.load_all():
        if qldb.grouping == 'Vocaloid':
            vocaloid_songs.append(Track.from_metadata(qldb))
    return vocaloid_songs

def create_art_link(track, path):
    dirname = os.path.basename(os.path.dirname(track.location))
    dest_name = filter_fname(f'{track.album_artist_or_artist} - {dirname}.jpg')
    dest_name = dest_name.replace('/', '_')
    dest = os.path.join(ART_DIR, dest_name)
    print(f'{path} -> {dest}')
    os.symlink(path, dest)

def get_cutoff_time():
    if not os.path.isfile(TIME_CUTOFF_FILE):
        return None
    with open(TIME_CUTOFF_FILE, 'r') as fobj:
        s = fobj.read().strip()
        return datetime.strptime(s, DT_FMT)

def save_cutoff_time():
    now = datetime.now()
    with open(TIME_CUTOFF_FILE, 'w') as fobj:
        fobj.write(now.strftime(DT_FMT))

def create_art_links():
    cutoff = get_cutoff_time()
    save_cutoff_time()

    checked_dirs = set()
    cover_arts = list()
    for track in get_all_vocaloid_songs():
        if cutoff is not None and track.date_added < cutoff:
            continue

        location = track.location
        d = os.path.dirname(location)
        if d not in checked_dirs:
            checked_dirs.add(d)
            arts = glob.glob(os.path.join(d, '*.jpg'))
            if arts:
                create_art_link(track, arts[0])

def main():
    create_art_links()

if __name__ == '__main__':
    main()
