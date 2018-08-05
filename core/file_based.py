import abc
from .metadata import Metadata

class FileBased(Metadata):
    """Abstract class for a Metadata object backed by a file (either an individual
       media file or a database file). Automatically keeps track of changes to
       metadata."""

    def __init__(self, d):
        super(FileBased, self).__init__(d)
        self._copy_changes()

    def changes(self):
        """Returns the changes that have been made to the object, as the difference
           between the current state and the staged copy."""
        changes = dict()
        for key in self.all_keys:
            if name in self.wrapped:
                if self.wrapped[name] != self.staged.get(name, None):
                    changes[key] = self.wrapped[name]
            elif name in self.staged:
                changes[key] = None
        return changes

    def _copy_changes(self):
        self.staged = dict(self.wrapped)

    def save(self):
        """Copies all current changes over to the staged copy, then writes them to
           the backing file/database."""
        self._save(self.changes())

    @abc.abstractmethod
    def _save(self):
        """Saves all currently staged changes to the backing file.

           For objects backed by a media file, writes these changes back to the file.
           For objects backed by a database, writes changes to the database.
           The commit() method must then be called to save the database."""
        raise NotImplementedError

