import os.path
import getpass

# Directory config variables - override these to be correct for your machine!

# Location of the contents of the CD drive in the file system
CDDriveLoc = "/run/user/1000/gvfs/cdda:host=sr0/"
# Top-level directory in which the user's music is stored
MusicDir = "/path/to/your/music/collection"
# Directory in which connected media devices show up
MediaDir = os.path.join('/media', getpass.getuser())
# Names of devices in which playlists are stored
BaseDevices = ["ROOT"]
# Banshee DB location
BansheeDbLoc = os.path.expanduser(os.path.join('~', '.config', 'banshee-1', 'banshee.db'))
# Quod Libet songs file location
QLSongsLoc = os.path.expanduser(os.path.join('~', '.quodlibet', 'songs'))
# Quod Libet playlist file location
QLPlaylistsLoc = os.path.expanduser(os.path.join('~', '.quodlibet', 'playlists'))
# Directory to check for playlists on a portable player
PortablePLsDir = 'PlaylistsQL'

# Library backup settings for RunQL.py
# Number of pre/post backups to maintain
NumBackups = 3
# Directory for backup copies of library
LibBackupDir = '/data/Music/Backups'


# Playlists to sync - override to suit your tastes

# Mapping from playlist names to {device_name: protocols} dicts
PlaylistsToSync = {
  "Playlist_Name_In_Banshee": {"ROOT": {
                                "sort_order": ['album_artist', 'album', 'dn', 'tn'],
                                "folder_suffix": "",
                                "ext": ".mu38",
                                "base_dir": "/path/to/music"}
                              },
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
# On synced tracks, change the artist to match the album artist
SimplifyArtists = False
# List of words to ignore at the beginning of artist names when grouping artists
# Lowercased
IgnoreWords = ['the']
# Group together "singletons" (tracks synced piecemeal rather than as part of a full album)
# into a single subfolder to avoid cluttering the folder
GroupSingletons = True
# How thorough to be when syncing music to a player
# 0 = Do not update existing files, only sync new files and delete
# 1 = Only update files whose size has changed
# 2 = Update any files that are newer in the source than in the destination
# 3 = Update any files whose modification times don't match
SyncLevel = 2
# Timestamp format for display
TsFmt = "%Y-%m-%d %H:%M:%S"
# album_artist defaults to artist if not specified
AlbumArtistDefault = True
# Default MusicDb class to use--callable
def DefaultDb():
    from db.ql import QLDb
    return QLDb
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
# File list extension
FileListExt = '.fl'
# Extensions for album artwork--lowercase
ArtExts = ['.jpg', '.bmp', '.png']
# Raw file options for encoding/decoding
RawSigned = 'signed'
RawBitsPerSample = 16
RawEndianness = 'big'
RawChannels = 2
RawSampleRate = 44100
# Maximum number of stars a track can be rated
MaxStars = 5
# If downloading album art, scale it down it to this size (maximum height or width in pixels)
MaxArtSize = 800
# Only download album art if it's at least this size (in pixels)'
MinArtSize = 400
