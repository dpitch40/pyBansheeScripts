import argparse
from pprint import pprint
import operator

import db_glue

def check(db, table, fields):
    rows = db.sql("SELECT * FROM %s" % table)

    found = set()
    getter = operator.itemgetter(*fields)
    for row in rows:
        key = getter(row)
        if key in found:
            print("DUPLICATE FOUND: %s" % str(key))
            pprint(row)
        else:
            found.add(key)

def main():
    parser = argparse.ArgumentParser(description='Searches a table in a selected Banshee library file '
                                    'for duplicates.')

    parser.add_argument("dbfile", help='The Banshee library file to search.')
    parser.add_argument("table", help='The table to search.')
    parser.add_argument("fields", nargs='+', help='The fields to match on for duplicate detection.')

    args = parser.parse_args()

    check(db_glue.new(args.dbfile), args.table, args.fields)

if __name__ == "__main__":
    main()

