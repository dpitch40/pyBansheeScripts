# /usr/bin/python2.7

import pickle
import os.path
import argparse
import operator
import shutil

import db_glue
import Util

db = db_glue.new()
ql_dir = os.path.expanduser(os.path.join('~', '.quodlibet'))
ql_songs = os.path.join(ql_dir, 'songs')
ql_playlists_dir = os.path.join(ql_dir, 'playlists')

select_sql = """SELECT ct.TrackID, ct.Uri, ct.Title, ct.Rating, ct.DateAddedStamp, ct.PlayCount, ct.SkipCount,
ct.TrackNumber, ct.TrackCount, ct.Disc, ct.DiscCount, ct.year, ct.Genre, ca.Name AS Artist, cl.Title AS Album,
cl.ArtistName AS AlbumArtist
FROM CoreTracks ct
JOIN CoreAlbums cl on ct.AlbumID = cl.AlbumID
JOIN CoreArtists ca on ct.ArtistID = ca.ArtistID
ORDER BY Artist, Album, Disc, TrackNumber;"""

playlist_sql = "SELECT PlaylistID, Name FROM CorePlaylists WHERE PrimarySourceID NOT NULL"
playlist_entry_sql = """SELECT ct.Uri, cpe.EntryID
FROM CoreTracks ct JOIN CorePlaylistEntries cpe ON cpe.TrackID = ct.TrackID
WHERE cpe.PlaylistID = %d"""


def id_(old_field, new_field):
    def func(x, o=old_field, f=new_field):
        return {f: x[old_field]}
    return func

def number(old_field, new_field):
    def func(x, o=old_field, f=new_field):
        v = x[old_field]
        if v != 0:
            return {f: v}
        else:
            return None
    return func

def year_transform(track):
    return {'date': u'%d' % track['Year']}

def disc_transform(track):
    if track['Disc']:
        if track['DiscCount']:
            return {'discnumber': u'%d/%d' % (track['Disc'], track['DiscCount'])}
        else:
            return {'discnumber': u'%d' % (track['Disc'])}
    else:
        return None

def track_transform(track):
    if track['TrackNumber']:
        if track['TrackCount']:
            return {'tracknumber': u'%d/%d' % (track['TrackNumber'], track['TrackCount'])}
        else:
            return {'tracknumber': u'%d' % (track['TrackNumber'])}
    else:
        return None

def rating_transform(track):
    if track["Rating"] != 0:
        return {'~#rating': float(track["Rating"]) / 5.0}
    else:
        return None

field_mappings = [
    id_('Album', 'album'),
    id_('Artist', 'artist'),
    id_('Genre', 'genre'),
    id_('AlbumArtist', 'albumartist'),
    number('PlayCount', '~#playcount'),
    number('SkipCount', '~#skipcount'),
    number('DateAddedStamp', '~#added'),
    id_('Title', 'title'),
    year_transform,
    disc_transform,
    track_transform,
    rating_transform
]

def match_tracks_to_songs(tracks, songs, force):
    track_locations = [db_glue.sql2pathname(str(track["Uri"])).decode('utf8') for track in tracks]
    song_locations = [song['~filename'].decode("utf8") for song in songs]
    
    extra_tracks, common, extra_songs = Util.boolean_diff(track_locations, song_locations, sort=True)
    
    if extra_tracks:
        print "Unmatched track locations from Banshee:\n%s" % '\n'.join(extra_tracks)
    if extra_songs:
        print "Unmatched song locations from Quod Libet:\n%s" % '\n'.join(extra_songs)
    if not force and (extra_tracks or extra_songs):
        raise SystemExit

    mapping = dict()
    track_locations_to_tracks = dict(zip(track_locations, tracks))
    song_locations_to_songs = dict(zip(song_locations, songs))
    for location in common:
        mapping[location] = (track_locations_to_tracks[location], song_locations_to_songs[location])

    return mapping

def transform_track(track):
    ql_track = dict()

    for mapping in field_mappings:
        result = mapping(track)
        if result is not None:
            ql_track.update(result)
    return ql_track

def sync_track_to_song(track, song):
    changes = dict()
    ql_track = transform_track(track)

    for k, v in sorted(ql_track.items()):
        if k not in song or song[k] != v:
            changes[k] = v

    return changes

def save_song_changes(songs):
    backup_loc = ql_songs + '_backup'
    print('Saving song changes! Backing existing songs file up to %s' % backup_loc)
    shutil.copy2(ql_songs, backup_loc)

    with open(ql_songs, 'wb') as fobj:
        pickle.dump(songs, fobj)

def sync_playlist(playlist):
    name = playlist['Name']
    playlist_id = playlist['PlaylistID']

    dest = os.path.join(ql_playlists_dir, name).replace(' ', '_')

    entries = db.sql(playlist_entry_sql % playlist_id)
    contents = []
    for entry in entries:
        contents.append(db_glue.sql2pathname(str(entry['Uri'])).decode('utf8') + '\n')

    return dest, ''.join(contents)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--dryrun', action='store_true')
    parser.add_argument('-f', '--force', action='store_true')

    args = parser.parse_args()

    tracks = db.sql(select_sql)

    with open(ql_songs, 'rb') as fobj:
        songs = pickle.load(fobj)
        songs.sort(key=lambda s: (s.get('artist', ''), s.get('album', ''),
                int(s.get('disc', '1/1').split('/')[0]),
                int(s.get('tracknumber', '1/1').split('/')[0])))

    mapping = match_tracks_to_songs(tracks, songs, args.force)

    changed = False
    for location, (track, song) in sorted(mapping.items()):
        changes = sync_track_to_song(track, song)
        if changes:
            changed = True
            print('%s\n\t%s' % (location, '\n\t'.join(['%r:\t%r -> %r' % (k, song.get(k, None), v) 
                                    for k, v in sorted(changes.items())])))
            song.update(changes)

    if changed and not args.dryrun:
        save_song_changes(songs)

    playlists = db.sql(playlist_sql)
    for playlist in playlists:
        playlist_dest, playlist_contents = sync_playlist(playlist)
        if os.path.isfile(playlist_dest):
            existing_contents = open(playlist_dest, 'r').read()
            sync = existing_contents != playlist_contents
        else:
            sync = True
        if sync:
            print('Syncing playlist %s to %s' % (playlist['Name'], playlist_dest))
            if not args.dryrun:
                open(playlist_dest, 'w').write(playlist_contents)

if __name__ == '__main__':
    main()
