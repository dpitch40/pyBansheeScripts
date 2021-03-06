import os.path
import six

dest = os.path.join(os.path.dirname(__file__), "user.py")

if not os.path.exists(dest):
    with open(dest, 'w') as fObj:
        fObj.write(
"""# Override any of the values in defaults.py here

MusicDir =
BaseDevices = ["ROOT"]

PlaylistsToSync = {}

DiscogsAppName = ''
DiscogsUserToken = ''
""")
    six.print_("config/user.py not defined! Please open the generated file and override "
               "its settings with the correct values.")
    raise SystemExit

from .defaults import *
from .user import *