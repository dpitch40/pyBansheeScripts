import requests
import re

from bs4 import BeautifulSoup

from core.metadata import Metadata
from .util import parse_time_str

# regex for the domain name of a url
urlRe = re.compile(r"^http(?:s)?://(?:www\.)?(?:[^\.]+\.)*([^\.]+)\.com")

hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

domainParsers = dict()
def register_parser(site):
    def _inner(func):
        domainParsers[site] = func
        return func
    return _inner

@register_parser("metal-archives")
def parse_ma_tracklist(soup):
    tracks = list()

    album_info = soup.find(id="album_info")
    album = album_info.find(class_="album_name").string
    artist = album_info.find(class_="band_name").a.string
    date_str = album_info.find("dt", string="Release date:").find_next_sibling("dd").string
    year = int(date_str.rsplit(None, 1)[-1])

    song_table = soup.findAll("table", class_="table_lyrics")[0]
    disc_num = None
    for track_num, table_row in enumerate(song_table.findAll("tr")):
        if table_row.get("class", None) == ["discRow"]:
            disc_num = int(next(table_row.stripped_strings).split()[1])
        title = table_row.find("td", class_="wrapWords")
        if title is None:
            continue
        track_title = title.string.strip()
        length = parse_time_str(title.find_next_sibling("td").string)

        track = Metadata({'title': track_title,
                          'artist': artist,
                          'album': album,
                          'year': year,
                          'length': length * 1000,
                          'tn': track_num + 1,
                          'dn': disc_num})
        tracks.append(track)
    track_count = len(tracks)
    for track in tracks:
        track.tc = track_count
        track.dc = disc_num

    return tracks

@register_parser("allmusic")
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

@register_parser("bandcamp")
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

def parse_tracklist_from_url(url):
    domain = urlRe.match(url).group(1).lower()
    if domain not in domainParsers:
        raise KeyError("No parser defined for domain %r" % domain)

    result = None
    request = requests.get(url, headers=hdr)

    html = request.text
    soup = BeautifulSoup(html, "lxml")
    result = domainParsers[domain](soup)

    return result