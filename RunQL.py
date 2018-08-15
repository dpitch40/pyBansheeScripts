import os
import os.path
import shutil

import config
from core.util import run_with_backups

def main():
    run_with_backups(['quodlibet', '--run'], config.QLSongsLoc,
                     config.LibBackupDir, config.NumBackups)

if __name__ == '__main__':
    main()
