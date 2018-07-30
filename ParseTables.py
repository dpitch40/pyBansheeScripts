import urllib2
import sys
import re
import os.path
import Util
import csv
import StringIO
import argparse
import datetime
from collections import defaultdict
import Config

from bs4 import BeautifulSoup

#regex for times
timeRe = re.compile(r"(\d+):(\d{2})")
# regex for the domain name of a url
urlRe = re.compile(r"^http(?:s)?://(?:www\.)?(?:[^\.]+\.)*([^\.]+)\.com")

fieldOrdering = ["Title", "Artist", "AlbumArtist", "Album", "Genre", "Year", "Duration",
                    "TrackNumber", "TrackCount", "Disc", "DiscCount"]
fieldOrderingSet = set(fieldOrdering)

strKeys = set(["Title", "Artist", "Album", "Genre", "AlbumArtist"])

hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
       # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       # 'Accept-Encoding': 'gzip, deflate, sdch, br',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

def parseTimeStr(timeStr):
    if not isinstance(timeStr, str) and not isinstance(timeStr, unicode):
        return timeStr
    m = timeRe.match(timeStr)
    if m:
        if m.group(1) is not None:
            return 60 * int(m.group(1)) + int(m.group(2))
        else:
            return int(m.group(2))
    else:
        return None

###############################################################################
# Track list from html
###############################################################################

domainParsers = dict()
def registerParser(site):
    def _inner(func):
        domainParsers[site] = func
        return func
    return _inner

@registerParser("metal-archives")
def parseMATracklist(soup):
    albumInfo = soup.find(id="album_info")
    album = albumInfo.find(class_="album_name").string
    artist = albumInfo.find(class_="band_name").a.string
    dateStr = albumInfo.find("dt", string="Release date:").find_next_sibling("dd").string
    year = int(dateStr.rsplit(None, 1)[-1])

    songTable = soup.findAll("table", class_="table_lyrics")[0]
    tracks = [(artist, album, year)]
    discNum = None
    for tableRow in songTable.findAll("tr"):
        if tableRow.get("class", None) == ["discRow"]:
            discNum = int(tableRow.stripped_strings.next().split()[1])
        title = tableRow.find("td", class_="wrapWords")
        if title is None:
            continue
        trackTitle = title.string.strip()
        trackLen = parseTimeStr(title.find_next_sibling("td").string)

        if discNum is not None:
            tracks.append((trackTitle, trackLen, discNum))
        else:
            tracks.append((trackTitle, trackLen))

    return tracks

@registerParser("allmusic")
def parseAllMusictracklist(soup):
    releaseDateDiv = soup.find("div", class_="release-date")
    releaseDateStr = releaseDateDiv.find("span").string
    year = int(releaseDateStr.rsplit(None, 1)[-1])

    artistH = soup.find("h2", class_="album-artist")
    artist = artistH.stripped_strings.next()
    albumH = artistH.find_next_sibling("h1")
    album = albumH.stripped_strings.next()

    tracks = [(artist, album, year)]

    tracksSection = soup.find("section", class_="track-listing")
    tBodies = list(tracksSection.findAll("tbody"))
    hasMultipleDiscs = len(tBodies) > 1
    for discNum, tBody in enumerate(tBodies):
        for tableRow in tBody.findAll("tr"):
            titleDiv = tableRow.find("div", class_="title")
            title = titleDiv.stripped_strings.next()

            timeDiv = tableRow.find("td", class_="time")
            try:
                trackLen = parseTimeStr(timeDiv.stripped_strings.next())
            except StopIteration:
                trackLen = 0

            if hasMultipleDiscs:
                tracks.append((title, trackLen, discNum+1))
            else:
                tracks.append((title, trackLen))

    return tracks

@registerParser("bandcamp")
def parseBandcampTracklist(soup):
    name_section = soup.find('div', id='name-section')
    album = next(name_section.find('h2', itemprop='name').stripped_strings)
    artist = next(name_section.find('span', itemprop='byArtist').stripped_strings)
    year = int(soup.find('meta', itemprop='datePublished')['content'][:4])

    tracks = [(artist, album, year)]

    track_table = soup.find('table', id='track_table')
    for row in track_table.find_all('tr'):
        # TODO: Support multiple discs
        title = next(row.find('span', itemprop='name').stripped_strings)
        time = parseTimeStr(next(row.find('span', class_='time').stripped_strings))
        tracks.append((title, time))

    return tracks

def parseTracklistFromUrl(url):
    domain = urlRe.match(url).group(1).lower()
    if domain not in domainParsers:
        raise KeyError, "No parser defined for domain %r" % domain

    result = None
    request = urllib2.Request(url, headers=hdr)
    f = urllib2.urlopen(request)
    try:
        html = f.read()
    except:
        raise
    else:
        soup = BeautifulSoup(html, "lxml")
        result = domainParsers[domain](soup)
    finally:
        f.close()

    return result

###############################################################################
# Track list from text file
###############################################################################

def readSimpleTrackList(fname):
    """Reads a tracklist consisting of a row of metadata followed 
by rows of track data."""
    with open(fname, 'r') as f:
        reader = csv.reader(f, delimiter='\t', skipinitialspace=True)
        tracklist = [reader.next()]
        for row in reader:
            if len(row) > 1:
                seconds = parseTimeStr(row[1])
                if seconds is not None:
                    row[1] = seconds
                else:
                    row[1] = 0
                # Disc num
                if len(row) == 3:
                    row[2] = int(row[2])
            else:
                row.append(0)
            tracklist.append(row)
    return tracklist

# Reads a track list from a file
def readAugmentedTrackList(fName):
    with open(fName, 'r') as f:
        reader = csv.DictReader(f)
        tracklist = list()
        for row in reader:
            if "Duration" in row:
                row["Duration"] = parseTimeStr(row["Duration"])
            for k, v in row.items():
                row[k] = Util.convertStrValue(v, k not in strKeys)
            tracklist.append(row)
    return tracklist

###############################################################################
# Common/tracklist manipulation functions
###############################################################################

# Changes a simple tracklist into a full one
def augmentTrackList(trackList):
    # Read initial metadata
    firstRow = trackList[0]
    trackList = trackList[1:]

    artist = Util.convertStrValue(firstRow[0], False)
    album = Util.convertStrValue(firstRow[1], False)
    year = Util.convertStrValue(firstRow[2])
    if len(firstRow) == 3:
        genre = None
    else:
        genre = Util.convertStrValue(firstRow[3], False)

    # Get max track and disc numbers
    trackCounts = defaultdict(int)
    maxDN = 0
    for row in trackList:
        if len(row) == 3:
            disc = row[2]
            maxDN = max(disc, maxDN)
        else:
            disc = None
        trackCounts[disc] += 1

    # Populate the table of dicts
    lastDN = 1
    curTN = 0
    if maxDN == 0:
        maxDN = None
    augmentedTrackList = list()
    for row in trackList:
        title, time = row[:2]
        if len(row) == 2:
            disc = None
        else:
            disc = row[2]
        time = parseTimeStr(time) * 1000 # Time in ms

        # Update track number; if we have changed discs, reset it and update the disc number
        curTN += 1
        if disc and disc != lastDN:
            curTN = 1
            lastDN = disc

        if not isinstance(title, unicode):
            title = unicode(title, Config.UnicodeEncoding)
        row =  {"Title": title,
                "Artist": artist,
                "AlbumArtist": artist,
                "Album": album,
                "Genre": genre,
                "Year": year,
                "Duration": time,
                "TrackNumber": curTN,
                "TrackCount": trackCounts[disc],
                "Disc": disc,
                "DiscCount": maxDN}

        augmentedTrackList.append(row)

    return augmentedTrackList

# Reverse of augmentTrackList
def simplifyTrackList(trackList):
    firstRow = [trackList[0]["Artist"], trackList[0]["Album"], trackList[0]["Year"]]
    genre = trackList[0]["Genre"]
    if genre:
        firstRow.append(genre)

    rows = [firstRow]
    for row in trackList:
        simpleRow = [row["Title"], row["Duration"] / 1000]
        if row["Disc"]:
            simpleRow.append(row["Disc"])
        rows.append(simpleRow)
    return rows

# Get a track list from a URL or file
def getTrackList(loc, **kwargs):
    if os.path.exists(loc):
        if loc.endswith(".csv"):
            tl = readAugmentedTrackList(loc)
        else:
            tl = readSimpleTrackList(loc)
    else:
        tl = parseTracklistFromUrl(loc)

    # Convert kwargs
    for k, v in kwargs.items():
        kwargs[k] = Util.convertStrValue(v)
    if isinstance(tl[0], dict):
        map(lambda r: r.update(kwargs), tl)
    else:
        if "Genre" in kwargs and len(tl[0]) == 3:
            tl[0] = tl[0] + (kwargs["Genre"],)

    return tl

# Gets a track list from the specified location; makes sure it is augmented
def getAugmentedTrackList(loc, **kwargs):
    tl = getTrackList(loc, **kwargs)
    if not isinstance(tl[0], dict):
        tl = augmentTrackList(tl)
    return tl

# Sort comparison function for field names in a track list
def _compareFields(a, b):
    if a in fieldOrderingSet:
        if b in fieldOrderingSet:
            return fieldOrdering.index(a) - fieldOrdering.index(b)
        else:
            return -1
    elif b in fieldOrderingSet:
        return 1
    else:
        return cmp(a, b)

# Format a track list for printing
def formatTrackList(trackList, buf=None):
    ioBuf = False
    if buf is None:
        buf = StringIO.StringIO()
        ioBuf = True
    headers = sorted(trackList[0].keys(), cmp=_compareFields)
    writer = csv.DictWriter(buf, headers, lineterminator='\n')
    writer.writeheader()
    for row in trackList:
        encodedRow = dict()
        for k, v in row.items():
            if isinstance(v, unicode):
                encodedRow[k] = v.encode(Config.UnicodeEncoding)
            else:
                encodedRow[k] = v
        writer.writerow(encodedRow)
    if ioBuf:
        return buf.getvalue()

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Get a track list from an external source.")
    parser.add_argument("location", help="The location (URL or file) to get metadata from.")
    parser.add_argument('-e', "--extra", action="append", nargs=2, default=list(),
                                help="Specify extra data fields for these tracks.")
    parser.add_argument('-o', "--out", help="Output to a file.")
    parser.add_argument('-s', "--simple", action="store_true",
                help="Use the simple tracklist format.")
    args = parser.parse_args()

    tl = getTrackList(args.location, **dict(args.extra))
    simpleTracklist = not isinstance(tl[0], dict)

    if args.simple:
        if not simpleTracklist:
            tl = simplifyTrackList(tl)
        def encodeRowElement(r):
            if isinstance(r, unicode):
                return r.encode(Config.UnicodeEncoding)
            else:
                return r
        tl = map(lambda row: map(encodeRowElement, row), tl)
        if args.out:
            with open(args.out, 'w') as f:
                writer = csv.writer(f, delimiter='\t', lineterminator='\n')
                writer.writerows(tl)
        else:
            print '\n'.join(['\t'.join(map(str, l)) for l in tl])
    else:
        if simpleTracklist: # Augment the tracklist
            tl = augmentTrackList(tl)

        if args.out:
            with open(args.out, 'w') as f:
                formatTrackList(tl, f)
        else:
            print formatTrackList(tl).strip()
