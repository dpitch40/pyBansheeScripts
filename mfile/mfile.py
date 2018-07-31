from core.metadata import Metadata

class MusicFile(Metadata):

    """Base class for metadata derived from a music file."""

    def __init__(self, fname):
        self.fname = fname

    @property
    def location(self):
        return self.fname
