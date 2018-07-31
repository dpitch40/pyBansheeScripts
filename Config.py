import os.path
import six

dest = os.path.join(os.path.dirname(__file__), "ConfigUser.py")

if not os.path.exists(dest):
    with open(dest, 'w') as fObj:
        fObj.write(
"""# Override any of the values in ConfigDefaults here

CDDriveLoc =
MusicDir =
MediaDir =
BaseDevice = "ROOT"
# Mappings from device names to slot numbers
SlotNums = {"ROOT": 1}

PlaylistsToSync = {}
""")
    six.print_("ConfigUser.py not defined! Please open the generated file and override "
               "its settings with the correct values.")
    raise SystemExit

from ConfigDefaults import *
from ConfigUser import *