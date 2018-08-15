import os
import os.path
import argparse

from core.db_glue import new
from db.ql import QLDb

db_name = 'plays.db'
delta_db_name = 'delta_plays.db'

dropbox = os.environ.get('DROPBOX', None)
if dropbox:
    delta_db_name = os.path.join(dropbox, 'Music', delta_db_name)

def _make_where_str(track):
    l = []
    for key in ('title', 'artist', 'album', 'dn', 'tn'):
        value = getattr(track, key)
        if value is None:
            l.append('%s ISNULL' % key)
        else:
            l.append('%s = :%s' % (key, key))
    return ' AND '.join(l)

def get_db(fname):
    db = new(fname)
    db.sql("""CREATE TABLE IF NOT EXISTS plays
(title text NOT NULL,
artist text NOT NULL,
album text NOT NULL,
dn integer DEFAULT NULL,
tn integer DEFAULT NULL,
play_count integer DEFAULT 0)""")

    db.sql("CREATE INDEX IF NOT EXISTS plays_i ON plays (title, artist, album, dn, tn)")
    db.commit()

    return db

def get_delta_db(fname):
    db = new(fname)
    db.sql("""CREATE TABLE IF NOT EXISTS delta_plays
(title text NOT NULL,
artist text NOT NULL,
album text NOT NULL,
dn integer DEFAULT NULL,
tn integer DEFAULT NULL,
delta_plays integer DEFAULT 0,
total_plays integer DEFAULT 0)""")

    db.sql("CREATE INDEX IF NOT EXISTS delta_plays_i ON delta_plays (title, artist, album, dn, tn)")
    db.commit()

    return db

def save_delta(track, delta, delta_db, verbose):
    """Increments the entry for this track in the delta_plays table by delta, or creates one
       if none exists."""
    d = track.to_dict()
    d['play_count'] = play_count = track.play_count if track.play_count is not None else 0
    d['delta'] = delta

    # Check if the delta_plays table has a row for this track
    rows = delta_db.sql("""SELECT delta_plays, total_plays FROM delta_plays WHERE %s""" %
                        _make_where_str(track), **d)

    if len(rows) > 1:
        raise ValueError('Multiple delta rows found for %s' % track)
    elif len(rows) == 0:
        # Create a row for this track
        sql = """INSERT INTO delta_plays (title, artist, album, dn, tn, delta_plays, total_plays)
    VALUES (:title, :artist, :album, :dn, :tn, :delta, :play_count)"""
    else:
        # Update the existing row in the delta_plays table for this track; add the existing
        # delta to the new one
        current_delta = rows[0]['delta_plays']
        d['delta'] += current_delta
        sql = """UPDATE delta_plays SET delta_plays = :delta, total_plays = :play_count
    WHERE %s""" % _make_where_str(track)
    if verbose:
        print(delta_db.preview_sql(sql, **d))
    else:
        print('%s:\t+%d' % (track, delta))
    delta_db.sql(sql, **d)

def update_db(dryrun, verbose):
    """Saves track plays to the plays database/table, and deltas (new track play counts since
       last update) to the delta_plays db/table."""
    db = get_db(db_name)

    tracks = QLDb.load_all()

    new_delta = not os.path.exists(delta_db_name)
    delta_db = get_delta_db(delta_db_name)
    deltas_to_save = list()

    for track in tracks:
        sql = None

        # Check to see if this track is in the plays table
        d = track.to_dict()
        d['play_count'] = play_count = track.play_count if track.play_count is not None else 0
        rows = db.sql("""SELECT play_count FROM plays WHERE %s""" % _make_where_str(track), **d)

        if len(rows) > 1:
            raise ValueError('Multiple rows found for %s' % track)
        elif len(rows) == 0:
            # If this track doesn't have an entry in the plays table, add it
            sql = """INSERT INTO plays (title, artist, album, dn, tn, play_count) VALUES
    (:title, :artist, :album, :dn, :tn, :play_count)"""
            # If the delta file is newly created, the delta is the play count
            if new_delta and play_count:
                deltas_to_save.append((track, play_count))
        else:
            # If the delta file is newly created, the delta is the play count
            if new_delta and play_count:
                deltas_to_save.append((track, play_count))
            else:
                # Find the delta--the number of plays since the last time the plays table was updated
                delta = play_count - rows[0]['play_count']
                if delta > 0:
                    # Update the plays table entry for this track
                    sql = """UPDATE plays SET play_count = :play_count WHERE %s""" % _make_where_str(track)
                    # Save the delta
                    deltas_to_save.append((track, delta))
        # Run SQL
        if sql:
            if verbose:
                print(db.preview_sql(sql, **d))
            db.sql(sql, **d)

    if not dryrun:
        db.commit()

    # Save deltas if required
    if deltas_to_save:
        if verbose:
            print('\n')
        for track, delta in deltas_to_save:
            save_delta(track, delta, delta_db, verbose)
        if not dryrun:
            delta_db.commit()

    delta_db.close()
    db.close()

def update_play_counts(dryrun, verbose):
    """Increments the play counts of tracks in the music library by the deltas stored in the
       delta_plays DB/table, then wipes it."""

    if not os.path.exists(delta_db_name):
        print('No delta database found.')
        raise SystemExit

    delta_db = get_delta_db(delta_db_name)
    tracks = QLDb.load_all()

    for track in tracks:
        d = track.to_dict()

        # Check if the delta_plays table has a row for this track
        rows = delta_db.sql("""SELECT delta_plays, total_plays FROM delta_plays WHERE %s""" %
                            _make_where_str(track), **d)
        if len(rows) > 1:
            raise ValueError('Multiple delta rows found for %s' % track)
        elif len(rows) > 0:
            delta = rows[0]['delta_plays']
            if track.play_count is None:
                track.play_count = delta
            else:
                track.play_count += delta
            print('%s:\t+%d' % (track, delta))
            if not dryrun:
                track.save()

            sql = 'DELETE FROM delta_plays WHERE %s' % _make_where_str(track)
            if verbose:
                print(delta_db.preview_sql(sql, **d))
            delta_db.sql(sql, **d)

    if not dryrun:
        QLDb.commit()

    extra_rows = delta_db.sql('SELECT * FROM delta_plays')
    for row in extra_rows:
        print('WARNING:\tUnmatched row - %(title)s, %(artist)s, %(album)s, %(dn)s, %(tn)s' % row)
    if not dryrun:
        delta_db.commit()
        delta_db.close()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--test', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('action', choices=['up', 'down'])

    args = parser.parse_args()

    if args.action == 'up':
        update_db(args.test, args.verbose)
    else:
        update_play_counts(args.test, args.verbose)

if __name__ == '__main__':
    main()
