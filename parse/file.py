# import Util
# import csv

# strKeys = set(["Title", "Artist", "Album", "Genre", "AlbumArtist"])

# def readSimpleTrackList(fname):
#     """Reads a tracklist consisting of a row of metadata followed 
# by rows of track data."""
#     with open(fname, 'r') as f:
#         reader = csv.reader(f, delimiter='\t', skipinitialspace=True)
#         tracklist = [reader.next()]
#         for row in reader:
#             if len(row) > 1:
#                 seconds = parseTimeStr(row[1])
#                 if seconds is not None:
#                     row[1] = seconds
#                 else:
#                     row[1] = 0
#                 # Disc num
#                 if len(row) == 3:
#                     row[2] = int(row[2])
#             else:
#                 row.append(0)
#             tracklist.append(row)
#     return tracklist

# # Reads a track list from a file
# def readAugmentedTrackList(fName):
#     with open(fName, 'r') as f:
#         reader = csv.DictReader(f)
#         tracklist = list()
#         for row in reader:
#             if "Duration" in row:
#                 row["Duration"] = parseTimeStr(row["Duration"])
#             for k, v in row.items():
#                 row[k] = Util.convertStrValue(v, k not in strKeys)
#             tracklist.append(row)
#     return tracklist