"""
Usage notes

First, back up your Banshee library and export all playlists you want to keep

Then delete your Banshee library from its initial location and reopen Banshee to
make a new, blank one. Reimport all your music/movies (this may take a while).

Close Banshee and run this script on your old and new libraries to copy over metadata
like play count and rating.

Then reopen Banshee and reimport your playlists/recreate your smart playlists. (Note that
tracks containing a # will not import correctly from .m3u playlist files and will have to
be re-added manually).

Your library should now be running more smoothly!
"""

import argparse
import os.path
from operator import itemgetter

from db_glue import DB

MATCHING_FIELD = "Uri"
FIELDS_TO_COPY = ["PlayCount", "SkipCount", "Rating", "LastPlayedStamp", "LastSkippedStamp",
                  "DateAddedStamp", "DateUpdatedStamp"]

def migrate_metadata(oldlib, newlib, dryrun):

    track_mapping = {}

    old_uris = []
    new_uris = []
    matched_uris = set()

    with DB(oldlib) as db:
        rows = db.sql("SELECT TrackID, %s, %s FROM CoreTracks" % (MATCHING_FIELD, ', '.join(FIELDS_TO_COPY)))

        for row in rows:
            old_uris.append(row[MATCHING_FIELD])
            track_mapping[row[MATCHING_FIELD]] = row

    matched = 0

    with DB(newlib) as db:
        new_rows = db.sql("SELECT TrackID, %s FROM CoreTracks" % MATCHING_FIELD)

        for row in new_rows:
            new_uri = row[MATCHING_FIELD]
            new_uris.append(new_uri)
            if new_uri in track_mapping:
                matched += 1
                matched_uris.add(new_uri)
                track_mapping[new_uri]["NewTrackID"] = row["TrackID"]

        print("%d old tracks, %d new tracks, %d matched" % (len(track_mapping),
                    len(new_rows), matched))

        print("Old not matched:\n%s" % ('\n'.join([u for u in old_uris if u not in matched_uris])))
        print("New not matched:\n%s" % ('\n'.join([u for u in new_uris if u not in matched_uris])))

        for track in sorted(track_mapping.values(), key=itemgetter(MATCHING_FIELD)):
            if "NewTrackID" not in track:
                continue

            update_stmts = ', '.join(["%s = ?" % field for field in FIELDS_TO_COPY])
            update_values = [track[field] for field in FIELDS_TO_COPY]
            db.sql("UPDATE CoreTracks SET %s WHERE TrackID = ?" % update_stmts,
                    *(update_values + [track["NewTrackID"]]))

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
