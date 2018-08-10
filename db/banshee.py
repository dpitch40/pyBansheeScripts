from db.db import MusicDb
from db import db_glue
from core.util import date_descriptor, make_descriptor_func

db = db_glue.db

# Statement template used to pull everything useful from the sqlite database
select_stmt = """SELECT ct.TrackID AS TrackID, ct.Title AS title, ct.TitleSort AS title_sort,
ca.Name AS artist, ca.NameSort AS artist_sort, cl.Title AS album, cl.TitleSort AS album_sort,
cl.ArtistName AS album_artist, cl.ArtistNameSort AS album_artist_sort, ct.Genre AS genre, ct.Year AS year,
ct.TrackNumber AS tn, ct.TrackCount AS tc, ct.Disc AS dn, ct.DiscCount AS dc,
ct.Uri AS Uri, ct.Duration AS length, ct.BitRate AS bitrate, ct.Rating AS rating,
ct.PlayCount AS play_count, ct.SkipCount AS skip_count, ct.DateAddedStamp AS date_added,
ct.LastPlayedStamp AS last_played, ct.LastSkippedStamp AS last_skipped
FROM CoreTracks ct
JOIN CoreAlbums cl ON ct.AlbumID = cl.AlbumID, CoreArtists ca ON ct.ArtistID = ca.ArtistID%(where)s
ORDER BY album_artist, artist, album, dn, tn"""

field_mapping = {'title': 'Title',
                 'title_sort': 'TitleSort',
                 'genre': 'Genre',
                 'year': 'Year',
                 'tn': 'TrackNumber',
                 'tc': 'TrackCount',
                 'dn': 'Disc',
                 'dc': 'DiscCount',
                 'rating': 'Rating',
                 'play_count': 'PlayCount',
                 'skip_count': 'SkipCount',
                 'date_added': 'DateAddedStamp',
                 'last_played': 'LastPlayedStamp',
                 'last_skipped': 'LastSkippedStamp'}

update_stmt = """UPDATE CoreTracks SET %s WHERE TrackID = :TrackID"""

class BansheeDb(MusicDb):
    """Class for metadata derived from a Banshee sqlite3 database."""

    read_only_keys = ('bitrate',
                      'length',
                       # These fields are read-only for Banshee tracks (due to their being from linked tables)
                      'album',
                      'album_sort',
                      'album_artist',
                      'album_artist_sort',
                      'artist',
                      'artist_sort')

    def __init__(self, d):
        super(BansheeDb, self).__init__(d)
        self.sql_row = self.wrapped.copy()
        self.id_ = self.wrapped['TrackID']

    # Overridden from MusicDb

    def _save(self, changes):
        changes = list()
        for name, trans_name in field_mapping.items():
            if name in self.wrapped:
                if self.wrapped[name] != self.sql_row.get(name, None):
                    changes.append('%s = :%s' % (trans_name, name))
            elif name in self.sql_row:
                changes.append('%s = NULL' % trans_name)

        if changes:
            change_strs = list()
            for k, v in sorted(changes.items()):
                name = field_mapping.get(k, k)
                if v is None:
                    change_strs.append('%s = NULL' % name)
                else:
                    change_strs.append('%s = :%s' % (name, k))
            db.sql(update_stmt % ', '.join(change_strs), **self.to_dict())

    @classmethod
    def commit(cls):
        db.commit()

    @classmethod
    def load_all(cls):
        return [cls(row) for row in db.sql(select_stmt % {'where': ''})]

    @classmethod
    def _load_playlists(cls):
        playlists = list()

        #Get the listings of playlists
        playlists = db.sql("SELECT Name, PlaylistID FROM CorePlaylists")
        smart_playlists = db.sql("SELECT Name, SmartPlaylistID AS PlaylistID "
                      "FROM CoreSmartPlaylists")

        return playlists, smart_playlists

    @classmethod
    def load_playlists(cls):
        playlists, smart_playlists = cls._load_playlists()
        all_tracks = cls.load_all()
        track_ids_to_tracks = dict([(track.id_, track) for track in all_tracks])
        smart_playlist_entries = db.sql('SELECT EntryID, SmartPlaylistID AS '
                                'PlaylistID, TrackID FROM CoreSmartPlaylistEntries '
                                'ORDER BY EntryID')

        all_playlists = dict()
        for pl_row in playlists:
            name = pl_row['Name']
            pl_id = pl_row['PlaylistID']
            pl_list = list()
            playlist_entries = db.sql('SELECT EntryID, TrackID FROM '
                        'CorePlaylistEntries WHERE PlaylistID = ? '
                        'ORDER BY ViewOrder, EntryID', pl_id)
            for row in playlist_entries:
                pl_list.append(track_ids_to_tracks[row['TrackID']])
            all_playlists[name] = pl_list

        for pl_row in smart_playlists:
            name = pl_row['Name']
            pl_id = pl_row['PlaylistID']
            pl_list = list()
            playlist_entries = db.sql('SELECT EntryID, TrackID FROM '
                        'CoreSmartPlaylistEntries WHERE SmartPlaylistID = ? '
                        'ORDER BY EntryID', pl_id)
            for row in playlist_entries:
                pl_list.append(track_ids_to_tracks[row['TrackID']])
            all_playlists[name] = pl_list

        return all_playlists

    @classmethod
    def from_file(cls, loc):
        try:
            return cls._from_sql(select_stmt % {'where': " WHERE ct.Uri = ?"}, db_glue.pathname2sql(loc))
        except ValueError:
            return None

    @classmethod
    def from_metadata(cls, md):
        rows = list()
        if md.artist and md.album and md.title:
            where_str = " WHERE ct.Title = ? AND cl.Title = ? AND ca.Name = ?"

            rows = db.sql(select_stmt % {'where': where_str}, md.title, md.album, md.artist)
            if len(rows) == 1:
                return cls._from_rows(rows)

            if md.tn:
                where_str += ' AND ct.TrackNumber = ?'
                if md.dn:
                    where_str += ' AND ct.Disc = ?'
                    rows = db.sql(select_stmt % {'where': where_str}, md.title, md.album, md.artist, md.tn, md.dn)
                else:
                    rows = db.sql(select_stmt % {'where': where_str}, md.title, md.album, md.artist, md.tn)

                if len(rows) == 1:
                    return cls._from_rows(rows)

        return None

    # other constructors for getting a track from the db

    @classmethod
    def _from_rows(cls, rows):
        num_rows = len(rows)
        if num_rows == 1:
            return cls(rows[0])
        elif num_rows == 0:
            raise ValueError('No rows found')
        else:
            raise ValueError('Multiple rows found')

    @classmethod
    def _from_sql(cls, sql, *args, **kwargs):
        rows = db.sql(sql, *args, **kwargs)
        return cls._from_rows(rows)

    @classmethod
    def from_trackid(cls, id_):
        return cls._from_sql(select_stmt % {'where': " WHERE ct.TrackID = ?"}, id_)

    # Properties/descriptors

    bitrate = make_descriptor_func(lambda x: int(x * 1000))('bitrate')
    length = make_descriptor_func(lambda x: x)('length')
    location = make_descriptor_func(db_glue.sql2pathname, db_glue.pathname2sql)('Uri')
    date_added = date_descriptor('date_added')
    last_played = date_descriptor('last_played')
    last_skipped = date_descriptor('last_skipped')

    @property
    def tnc(self):
        return (getattr(self, 'tn', None), getattr(self, 'tc', None))

    @tnc.setter
    def tnc(self, value):
        tn, tc = value
        self.tn = tn
        self.tc = tc

    @tnc.deleter
    def tnc(self):
        self.tn, self.tc = None, None

    @property
    def dnc(self):
        return (getattr(self, 'dn', None), getattr(self, 'dc', None))

    @dnc.setter
    def dnc(self, value):
        dn, dc = value
        self.dn = dn
        self.dc = dc

    @dnc.deleter
    def dnc(self):
        self.dn, self.dc = None, None

def main():
    import sys
    import datetime
    track = BansheeDb.from_file(sys.argv[1])

    print(track.format())

    # del track.title_sort
    # del track.last_skipped
    # del track.dnc
    # track.year = 1998
    # track.rating = 0
    # track.save()
    # track.commit()

if __name__ == '__main__':
    main()
