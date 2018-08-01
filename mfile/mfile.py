from core.metadata import Metadata

class MusicFile(Metadata):

    """Base class for metadata derived from a music file."""

    def __init__(self, fname, d):
        self.fname = fname
        super(MusicFile, self).__init__(d)

    @property
    def location(self):
        return self.fname
