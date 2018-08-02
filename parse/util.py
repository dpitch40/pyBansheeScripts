import re
import os.path
import Util
import csv
from io import StringIO
from collections import defaultdict
import Config

#regex for times
time_re = re.compile(r"(\d+):(\d{2})")

# fieldOrdering = ["Title", "Artist", "AlbumArtist", "Album", "Genre", "Year", "Duration",
#                     "TrackNumber", "TrackCount", "Disc", "DiscCount"]
# fieldOrderingSet = set(fieldOrdering)

def parse_time_str(time_str):
    if not isinstance(time_str, str) and not isinstance(time_str, unicode):
        return time_str
    m = time_re.match(time_str)
    if m:
        if m.group(1) is not None:
            return 60 * int(m.group(1)) + int(m.group(2))
        else:
            return int(m.group(2))
    else:
        return None

# # Changes a simple tracklist into a full one
# def augmentTrackList(trackList):
#     # Read initial metadata
#     firstRow = trackList[0]
#     trackList = trackList[1:]

#     artist = Util.convertStrValue(firstRow[0], False)
#     album = Util.convertStrValue(firstRow[1], False)
#     year = Util.convertStrValue(firstRow[2])
#     if len(firstRow) == 3:
#         genre = None
#     else:
#         genre = Util.convertStrValue(firstRow[3], False)

#     # Get max track and disc numbers
#     trackCounts = defaultdict(int)
#     maxDN = 0
#     for row in trackList:
#         if len(row) == 3:
#             disc = row[2]
#             maxDN = max(disc, maxDN)
#         else:
#             disc = None
#         trackCounts[disc] += 1

#     # Populate the table of dicts
#     lastDN = 1
#     curTN = 0
#     if maxDN == 0:
#         maxDN = None
#     augmentedTrackList = list()
#     for row in trackList:
#         title, time = row[:2]
#         if len(row) == 2:
#             disc = None
#         else:
#             disc = row[2]
#         time = parseTimeStr(time) * 1000 # Time in ms

#         # Update track number; if we have changed discs, reset it and update the disc number
#         curTN += 1
#         if disc and disc != lastDN:
#             curTN = 1
#             lastDN = disc

#         if not isinstance(title, unicode):
#             title = unicode(title, Config.UnicodeEncoding)
#         row =  {"Title": title,
#                 "Artist": artist,
#                 "AlbumArtist": artist,
#                 "Album": album,
#                 "Genre": genre,
#                 "Year": year,
#                 "Duration": time,
#                 "TrackNumber": curTN,
#                 "TrackCount": trackCounts[disc],
#                 "Disc": disc,
#                 "DiscCount": maxDN}

#         augmentedTrackList.append(row)

#     return augmentedTrackList

# # Reverse of augmentTrackList
# def simplifyTrackList(trackList):
#     firstRow = [trackList[0]["Artist"], trackList[0]["Album"], trackList[0]["Year"]]
#     genre = trackList[0]["Genre"]
#     if genre:
#         firstRow.append(genre)

#     rows = [firstRow]
#     for row in trackList:
#         simpleRow = [row["Title"], row["Duration"] / 1000]
#         if row["Disc"]:
#             simpleRow.append(row["Disc"])
#         rows.append(simpleRow)
#     return rows

# # Sort comparison function for field names in a track list
# def _compareFields(a, b):
#     if a in fieldOrderingSet:
#         if b in fieldOrderingSet:
#             return fieldOrdering.index(a) - fieldOrdering.index(b)
#         else:
#             return -1
#     elif b in fieldOrderingSet:
#         return 1
#     else:
#         return cmp(a, b)

# # Format a track list for printing
# def formatTrackList(trackList, buf=None):
#     ioBuf = False
#     if buf is None:
#         buf = StringIO()
#         ioBuf = True
#     headers = sorted(trackList[0].keys(), cmp=_compareFields)
#     writer = csv.DictWriter(buf, headers, lineterminator='\n')
#     writer.writeheader()
#     for row in trackList:
#         encodedRow = dict()
#         for k, v in row.items():
#             if isinstance(v, unicode):
#                 encodedRow[k] = v.encode(Config.UnicodeEncoding)
#             else:
#                 encodedRow[k] = v
#         writer.writerow(encodedRow)
#     if ioBuf:
#         return buf.getvalue()