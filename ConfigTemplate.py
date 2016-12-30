# Contains config variables used by other modules.

# Location of the contents of the CD drive in the file system
CDDriveLoc = "/run/user/1000/gvfs/cdda:host=sr0/"
# Top-level directory in which the user's music is stored
MusicDir = "/data/Music/iTunes/iTunes Music"
# Mapping from device names to lists of the playlists to sync onto them
PlaylistsToSync = {"0123-4567": ["VI_Victor Core"],
                   "6432-3634": ["VI_Victor",
                                 "VI_Victor Transient",
                                 "MIXES_Styx Greatest Hits"]
                   }
# Names of playlists to keep in their original order. Playlists not listed will be
# sorted by Artist/Album/TrackNumber.
OrigSortPlaylists = ["MIXES_Styx Greatest Hits"]
# Directory in which connected media devices show up
MediaDir = '/media/david'
# Name of the device in which playlists are stored
BaseDevice = "0123-4567"