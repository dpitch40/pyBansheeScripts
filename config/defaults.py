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

# Mapping from playlist names to (Device name, sort order, protocols) tuples
PlaylistsToSync = {
  "Playlist_Name_In_Banshee": ("ROOT", ['album_artist', 'album', 'dn', 'tn'],
                                ('', ".m3u8", "/path/to/music", False)),
}
# Device order in which to load playlists--tracks existing on multiple playlists across
# multiple devices will be synced to the device listed first in this list
DeviceOrder = ["ROOT", "DEV2"]



# Default settings - override these if you wish

# Add track/disc numbers to file names, e.g. "Age of Shadows.mp3" -> "1-01 Age of Shadows.mp3"
NumberTracks = True
# Group artist folders into parent folders by first letter of their name, e.g. "/Agalloch/" ->
# "/A/Agalloch/"
GroupArtists = False
# Group artists when syncing to a portable media player
GroupArtistsMedia = True
# List of words to ignore at the beginning of artist names when grouping artists
IgnoreWords = ['The']
# Group together "singletons" (tracks synced piecemeal rather than as part of a full album)
# into a single subfolder to avoid cluttering the folder
GroupSingletons = True
# Re-sync music files to the player if the size does not match the file on the disc
CheckSizes = True
# Timestamp format for display
TsFmt = "%Y-%m-%d %H:%M:%S"
# album_artist defaults to artist if not specified
AlbumArtistDefault = True
# Default MusicDb class to use--callable
DefaultDb = lambda x: None
# Default bit rate to encode arbitrary tracks to
DefaultBitrate = 128
# Default bit rate to encode CDs to
DefaultCDBitrate = 256
# Default file type to encode to (.mp3 or .ogg)
DefaultEncodeExt = ".ogg"
# Default source to use when opening track metadata from filenames. Select 'db' or 'mfile'.
DefaultMetadataSource = 'mfile'
# Default MP3 quality (0 <= qual <= 9, lower is better)
MP3Qual = 2
# Default FLAC encoding compression level (0 <= level <= 8; lower is faster, higher is more compressed)
FlacCompLevel = 5
# Raw file options for encoding/decoding
RawSigned = 'signed'
RawBitsPerSample = 16
RawEndianness = 'big'
RawChannels = 2
RawSampleRate = 44100