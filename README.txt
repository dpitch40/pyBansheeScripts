This is a suite of Python scripts I've developed over the years to automate/make possible various tasks in Banshee, by interacting with file metadata and banshee's internal database. With these scripts I can do everything I could do in iTunes and more.

Before running any of the scripts, you will want to create your own Config.py file, by copying and editing ConfigTemplate.py. This file contains variables that will vary from user to user, and must be specified manually once.

A brief overview of the scripts available (run "python [Scriptname].py -h" for more detailed information):

- Metadata.py
    A powerful "Swiss army knife" script that combines the functionality of several older metadata-editing scripts.
- WalkSync.py
    Used to sync files to a portable music player in an iTunes-like fashion. Might need some modification to work on other machines.
- SyncPlaylist.py
    Used to sync a playlist to a flash drive in nested format for sharing. A simpler version of WalkSync.py; may be merged together with it.
- Rip_CD.py
    Used to rip CDs (or, more abstractly, any folder of lossless music files).
- ParseTables
    Designed to automatically parse metadata from a variety of sources, currently local files and the Metal Archives. Rather outdated, but works fine as long as the metal Archives doesn't change its page format.

Tracklist files:

There are two possible formats for tracklist files. The first, more verbose format uses .csv files. The file will contain one header row and one row for each track, and may have any of the following columns:

TrackID     Corresponds to CoreTracks.TrackID in the database.
Title       Corresponds to CoreTracks.Title in the database.
Artist      Corresponds to CoreArtists.Name in the database.
Album       Corresponds to CoreAlbums.Title in the database.
AlbumArtist Corresponds to CoreAlbums.ArtistName in the database.
Genre       Corresponds to CoreTracks.Genre in the database.
Year        Corresponds to CoreTracks.Year in the database.
TrackNumber Corresponds to CoreTracks.TrackNumber in the database.
TrackCount  Corresponds to CoreTracks.TrackCount in the database.
Disc        Corresponds to CoreTracks.Disc in the database.
DiscCount   Corresponds to CoreTracks.DiscCount in the database.
Uri         Corresponds to CoreTracks.Uri in the database.
Duration    Corresponds to CoreTracks.Duration in the database.
BitRate     Corresponds to CoreTracks.BitRate in the database.
FileSize    Corresponds to CoreTracks.FileSize in the database.
Location    The location of the file associated with this track.

The second, simpler format uses .txt files with the following format:

SimpleTrackList -> [HeaderRow] + '\n' + [TrackList]
HeaderRow -> [Artist] + '\t' + [Album] + '\t' + [Year] + [Genre]
Artist -> str
Album -> str
Year -> str (e.g. "2006")
Genre -> ''
Genre -> '\t' + str
TrackList -> [TrackRow] + [TrackListTail]
TrackRow -> [TrackTitle] + '\t' + [TrackLength] + [Disc]
TrackTitle -> str
TrackLength -> str (e.g. "3:14" or "186")
Disc -> ''
Disc -> '\t' + int
TrackListTail -> ''
TrackListTail -> '\n' + [TrackRow] + [TrackListTail]

Third-party dependencies:

mutagen: https://pypi.python.org/pypi/mutagen