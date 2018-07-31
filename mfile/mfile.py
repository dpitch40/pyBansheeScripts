import pprint

"""EasyID3 tags:
   ['albumartistsort', 'musicbrainz_albumstatus', 'lyricist', 'musicbrainz_workid', 'releasecountry',
    'date', 'performer', 'musicbrainz_albumartistid', 'composer', 'catalognumber', 'encodedby',
    'tracknumber', 'musicbrainz_albumid', 'album', 'asin', 'musicbrainz_artistid', 'mood', 'copyright',
    'author', 'media', 'length', 'acoustid_fingerprint', 'version', 'artistsort', 'titlesort',
    'discsubtitle', 'website', 'musicip_fingerprint', 'conductor', 'musicbrainz_releasegroupid',
    'compilation', 'barcode', 'performer:*', 'composersort', 'musicbrainz_discid',
    'musicbrainz_albumtype', 'genre', 'isrc', 'discnumber', 'musicbrainz_trmid', 'acoustid_id',
    'replaygain_*_gain', 'musicip_puid', 'originaldate', 'language', 'artist', 'title', 'bpm',
    'musicbrainz_trackid', 'arranger', 'albumsort', 'replaygain_*_peak', 'organization',
    'musicbrainz_releasetrackid']"""

class MusicFile(object):
    read_write_keys = ('album_artist',
                       'album_artist_sort',
                       'album',
                       'album_sort',
                       'artist',
                       'artist_sort',
                       'dc', # int
                       'dn', # int
                       'dnc', # (int, int)
                       'genre',
                       'tc', # int
                       'title',
                       'title_sort',
                       'tn', # int
                       'tnc', # (int, int)
                       'year' # int
                       )

    read_only_keys = ('bitrate', # Integer number of bits/second
                      'length' # Float number of seconds
                      )

    all_keys = sorted(read_only_keys + read_write_keys)

    def __init__(self, fname):
        super(MusicFile, self).__setattr__('fname', fname)

    def __repr__(self):
        d = dict([(k, getattr(self, k)) for k in self.all_keys])
        return pprint.pformat(d)
