import os.path

import config
from core.util import run_with_backups

def main():
    backup_mapping = {config.QLSongsLoc: config.LibBackupDir,
                      os.path.join(config.QLPlaylistsLoc, '*'):
                        os.path.join(config.LibBackupDir, 'Playlists')}

    run_with_backups(['quodlibet', '--run'], backup_mapping, config.NumBackups)

if __name__ == '__main__':
    main()
