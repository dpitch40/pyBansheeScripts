import os.path

# Directory config variables - override these to be correct for your machine!

# Location of the contents of the CD drive in the file system
CDDriveLoc = "/run/user/1000/gvfs/cdda:host=sr0/"
# Top-level directory in which the user's music is stored
MusicDir = "/path/to/your/music/collection"
# Directory in which connected media devices show up
MediaDir = "/media/user_name"
# Name of the device in which playlists are stored
BaseDevice = "ROOT"
# Banshee DB location
BansheeDbLoc = os.path.expanduser(os.path.join('~', '.config', 'banshee-1', 'banshee.db'))
# Quod Libet songs file location
QLSongsLoc = os.path.expanduser(os.path.join('~', '.quodlibet', 'songs'))



# Playlists to sync - override to suit your tastes

# Mapping from playlist names to (Device name, protocols, sort order) tuples
PlaylistsToSync = {
  "Playlist_Name_In_Banshee": ("ROOT", ('', ".m3u8", "/path/to/music"),
                               ["AlbumArtist", "Album", "Disc", "TrackNumber"]),
}
# Device order in which to load playlists--tracks existing on multiple playlists across
# multiple devices will be synced to the device listed first in this list
DeviceOrder = ["ROOT", "DEV2"]



# Default settings - override these if you wish

# Add track/disc numbers to file names, e.g. "Age of Shadows.mp3" -> "1-01 Age of Shadows.mp3"
NumberTracks = True
# Group artist folders into parent folders by first letter of their name, e.g. "/Agalloch/" ->
# "/A/Agalloch/"
GroupArtists = True
# Ignore "The" at the beginning of artist names when grouping artists
# TODO: Change this to a list of ignored words
IgnoreThe = True
# Group together "singletons" (tracks synced piecemeal rather than as part of a full album)
# into a single subfolder to avoid cluttering the folder
GroupSingletons = True
# Default unicode encoding
UnicodeEncoding = "utf-8"
# Default bit rate to encode arbitrary tracks to
DefaultBitrate = 128
# Default bit rate to encode CDs to
DefaultCDBitrate = 256
# Default file type to encode to (.mp3 or .ogg)
DefaultEncodeExt = ".ogg"
# Default MP3 quality (0 <= qual <= 9, lower is better)
MP3Qual = 2
# Timestamp format for display
TsFmt = "%Y-%m-%d %H:%M:%S"
# album_artist defaults to artist if not specified
AlbumArtistDefault = True