from db.db import MusicDb
import db_glue

db = db_glue.db

# Statement template used to pull everything useful from the sqlite database
select_stmt = """SELECT ct.TrackID AS TrackID, ct.Title AS title, ct.TitleSort AS title_sort,
ca.Name AS artist, ca.NameSort AS artist_sort, cl.Title AS album, cl.TitleSort AS album_sort,
cl.ArtistName AS album_artist, cl.ArtistNameSort AS album_artist_sort, ct.Genre AS genre, ct.Year AS year,
ct.TrackNumber AS tn, ct.TrackCount AS tc, ct.Disc AS dn, ct.DiscCount AS dc,
ct.Uri AS Uri, ct.Duration AS length, ct.BitRate AS bitrate
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
                 'dc': 'DiscCount'}

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
        self.row = d
        self.sql_row = self.row.copy()
        self.id_ = self.row['TrackID']

    def save(self):
        changes = list()
        for name, trans_name in field_mapping.items():
            if name in self.row:
                if self.row[name] != self.sql_row.get(name, None):
                    changes.append('%s = :%s' % (trans_name, name))
            elif name in self.sql_row:
                changes.append('%s = NULL' % trans_name)

        db.sql(update_stmt % ', '.join(changes), **self.row)
        self.sql_row = self.row.copy()

    @classmethod
    def commit(cls):
        db.commit()

    @classmethod
    def load_all(cls):
        return [cls(row) for row in db.sql(select_stmt % {'where': ''})]

    # Constructors for getting a track from the db

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

    @classmethod
    def from_location(cls, loc):
        return cls._from_sql(select_stmt % {'where': " WHERE ct.Uri = ?"}, db_glue.pathname2sql(loc))

    # Properties/descriptors

    @property
    def bitrate(self):
        return self.row['bitrate'] * 1000

    @property
    def length(self):
        return self.row['length'] / 1000

    @property
    def location(self):
        return db_glue.sql2pathname(self.row['Uri'])

    @location.setter
    def location(self, value):
        self.row['Uri'] = db_glue.pathname2sql(value)

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
        return (getattr(self, 'dc', None), getattr(self, 'dc', None))

    @dnc.setter
    def dnc(self, value):
        dc, dc = value
        self.dc = dc
        self.dc = dc

    @dnc.deleter
    def dnc(self):
        self.dc, self.dc = None, None

def main():
    import sys
    # track = BansheeDb.from_trackid(int(sys.argv[1]))
    # track.tc = 13
    # print(repr(track))
    # track.save()

    tracks = BansheeDb.load_all()
    print(len(tracks))
    for track in tracks[:5]:
        print(repr(track))

if __name__ == '__main__':
    main()
