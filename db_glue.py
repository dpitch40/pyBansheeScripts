"""Database integration class. Handles all I/O with the sqlite database."""

import sqlite3 as sql
import os.path
import os
import urllib
import re

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
    sqlloc = urllib.pathname2url(path)
    # Escape troublesome characters
    for c in PATHNAME_CHARS:
          sqlloc = sqlloc.replace("%%%X" % ord(c), c)
    return "file://" + sqlloc

def sql2pathname(uri):
    # Just strip the "file://" from the start and run through url2pathname
    return urllib.url2pathname(uri[7:])

class DB:
    """An object representing a cursor to a database."""
    
    __slots__ = ('conn', 'curs')
    
    def __init__(self, path):
        self.conn = sql.connect(path)
        self.curs = self.conn.cursor()

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
        r = xrange(len(desc))
        for row in rows:
            result.append(dict(((desc[i][0], row[i]) for i in r)))
        return result
    
    def sql(self, sqlstr, parms={}, debug=False):
        """Executes the sql in the string, returns results (if any) as a list of
            dicts.
            debug: If true, prints the sql string."""
        if debug:
            print '\n' + sqlstr
            print str(parms)
        
        self.curs.execute(sqlstr, parms)
        if (self.curs.description is None):
            return None
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
