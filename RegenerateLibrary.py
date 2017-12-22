import argparse
import os.path
import os
import db_glue
import shutil
import re
import operator
from pprint import pprint

DEFAULT_LIBRARY = os.path.expanduser("~/.config/banshee-1/banshee.db")

TABLE_NAME_RE = re.compile(r"(?<=CREATE TABLE )\w+")

# Table loaders

loader_registry = {}
key_registry = {}

_ = lambda *args: args

class MetaLoader(type):
    def __new__(cls, name, bases, namespace, **kwds):
        new_cls = super(MetaLoader, cls).__new__(cls, name, bases, namespace)
        if bases:
            if new_cls.table_name:
                loader_registry[new_cls.table_name] = new_cls
                if new_cls.key:
                    if new_cls.key in key_registry:
                        raise Exception("The key %r was specified twice" % new_cls.key)
                    key_registry[new_cls.key] = new_cls
        return new_cls

class TableLoader(metaclass=MetaLoader):
    table_name = None
    key = None
    sort_key = None
    order = 0
    dereference = True

    def __init__(self, db, contents, table_name=None):
        self.db = db
        self.contents = contents

        if table_name and self.table_name is None:
            self.table_name = table_name

    @classmethod
    def _dereference(cls, _id, contents):
        table = contents[cls.table_name]
        if _id is not None:
            return table[_id]
        else:
            return None

    def _link_rows(self, rows):
        if rows:
            columns = sorted(rows[0].keys())
            column_transforms = {}
            for col_name in columns:
                if self.dereference and col_name in key_registry and col_name != self.key:
                    cls = key_registry[col_name]
                    column_transforms[col_name] = cls._dereference

            contents = {}
            for row in rows:
                for col_name, col_val in row.items():
                    if col_name in column_transforms:
                        row[col_name] = column_transforms[col_name](col_val, self.contents)
                if self.key:
                    key = self.key
                else:
                    key = self.sort_key
                key_val = row[key]
                if isinstance(key_val, dict):
                    key_val = key_val[key]
                contents[key_val] = row

            return contents
        else:
            return {}

    def load_table(self):
        rows = self.db.sql("SELECT * FROM %s" % self.table_name)
        return self._link_rows(rows)

class PrimarySourceTableLoader(TableLoader):
    table_name = "coreprimarysources"
    order = -6
    key = "PrimarySourceID"

class ArtistTableLoader(TableLoader):
    table_name = "coreartists"
    order = -6
    key = "ArtistID"


class AlbumTableLoader(TableLoader):
    table_name = "corealbums"
    order = -5
    key = "AlbumID"


class TrackTableLoader(TableLoader):
    table_name = "coretracks"
    order = -4
    key = "TrackID"


class PlaylistTableLoader(TableLoader):
    table_name = "coreplaylists"
    order = -3
    key = "PlaylistID"

class SmartPlaylistTableLoader(TableLoader):
    table_name = "coresmartplaylists"
    order = -3
    key = "SmartPlaylistID"

class PodcastSyndicationsLoader(TableLoader):
    table_name = "podcastsyndications"
    order = -2
    key = "FeedID"


class RemovedTracksTableLoader(TableLoader):
    table_name = "coreremovedtracks"
    order = -1
    sort_key = "TrackID"
    dereference = False

class PodcastItemsLoader(TableLoader):
    table_name = "podcastitems"
    order = -1
    key = "ItemID"

class ShufflerTableLoader(TableLoader):
    table_name = "coreshufflers"
    order = -1
    key = "ShufflerId"


class BookmarkTableLoader(TableLoader):
    table_name = "bookmarks"
    key = "BookmarkId"

class CacheModelTableLoader(TableLoader):
    table_name = "corecachemodels"
    key = "CacheID"

class LastFMLoader(TableLoader):
    table_name = "lastfmstations"
    key = "StationID"

class MetadataProblemsTableLoader(TableLoader):
    table_name = "metadataproblems"
    key = "ProblemID"

class PodcastEnclosuresLoader(TableLoader):
    table_name = "podcastenclosures"
    key = "EnclosureID"

class HyenaTableLoader(TableLoader):
    table_name = "hyenamodelversions"
    key = "id"

class PlaylistEntryTableLoader(TableLoader):
    table_name = "coreplaylistentries"
    sort_key = "EntryID"

class SmartPlaylistEntryTableLoader(TableLoader):
    table_name = "coresmartplaylistentries"
    sort_key = "EntryID"

class ShufflesTableLoader(TableLoader):
    table_name = "coreshuffles"
    sort_key = "TrackID"

class ShuffleModsTableLoader(TableLoader):
    table_name = "coreshufflemodifications"
    sort_key = "TrackID"

class ConfigTableLoader(TableLoader):
    table_name = "coreconfiguration"
    sort_key = "EntryID"

class ArtDownloadTableLoader(TableLoader):
    table_name = "coverartdownloads"
    sort_key = "AlbumID"

class IAItemTableLoader(TableLoader):
    table_name = "iaitems"
    sorty_key = "ItemID"

# Table generators

# Main driver class

class LibraryRegenerator(object):

    def __init__(self, target, dest, backup, dryrun):

        self.schema = open("BansheeSchema.sql", 'rU').read()

        self.target = target
        self.dest = dest
        self.backup = backup
        self.dryrun = dryrun

        self.db = None

    def backup_library(self):
        """Copies the old library to the backup location."""

        print("Backing up %s to %s...\n" % (self.target, self.backup))
        if not self.dryrun:
            _dir = os.path.dirname(self.backup)
            if not os.path.isdir(_dir):
                os.makedirs(_dir)
            shutil.copy2(self.target, self.backup)

    def load_library(self):
        """Loads the contents of the old library into a Python data structure."""

        lib_contents = {}
        table_names = map(operator.methodcaller("lower"), TABLE_NAME_RE.findall(self.schema))
        db = db_glue.new(self.target)
        
        loaders = []
        for table_name in table_names:
            loader = loader_registry[table_name](db, lib_contents)
            loaders.append(loader)

        loaders.sort(key=operator.attrgetter("order", "table_name"))

        for loader in loaders:
            print("Loading %s..." % loader.table_name)
            rows = loader.load_table()
            lib_contents[loader.table_name] = rows
            # print(rows.keys())

        db.close()

        pprint(next(iter(lib_contents["coreplaylistentries"].items())))

        return lib_contents

    def generate_new_library(self):
        """Creates a new, empty library with the proper schema at dest."""
        print("Generating a new empty library at %s...\n" % dest)

        if not self.dryrun:
            if os.path.exists(dest):
                print("Deleting %s...\n" % dest)
                os.remove(dest)
            self.db = db_glue.new(dest)
            for stmt in self.schema.split(';'):
                print(stmt.strip() + ';')
                self.db.sql(stmt)
            self.db.commit()
        else:
            if os.path.exists(dest):
                print("Deleting %s...\n" % dest)
            for stmt in sql.split(';'):
                print(stmt.strip() + ';')


    def recreate_db(self, contents):
        """Recreates the old library, in regenerated form, at dest, from the contents data structure."""
        pass

    def regenerate_library(self):

        if self.target == self.dest:
            self.backup_library()

        old_lib_contents = self.load_library()

        # self.generate_new_library()

        # self.recreate_db(old_lib_contents)

        # self.db.close()

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', "--target", help="The banshee.db library file to regenerate. Defaults to %s"
                            % DEFAULT_LIBRARY, default=DEFAULT_LIBRARY)
    parser.add_argument('-d', "--dest", help="The location of the regenerated library. Defaults to the "
                                    "location of the old library.")
    parser.add_argument('-b', "--backup", help="Manually specify the location to back up the old library.")
    parser.add_argument('-n', "--dryrun", action="store_true", help="Display all the actions/SQL to be executed, "
                                                "do not make any actual changes.")

    args = parser.parse_args()

    if not os.path.exists(args.target):
        print("The library %r does not exist." % args.target)
        return

    if args.backup is None:
        _dir, base = os.path.split(args.target)
        base, ext = os.path.splitext(base)
        args.backup = os.path.join(_dir, "%s_backup%s" % (base, ext))

    if args.dest is None:
        args.dest = args.target

    r = LibraryRegenerator(args.target, args.dest, args.backup, args.dryrun)
    r.regenerate_library()

if __name__ == "__main__":
    main()
