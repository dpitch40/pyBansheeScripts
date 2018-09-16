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
        current_state = self.to_dict()
        for k, v in current_state.items():
            if v != self.staged.get(k, None):
                changes[k] = v
        for k in self.staged.keys():
            if k not in current_state:
                changes[k] = None

        return changes

    def _copy_changes(self):
        self.staged = self.to_dict()

    def save(self):
        """Copies all current changes over to the staged copy, then writes them to
           the backing file/database."""
        changes = self.changes()
        self._copy_changes()
        self._save(changes)
        return len(changes) > 0

    def _save(self, changes):
        """Saves all currently staged changes to the backing file.

           For objects backed by a media file, writes these changes back to the file.
           For objects backed by a database, writes changes to the database.
           The commit() method must then be called to save the database."""
        raise NotImplementedError

