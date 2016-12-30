import urllib
import sys
import re
import os.path
import Util
import csv
import StringIO
import argparse

tablenums =  {'metal-archives': 1,
                 'allmusic': 0}

titleindices = {'metal-archives': 1}

rowlens = {'metal-archives': 4,
              'allmusic': 5}

searchstrs = {'allmusic': {'Artist': '<h3 class="album-artist"',
                                    'Album': '<h2 class="album-title"',
                                    'Date': '<h4>Release Date</h4>'},
                  'metal-archives': {'Artist': 'class="band_name"',
                                            'Album': 'class="album_name"',
                                            'Date': '<dt>Release date:</dt>'}}

#regex for an ordinal number, e.g. 3.
ordre = re.compile(r'^[1-9]\d\.?$')
#regex for an HTML tag, some tagless text, then the closing tag
tagre = re.compile(r'<(\w+)( [^>]*)?>\s*([^<>]+)</\1', flags=re.MULTILINE)
#regex for a year
datere = re.compile(r'(\d{4})')
#regex for flags
flagre = re.compile(r'^[a-z]\d(?:,\d)*')
#regex for times
timeRe = re.compile(r"(\d+):(\d{2})")

fieldOrdering = ["Title", "Artist", "AlbumArtist", "Album", "Genre", "Year", "Duration",
                    "TrackNumber", "TrackCount", "Disc", "DiscCount"]
fieldOrderingSet = set(fieldOrdering)

strKeys = set(["Title", "Artist", "Album", "Genre", "AlbumArtist"])

def parseTime(timeStr):
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

def formattime(mins, secs):
    return "%d:%s" % (mins + secs/60, str(secs%60).zfill(2))

def divide(html, tag):
    st = '<%s' % tag
    en = '</%s>' % tag
    items = list()
    startitem = html.find(st)
    startitem = html.find('>', startitem) + 1
    enditem = html.find(en, startitem)
    while startitem > -1:
        items.append(html[startitem:enditem].strip())
        startitem = html.find(st, enditem)
        if startitem > -1:
            startitem = html.find('>', startitem) + 1
            enditem = html.find(en, startitem)
    return items

def removetags(html):
    els = list()
    i = html.find('<')
    if i > -1:
        els.append(html[:i])
        while i > -1:
            j = html.find('>', i)
            i = html.find('<', j)
            if i > -1:
                els.append(html[j+1:i])
        els.append(html[j+1:])
        return ''.join(els).strip()
    else:
        return html.strip()

def searchforelement(html, domain, elname, matchsame=False):
    searchstr = searchstrs[domain][elname]
    i = html.find(searchstr)
    if not matchsame:
        tag = tagre.search(html, i+len(searchstr)-1)
    else:
        tag = tagre.search(html, i-1)
    return tag.group(3).strip()

def findtables(html):
    htmlOrig = html.decode("latin")
    html = html.lower().decode("latin")

    tindex = html.find('<table')
    captured = '<table'
    start_block = tindex
    t_level = 1
    while tindex > -1:
        next_start = html.find('<table', tindex + len(captured))
        next_end = html.find('</table>', tindex + len(captured))
        if next_start < next_end and next_start != -1:
            tindex = next_start
            if t_level == 0:
                start_block = tindex
            t_level += 1
            captured = '<table'
        else:
            tindex = next_end
            t_level -= 1
            if t_level == 0:
                yield htmlOrig[start_block:next_end+len('</table>')]
            captured = '</table>'

def getTrackListFromUrl(url):
    f = urllib.urlopen(url)
    html = f.read()
    f.close()
    domain = url[url.find('www.') + 4:].split('.', 1)[0]
    
    artist = searchforelement(html, domain, 'Artist').replace("&amp;", '&')
    album =  searchforelement(html, domain, 'Album', True).replace("&amp;", '&')
    date = searchforelement(html, domain, 'Date')
    m = datere.search(date)
    if m:
        year = m.group(1)
    else:
        year = None

    tables = list(findtables(html))

    tab = tables[tablenums[domain]]
    tab = tab[tab.find('<tbody>') + 7:tab.rfind('</tbody>')]

    rowstrings = divide(tab, 'tr')
    rows = map(lambda x: map(removetags, divide(x, 'td')), rowstrings)
    
    tracklist = [(artist, album, year)]
    curDiscNum = None
    for r in rows:
        if r[0].startswith("Disc"):
            d, discNum = r[0].split()[:2]
            curDiscNum = int(discNum)
        elif len(r) == rowlens[domain] or (domain == 'allmusic' and len(r) > rowlens[domain]):
            # print r
            time = None
            for e in reversed(r):
                t = parseTime(e)
                if t:
                    time = e
            if domain != 'allmusic':
                title = r[titleindices[domain]]
            else:
                i = 0
                while len(r[i]) == 0:
                    i += 1
                index = i + 1
                title = r[index].split('\n', 1)[0].strip()
            title = title.encode("latin").replace("&amp;", '&')
            if curDiscNum is None:
                tracklist.append((title, time))
            else:
                tracklist.append((title, time, curDiscNum))
    return tracklist

def readSimpleTrackList(fname):
    """Reads a tracklist consisting of a row of metadata followed 
by rows of track data."""
    with open(fname, 'r') as f:
        reader = csv.reader(f, delimiter='\t', skipinitialspace=True)
        tracklist = [reader.next()]
        for row in reader:
            if len(row) > 1:
                seconds = parseTime(row[1])
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

# Comparison function for field names in a track list
def compareFields(a, b):
    if a in fieldOrderingSet:
        if b in fieldOrderingSet:
            return fieldOrdering.index(a) - fieldOrdering.index(b)
        else:
            return -1
    elif b in fieldOrderingSet:
        return 1
    else:
        return cmp(a, b)

def convertStrValue(v, unicodeEncoding="utf-8", convertNumbers=True):
    if v == '' or v is None:
        return None
    elif isinstance(v, str):
        if convertNumbers and v.isdigit():
            return int(v)
        else:
            return unicode(v, unicodeEncoding)
    else:
        return v

# Reads a track list from a file
def readTrackList(fName, unicodeEncoding):
    with open(fName, 'r') as f:
        reader = csv.DictReader(f)
        tracklist = list()
        for row in reader:
            if "Duration" in row:
                row["Duration"] = parseTime(row["Duration"])
            for k, v in row.items():
                row[k] = convertStrValue(v, unicodeEncoding, k not in strKeys)
            tracklist.append(row)
    return tracklist

# Changes a simple tracklist into a full one
def augmentTrackList(trackList, unicodeEncoding, **kwargs):
    # Read initial metadata
    firstRow = trackList[0]
    if len(firstRow) == 3:
        artist = convertStrValue(firstRow[0], unicodeEncoding, False)
        album = convertStrValue(firstRow[1], unicodeEncoding, False)
        year = convertStrValue(firstRow[2], unicodeEncoding)
        genre = None
    else:
        artist = convertStrValue(firstRow[0], unicodeEncoding, False)
        album = convertStrValue(firstRow[1], unicodeEncoding, False)
        year = convertStrValue(firstRow[2], unicodeEncoding)
        genre = convertStrValue(firstRow[3], unicodeEncoding, False)
    trackList = trackList[1:]

    for k, v in kwargs.items():
        kwargs[k] = convertStrValue(v, unicodeEncoding)

    # Get max track and disc numbers
    trackCounts = dict()
    maxDN = 0
    curTN = 0
    lastDN = 0
    for row in trackList:
        if len(row) == 3:
            disc = row[2]
            if disc > lastDN:
                trackCounts[lastDN] = curTN
                curTN = 0
                lastDN = disc
                maxDN = max(lastDN, maxDN)
        curTN += 1
    if maxDN or lastDN:
        trackCounts[lastDN] = curTN
    else:
        maxDN = None
        trackCounts[None] = curTN

    # Populate the table of dicts
    lastDN = 1
    curTN = 0
    augmentedTrackList = list()
    for row in trackList:
        if len(row) == 2:
            title, time = row
            disc = None
        else:
            title, time, disc = row
        time = parseTime(time) * 1000

        curTN += 1
        dc = maxDN
        if disc:
            if disc != lastDN:
                curTN = 1
                lastDN = disc

        row =  {"Title": unicode(title, unicodeEncoding),
                  "Artist": artist,
                  "AlbumArtist": artist,
                  "Album": album,
                  "Genre": genre,
                  "Year": year,
                  "Duration": time,
                  "TrackNumber": curTN,
                  "TrackCount": trackCounts[disc],
                  "Disc": disc,
                  "DiscCount": dc}

        row.update(kwargs)
        augmentedTrackList.append(row)

    return augmentedTrackList

# Get a track list from a URL or file
def getTrackList(loc, unicodeEncoding="utf-8"):
    if os.path.exists(loc):
        if loc.endswith(".csv"):
            tl = readTrackList(loc, unicodeEncoding)
        else:
            tl = readSimpleTrackList(loc)
    # elif os.path.exists(os.path.join(Config.dropboxdir, loc)):
    #    tl = readSimpleTrackList(os.path.join(Config.dropboxdir, loc))
    else:
        tl = getTrackListFromUrl(loc)

    return tl

def getAugmentedTrackList(loc, unicodeEncoding="utf-8", **kwargs):
    tl = getTrackList(loc, unicodeEncoding)
    simple = not loc.lower().endswith(".csv")
    if simple:
        tl = augmentTrackList(tl, unicodeEncoding, **kwargs)

    return tl

# Format a track list for printing
def formatTrackList(trackList, unicodeEncoding, buf=None):
    ioBuf = False
    if buf is None:
        buf = StringIO.StringIO()
        ioBuf = True
    headers = sorted(trackList[0].keys(), cmp=compareFields)
    writer = csv.DictWriter(buf, headers, lineterminator='\n')
    writer.writeheader()
    for row in trackList:
        encodedRow = dict()
        for k, v in row.items():
            if isinstance(v, unicode):
                encodedRow[k] = v.encode(unicodeEncoding)
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
    parser.add_argument('-u', "--unicodeencoding", help="Specify a unicode encoding to use.",
                                default="utf-8")
    parser.add_argument('-o', "--out", help="Output to a file.")
    parser.add_argument('-s', "--simple", action="store_true",
                help="Use the simple tracklist format.")
    args = parser.parse_args()

    tl = getTrackList(args.location, args.unicodeencoding)

    simple = not args.location.lower().endswith(".csv")
    if simple and not args.simple:
        tl = augmentTrackList(tl, args.unicodeencoding, **dict(args.extra))

        # for row in table:
        #    print row
        if args.out:
            with open(args.out, 'w') as f:
                formatTrackList(tl, args.unicodeencoding, f)
        else:
            print formatTrackList(tl, args.unicodeencoding).strip()
    else:
        if args.out:
            with open(args.out, 'w') as f:
                writer = csv.writer(f, delimiter='\t', lineterminator='\n')
                writer.writerows(tl)
        else:
            print '\n'.join(['\t'.join(map(str, l)) for l in tl])

# def readtrackrow(rowstr):
#    #FIXME: Do times need to delineated by tabs?
#    #Filter out track numbers
#    if '\t' in rowstr:
#       items = rowstr.split(None, 1)
#       if ordre.match(items[0].strip()):
#          line = items[1]
#       else:
#          line = rowstr
#       title, items = line.split('\t', 1)
#    else:
#       title = rowstr
#       items = ''
    
#    #Remove quotes from around title
    
#    items = items.split()
    
#    time = None
#    if len(items) > 0:
#       time = parseTime(items[0])
#       if not time:
#          for i in xrange(1, len(items)):
#             time = parseTime(items[i])
#             if time:
#                break
#    if len(items) == 2:
#       discNum = int(items[1])
#       return (title, time, discNum)
#    else:
#       return (title, time)

# def writeextendedtracklist(fname, flags, metadata, tracklist):
#    """The inverse of readextendedtracklist."""
#    print tracklist
#    f = open(fname, 'w')
#    s = '\t'.join(["%s%s" % (k, ','.join(map(str, v))) for k, v in flags.items()])
#    s = '%s\n%s' % (s, '\t'.join(map(str, metadata)))
#    s = '%s\n%s' % (s, '\n'.join(["%s\t%s" % (title, formattime(0, time)) for title, time in tracklist]))
#    f.write(s)
#    f.close()
#    return s

# def readextendedtracklist(fname):
#    """Read an "extended" tracklist consisting of flags on the first line,
#       metadata on the second, and then a track on each line after that. Returns
#       the flags as a dict, the metadata. and the tracklist, as a 3-tuple."""
#    f = open(fname, 'r')
#    line = f.readline().strip()
#    if line == '':
#       line = f.readline().strip()
#    flags = dict()
#    if datere.search(line):
#       metadata = line.split('\t')
#    else:
#       for s in line.split():
#          if len(s) > 1:
#             flags[s[0]] = map(int, s[1:].split(','))
#          else:
#             flags[s] = []
#       metadata = f.readline().strip().split('\t')
#    tracklist = list()
#    for line in f.readlines():
#       tracklist.append(readtrackrow(line.strip()))
#    return (flags, metadata, tracklist)