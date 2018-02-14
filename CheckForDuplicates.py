import argparse
import operator

import db_glue

def check(db, table, fields):
    rows = db.sql("SELECT * FROM %s" % table)

    found = set()
    getter = operator.itemgetter(*fields)
    for row in rows:
        key = getter(row)
        if key in found:
            print("DUPLICATE FOUND: %s\n%s" % (key, row))
        else:
            found.add(key)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("dbfile")
    parser.add_argument("table")
    parser.add_argument("fields", nargs='+')

    args = parser.parse_args()

    check(db_glue.new(args.dbfile), args.table, args.fields)

if __name__ == "__main__":
    main()

