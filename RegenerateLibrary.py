import functools
import argparse
import os.path
import os
import db_glue
import shutil
import re
import operator
import collections
from pprint import pprint

DEFAULT_LIBRARY = os.path.expanduser(os.path.join('~', '.config', 'banshee-1', 'banshee.db'))

TABLE_NAME_RE = re.compile(r"(?<=CREATE TABLE )\w+")

_ = lambda *args: args

playlistid_re = re.compile(r'<field name="(?:smart)?playlistid" ?/><int>(\d+)</int>')

def playlist_id_replace(m):
    matched = m.group(0)
    _id = m.group(1)
    if "smart" in matched:
        lookup = SmartPlaylistTableGenerator.reindexed
    else:
        lookup = PlaylistTableGenerator.reindexed
    return matched.replace(_id, str(lookup[int(_id)]))

# Table loaders

loader_registry = {}
key_registry = {}

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

    def __init__(self, db, contents):
        self.db = db
        self.contents = contents

    @classmethod
    def _dereference(cls, name, _id, contents):
        table = contents[cls.table_name]
        if _id is not None:
            try:
                return table[_id]
            except KeyError as e:
                print("Could not find %s %d in %s" % (name, _id, cls.table_name))
                raise
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
                        row[col_name] = column_transforms[col_name](col_name, col_val,
                                        self.contents)
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
    order = -2
    key = "SmartPlaylistID"


class RemovedTracksTableLoader(TableLoader):
    table_name = "coreremovedtracks"
    order = -1
    sort_key = "TrackID"
    dereference = False

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

# Table generators

generator_registry = {}

class MetaGenerator(type):
    def __new__(cls, name, bases, namespace, **kwds):
        new_cls = super(MetaGenerator, cls).__new__(cls, name, bases, namespace)
        if bases:
            if new_cls.loader_class:
                loader = new_cls.loader_class
                generator_registry[loader] = new_cls
                new_cls.table_name = loader.table_name
                new_cls.sort_key = loader.key if loader.key else loader.sort_key
                new_cls.reindex = bool(loader.key or new_cls.sort_key not in key_registry)
        return new_cls

class TableGenerator(metaclass=MetaGenerator):
    loader_class = None

    def __init__(self, db, contents):
        self.db = db
        self.contents = contents

        self.new_id = 1

    def _filter_row(self, row):
        return True

    def generate_table(self):
        table_contents = self.contents[self.table_name]
        sqls = []
        if table_contents:
            column_names = sorted(list(table_contents.values())[0].keys())

            for row in sorted(table_contents.values(), key=self._get_sort_key):
                if self._filter_row(row):
                    if self.reindex:
                        self._reindex_row(row)
                    transformed_row = self._transform_row(row)

                    formatted = "INSERT INTO %s (%s) VALUES (%s)" % \
                        (self.table_name, ','.join(column_names), ','.join(['?'] * len(column_names)))
                    col_vals = [transformed_row[c] for c in column_names]
                    sql = self.db.preview_sql(formatted, *col_vals)
                    sqls.append(sql)

        return sqls

    def _get_sort_key(self, row):
        v = row[self.sort_key]
        if isinstance(v, dict):
            v = v[self.sort_key]
        return v

    def _reindex_row(self, row):
        row[self.sort_key] = self.new_id
        self.new_id += 1
        return row

    def _transform_row(self, row):
        row = self._unlink_row(row)
        return row

    def _unlink_row(self, row):
        new_row = {}
        for k, v in row.items():
            if isinstance(v, dict):
                new_row[k] = v[k]
            else:
                new_row[k] = v
        return new_row

class PrimarySourceTableGenerator(TableGenerator):
    loader_class = PrimarySourceTableLoader
class ArtistTableGenerator(TableGenerator):
    loader_class = ArtistTableLoader
class AlbumTableGenerator(TableGenerator):
    loader_class = AlbumTableLoader
class TrackTableGenerator(TableGenerator):
    loader_class = TrackTableLoader
class PlaylistEntryTableGenerator(TableGenerator):
    loader_class = PlaylistEntryTableLoader
class ShufflerTableGenerator(TableGenerator):
    loader_class = ShufflerTableLoader
class BookmarkTableGenerator(TableGenerator):
    loader_class = BookmarkTableLoader
class CacheModelTableGenerator(TableGenerator):
    loader_class = CacheModelTableLoader
class HyenaTableGenerator(TableGenerator):
    loader_class = HyenaTableLoader
class SmartPlaylistEntryTableGenerator(TableGenerator):
    loader_class = SmartPlaylistEntryTableLoader
class ShufflesTableGenerator(TableGenerator):
    loader_class = ShufflesTableLoader
class ShuffleModsTableGenerator(TableGenerator):
    loader_class = ShuffleModsTableLoader
class ConfigTableGenerator(TableGenerator):
    loader_class = ConfigTableLoader
class ArtDownloadTableGenerator(TableGenerator):
    loader_class = ArtDownloadTableLoader

class PlaylistGenerator(TableGenerator):
    def _reindex_row(self, row):
        self.reindexed[row[self.sort_key]] = self.new_id
        return super(PlaylistGenerator, self)._reindex_row(row)

class PlaylistTableGenerator(PlaylistGenerator):
    loader_class = PlaylistTableLoader
    reindexed = collections.defaultdict(dict)

class SmartPlaylistTableGenerator(PlaylistGenerator):
    loader_class = SmartPlaylistTableLoader
    reindexed = collections.defaultdict(dict)

    def _transform_row(self, row):
        new_row =  super(SmartPlaylistTableGenerator, self)._transform_row(row)

        # Transform table condition
        new_row["Condition"] = playlistid_re.sub(playlist_id_replace, new_row["Condition"])

        return new_row

class RemovedTracksTableGenerator(TableGenerator):
    loader_class = RemovedTracksTableLoader

    def _filter_row(self, row):
        return False # Don't regenerate this table

# Main driver class

class LibraryRegenerator(object):

    def __init__(self, target, dest, backup, cleanup, dryrun):

        self.schema = open("BansheeSchema.sql", 'rU').read()

        self.target = target
        self.dest = dest
        self.backup = backup
        self.cleanup_only = cleanup
        self.dryrun = dryrun

        self.old_db = db_glue.new(self.target)
        self.db = None

    def backup_library(self):
        """Copies the old library to the backup location."""

        print("Backing up %s to %s...\n" % (self.target, self.backup))
        if not self.dryrun:
            _dir = os.path.dirname(self.backup)
            if not os.path.isdir(_dir):
                os.makedirs(_dir)
            shutil.copy2(self.target, self.backup)

    def _remove_orphans(self, orphan_playlist, parent_playlist, parent_id,
                            orphan_id=None):

        ids = map(operator.itemgetter(parent_id),
                self.old_db.sql("SELECT %s FROM %s" % (parent_id, parent_playlist)))
        if orphan_id:
            ids = set(ids)
        else:
            ids = sorted(list(ids))

        if orphan_id:
            select_sql = "SELECT %s, %s FROM %s" % (parent_id, orphan_id, orphan_playlist)

            entries = self.old_db.sql(select_sql)
            orphaned = [e for e in entries if e[parent_id] not in ids]
            orphan_ids = list(map(operator.itemgetter(orphan_id), orphaned))
            if not orphan_ids:
                return 0

            delete_sql = "DELETE FROM %s WHERE %s IN (%s)" %\
                            (orphan_playlist, orphan_id, ','.join(map(str, orphan_ids)))
        else:
            delete_sql = "DELETE FROM %s WHERE %s NOT IN (%s)" %\
                            (orphan_playlist, parent_id, ','.join(map(str, ids)))

        print(delete_sql)
        return self.old_db.sql(delete_sql)

    def initial_cleanup(self):
        print("Removing orphaned playlist entries...")

        row_count = self._remove_orphans("CorePlaylistEntries", "CoreTracks",
                            "TrackID", "EntryID")
        print("%d rows deleted" % row_count)
        row_count = self._remove_orphans("CorePlaylistEntries", "CorePlaylists",
                            "PlaylistID")
        print("%d rows deleted" % row_count)

        print("Removing orphaned smart playlist entries...")

        row_count = self._remove_orphans("CoreSmartPlaylistEntries", "CoreTracks",
                            "TrackID", "EntryID")
        print("%d rows deleted" % row_count)
        row_count = self._remove_orphans("CoreSmartPlaylistEntries", "CoreSmartPlaylists",
                            "SmartPlaylistID")
        print("%d rows deleted" % row_count)

        print("Removing orphaned shuffles...")

        row_count = self._remove_orphans("CoreShuffles", "CoreShufflers", "ShufflerId")
        print("%d rows deleted" % row_count)

        print("Removing orphaned art downloads...")
        row_count = self._remove_orphans("CoverArtDownloads", "CoreAlbums", "AlbumID",
                                        "AlbumID")
        print("%d rows deleted" % row_count)

        print("Deleting smart playlists with invalid PrimarySourceIDs...")
        row_count = self._remove_orphans("CoreSmartPlaylists", "CorePrimarySources", "PrimarySourceID",
                                        "SmartPlaylistID")
        print("%d rows deleted" % row_count)

    def load_library(self):
        """Loads the contents of the old library into a Python data structure."""

        lib_contents = {}
        table_names = map(operator.methodcaller("lower"), TABLE_NAME_RE.findall(self.schema))
        
        self.loaders = []
        for table_name in table_names:
            loader = loader_registry[table_name](self.old_db, lib_contents)
            self.loaders.append(loader)

        self.loaders.sort(key=operator.attrgetter("order", "table_name"))

        for loader in self.loaders:
            print("Loading %s... " % loader.table_name, end='')
            rows = loader.load_table()
            lib_contents[loader.table_name] = rows
            print("%d rows found" % (len(rows)))

        print()

        return lib_contents

    def generate_new_library(self):
        """Creates a new, empty library with the proper schema at dest."""
        print("Generating a new empty library at %s..." % self.dest)

        if os.path.exists(self.dest):
            print("Deleting existing library at %s..." % self.dest)
            if not self.dryrun:
                os.remove(self.dest)
        print()
        if not self.dryrun:
            self.db = db_glue.new(self.dest)
        for stmt in self.schema.split(';'):
            print(stmt.strip() + ';')
            if not self.dryrun:
                self.db.sql(stmt)

        print()

    def recreate_db(self, contents):
        """Recreates the old library, in regenerated form, at dest, from the contents data structure."""

        print("Recreating DB from stored contents...\n")

        for loader in self.loaders:
            generator = generator_registry[loader.__class__](self.db if not self.dryrun else self.old_db, contents)

            sqls = generator.generate_table()
            print("Inserting %d rows in %s..." % (len(sqls), generator.table_name))
            if sqls:
                print('\n'.join(sqls[:5]))
                if not self.dryrun:
                    for sql in sqls:
                        self.db.sql(sql)

        print()

    def regenerate_library(self):

        if self.backup:
            self.backup_library()

        self.initial_cleanup()
        if not self.dryrun:
            self.old_db.commit()

        if not self.cleanup_only:
            old_lib_contents = self.load_library()

            # pprint(next(iter(old_lib_contents["coreplaylistentries"].items())))

            self.generate_new_library()

            self.recreate_db(old_lib_contents)

            if not self.dryrun:
                self.db.commit()
                self.db.close()
        self.old_db.close()

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', "--target", help="The banshee.db library file to regenerate. Defaults to %s"
                            % DEFAULT_LIBRARY, default=DEFAULT_LIBRARY)
    parser.add_argument('-d', "--dest", help="The location of the regenerated library. Defaults to the "
                                    "location of the old library.")
    parser.add_argument('-b', "--backup", help="Manually specify the location to back up the old library.")
    parser.add_argument('-n', "--dryrun", action="store_true", help="Display all the actions/SQL to be executed, "
                                                "do not make any actual changes.")
    parser.add_argument('-c', "--cleanup", action="store_true",
                            help="Only clean up the old library, do not regenerate")

    args = parser.parse_args()

    if not os.path.exists(args.target):
        print("The library %r does not exist." % args.target)
        return

    if args.dest is None:
        args.dest = args.target

    if args.dest == args.target:
        if args.backup is None:
            _dir, base = os.path.split(args.target)
            base, ext = os.path.splitext(base)
            args.backup = os.path.join(_dir, "%s_backup%s" % (base, ext))
    else:
        args.backup = None

    r = LibraryRegenerator(args.target, args.dest, args.backup, args.cleanup, args.dryrun)
    r.regenerate_library()

if __name__ == "__main__":
    main()
