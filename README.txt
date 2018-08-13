This is a suite of Python scripts I've developed over the years to automate/make possible various tasks in my music player of choice, by interacting with file metadata and the player's internal database. With these scripts I can do everything I could do in iTunes and more.

Before running any of the scripts, you will want to create your own config/user.py file (a basic one is automatically created upon first importing config). This file contains variables that will vary from user to user, and must be specified manually once.

A brief overview of the scripts available (run "python <Scriptname>.py -h" for more detailed information):

- Metadata.py
    A powerful "Swiss army knife" script that combines the functionality of several older metadata-editing scripts. Can glean metadata for a batch of music files from a variety of sources and display it, save it to a file, or apply it to another selected batch of files.
- WalkSync.py
    Used to intelligently sync music files and playlists to a portable music player.
- SyncPlaylist.py
    Used to sync a playlist to a flash drive in nested format for sharing.
- Transcode.py
    Used to batch-reencode music files, e.g. FLAC to Ogg Vorbis.
- Sync.py
    Used to transfer music and playlists from a portable music player to a satellite computer.

Tracklist files:

There are two possible formats for tracklist files. The first, more verbose format uses .csv files. The file will contain one header row and one row for each track, and may have any of the following columns:

title               The track title.
title_sort          Alternate version of title used for sorting.
artist              The track's artist.
artist_sort         Alternate version of artist used for sorting.
album               The track's album.
album_sort          Alternate version of album used for sorting.
album_artist        The track's album artist.
album_artist_sort   Alternate version of album_artist used for sorting.
genre               The track genre.
year                The track release year.
tn                  The track number.
tc                  The total number of tracks on the album/disc.
tnc                 Concatenation of tn and tc.
dn                  The disc number.
dc                  The total number of discs in the album.
dnc                 Concatenation of dn and dc.
length              The track length, in milliseconds.
bitrate             The track bit rate, in bits per second.
rating              The track rating, as an integer out of 5.
play_count          The track's play count.
skip_count          The track's skip count.
last_played         When the track was last played.
last_skipped        When the track was last skipped.
date_added          When the track was added to the music player's database.
location            The track's file location.
fsize               The track's file size.

The second, simpler format uses .txt files with the following format:

SimpleTrackList -> <HeaderRow> + '\n' + <TrackList>
HeaderRow -> <Artist> + '\t' + <Album> + '\t' + <Year> + <Genre>
Artist -> str
Album -> str
Year -> str (e.g. "2006")
Genre -> ''
Genre -> '\t' + str
TrackList -> <TrackRow> + <TrackListTail>
TrackRow -> <TrackTitle> + '\t' + <TrackLength> + <Disc>
TrackTitle -> str
TrackLength -> str (e.g. "3:14" or "186")
Disc -> ''
Disc -> '\t' + int
TrackListTail -> ''
TrackListTail -> '\n' + <TrackRow> + <TrackListTail>

Third-party dependencies:

mutagen: https://pypi.python.org/pypi/mutagen
Beautiful Soup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/