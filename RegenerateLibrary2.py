import argparse
import os.path
from operator import itemgetter

from db_glue import DB

MATCHING_FIELD = "Uri"
FIELDS_TO_COPY = ["PlayCount", "SkipCount", "Rating", "LastPlayedStamp", "LastSkippedStamp",
                  "DateAddedStamp", "DateUpdatedStamp"]

def migrate_metadata(oldlib, newlib, dryrun):

    track_mapping = {}

    with DB(oldlib) as db:
        rows = db.sql("""SELECT TrackID, %s, %s FROM CoreTracks""" % (MATCHING_FIELD, ', '.join(FIELDS_TO_COPY)))
        num_old_rows = len(rows)

        for row in rows:
            track_mapping[row[MATCHING_FIELD]] = row

    matched = 0

    with DB(newlib) as db:
        new_rows = db.sql("SELECT TrackID, %s FROM CoreTracks" % MATCHING_FIELD)
        num_new_rows = len(now_rows)

        for row in new_rows:
            new_uri = row[MATCHING_FIELD]
            if new_uri in track_mapping:
                matched += 1
                track_mapping[new_uri]["NewTrackID"] = row["TrackID"]

        print("%d old tracks, %d new tracks, %d matched" % (num_old_rows, num_new_rows, matched))

        for track in sorted(track_mapping.values(), key=itemgetter(MATCHING_FIELD)):
            if "NewTrackID" not in track:
                continue

            update_stmts = ', '.join(["%s = ?" % field for field in FIELDS_TO_COPY])
            update_values = [track[field] for field in FIELDS_TO_COPY]
            db.sql("UPDATE CoreTracks SET %s WHERE TrackID = ?" % update_stmts,
                    tuple(update_values) + (track["NewTrackID"],))

        if not dryrun:
            db.commit()

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', "--dryrun", action="store_true")
    parser.add_argument("oldlib")
    parser.add_argument("newlib")

    args = parser.parse_args()

    if not os.path.isfile(args.oldlib):
        print("oldlib must be an existing library file")
    elif not os.path.isfile(args.newlib):
        print("newlib must be an existing library file")
    else:
        migrate_metadata(args.oldlib, args.newlib, args.dryrun)

if __name__ == "__main__":
    main()
