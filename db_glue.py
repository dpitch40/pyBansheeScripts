"""Database integration class. Handles all I/O with the sqlite database."""

import sqlite3 as sql
import os.path
import os
import re
import operator

from six.moves.urllib.request import url2pathname, pathname2url

defaultLoc = os.path.expanduser(os.path.join('~', '.config', 'banshee-1', 'banshee.db'))

# Characters to escape when converting to SQL-compatible strings
PATHNAME_CHARS = "~!@$&*()-_=+:',."

initialPeriodRe = re.compile(r"^(\.+)")

def new(loc=defaultLoc):
    """Returns a new cursor to the database. (Creates the database if none exists)"""
    db = DB(loc)
    return db

def pathname2sql(path):
    pathDir, pathBase = os.path.split(path)
    # Fix filenames with periods at the start
    m = initialPeriodRe.match(pathBase)
    if m:
        numPeriods = len(m.group(1))
        path = os.path.join(pathDir, "%s%s" % ('_' * numPeriods, pathBase[numPeriods:]))
    sqlloc = pathname2url(path)
    # Escape troublesome characters
    for c in PATHNAME_CHARS:
          sqlloc = sqlloc.replace("%%%X" % ord(c), c)
    return "file://" + sqlloc

def sql2pathname(uri):
    # Just strip the "file://" from the start and run through url2pathname
    return url2pathname(uri[7:])

class DB:
    """An object representing a cursor to a database."""
    
    __slots__ = ('conn', 'curs')
    
    def __init__(self, path):
        self.conn = sql.connect(path)
        self.curs = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, _type, value, traceback):
        self.close()

    def close(self):
        self.conn.close()
    
    def commit(self):
        """Saves the changes made with this cursor."""
        self.conn.commit()
    
    def delete(self, table, id_cols):
        self.sql("DELETE FROM %s WHERE %s" % (table,
                ' AND '.join(['%s = :%s' % (k,k) for k in id_cols.keys()])), id_cols)
  
    def dict_prep(self, d):
        for k in d.keys():
            if d[k] == '' or d[k] is None:
                d[k] = 'NULL'

    def get_tables(self):
        rows = self.sql("SELECT name FROM sqlite_master WHERE type='table'")
        return sorted(map(operator.itemgetter('name'), rows))
    
    def insert(self, table, id_cols, nonid_cols):
        all_cols = id_cols.copy()
        all_cols.update(nonid_cols)
        self.dict_prep(all_cols)
        insert_cols = [k for k, v in all_cols.items() if v is not None and k in columns[table]]
        self.sql("INSERT INTO %s (%s) VALUES (%s)" % 
                (table, ','.join(insert_cols), ','.join([":%s" % i for i in insert_cols])), all_cols)
    
    def last_insert_rowid(self):
        return self.sql("SELECT last_insert_rowid() AS id")[0]["id"]
    
    def pack_rows(self, desc, rows):
        result = list()
        for row in rows:
            result.append(dict(((desc[i][0], row[i]) for i in range(len(desc)))))
        return result

    def preview_sql(self, sqlstr, *args, **kwargs):
        quoted_args = []
        quoted_kwargs = {}

        for v in args:
            quoted_args.append(self._quote_value(v))

        for k, v in kwargs.items():
            quoted_kwargs[k] = self._quote_value(v)

        # Replace non-keyword arguments in two steps, in case any of them contain question marks
        for i, quoted in enumerate(quoted_args):
            sqlstr = sqlstr.replace('?', "%%QARG%d%%" % i, 1)
        for i, quoted in enumerate(quoted_args):
            sqlstr = sqlstr.replace("%%QARG%d%%" % i, quoted, 1)

        for k, quoted in quoted_kwargs.items():
            sqlstr = sqlstr.replace(':%s' % k, quoted)

        return sqlstr

    def _quote_value(self, value):
        self.curs.execute("SELECT quote(?)", (value,))
        quoted = self.curs.fetchone()[0]
        return str(quoted)
    
    def sql(self, sqlstr, *args, **kwargs):
        """Executes the sql in the string, returns results (if any) as a list of
            dicts."""
        if args and kwargs:
            raise ValueError("Cannot specify both args and kwargs")
        if args:
            parms = args
        else:
            parms = kwargs
        
        self.curs.execute(sqlstr, parms)
        if (self.curs.description is None):
            return self.curs.rowcount
        else:
            return self.pack_rows(self.curs.description, self.curs.fetchall())
    
    def update(self, table, id_cols, nonid_cols):
        ids = id_cols.copy()
        nonids = nonid_cols.copy()
        all_cols = id_cols.copy()
        all_cols.update(nonid_cols)
        self.dict_prep(ids)
        self.dict_prep(nonids)
        self.sql("UPDATE %s SET %s WHERE %s" % 
                (table, ','.join(["%s = :%s" % (k,k) for k in nonids.keys() if k in columns[table]]), 
                          ' AND '.join(["%s = :%s" % (k,k) for k in ids.keys()])), all_cols)
