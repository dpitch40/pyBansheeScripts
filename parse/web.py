import requests
import re

from bs4 import BeautifulSoup

from .util import parse_time_str, convert_to_tracks

# regex for the domain name of a url
url_re = re.compile(r"^http(?:s)?://(?:www\.)?(?:[^\.]+\.)*([^\.]+)\.(com|org|net)")

hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

parsers = dict()
def register_parser(site):
    def _inner(func):
        parsers[site] = func
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
    track_info = list()
    disc_num = None
    for table_row in song_table.findAll("tr"):
        if table_row.get("class", None) == ["discRow"]:
            disc_num = int(next(table_row.stripped_strings).split()[1])

        title = table_row.find("td", class_="wrapWords")
        if title is None:
            continue
        track_title = title.string.strip()
        length = title.find_next_sibling("td").string
        track_info.append((track_title, length, disc_num))

    return convert_to_tracks(track_info, artist=artist, album=album, year=year)

@register_parser("allmusic")
def parse_allmusic_tracklist(soup):
    release_date_div = soup.find("div", class_="release-date")
    release_date_str = release_date_div.find("span").string
    year = int(release_date_str.rsplit(None, 1)[-1])

    artist_header = soup.find("h2", class_="album-artist")
    artist = artist_header.stripped_strings.next()
    album_header = artist_header.find_next_sibling("h1")
    album = album_header.stripped_strings.next()

    track_info = list()

    tracks = soup.find("section", class_="track-listing")
    t_bodies = list(tracks.findAll("tbody"))
    has_multiple_disc = len(t_bodies) > 1
    for disc_num, t_body in enumerate(t_bodies):
        for table_row in t_body.findAll("tr"):
            title = table_row.find("div", class_="title").stripped_strings.next()

            time_div = table_row.find("td", class_="time")
            try:
                track_len = time_div.stripped_strings.next()
            except StopIteration:
                track_len = 0

            if has_multiple_disc:
                track_info.append((title, track_len, disc_num+1))
            else:
                track_info.append((title, track_len, None))

    return convert_to_tracks(track_info, artist=artist, album=album, year=year)

@register_parser("bandcamp")
def parse_bandcamp_tracklist(soup):
    name_section = soup.find('div', id='name-section')
    album = next(name_section.find('h2', itemprop='name').stripped_strings)
    artist = next(name_section.find('span', itemprop='byArtist').stripped_strings)
    year = int(soup.find('meta', itemprop='datePublished')['content'][:4])

    track_table = soup.find('table', id='track_table')
    track_info = list()
    disc_num = None
    for row in track_table.find_all('tr'):
        # TODO: Support multiple discs
        title = next(row.find('span', itemprop='name').stripped_strings)
        time = next(row.find('span', class_='time').stripped_strings)
        track_info.append((title, time, disc_num))

    return convert_to_tracks(track_info, artist=artist, album=album, year=year)

@register_parser('discogs')
def parse_discogs_tracklist(soup):
    profile = soup.find('div', class_='profile')
    artist_span, album_span = profile.find_all('spanitemprop')
    artist = artist_span['title']
    album = next(album_span.stripped_strings)
    year = None
    for div in profile.find_all('div', class_='head'):
        if next(div.stripped_strings) == 'Released:':
            year = int(next(div.find_next_sibling('div').stripped_strings))
            break

    tl_table = soup.find('div', id='tracklist').find('table')
    track_info = list()
    for row in tl_table.find_all('tr'):
        try:
            pos = next(row.find('td', class_='tracklist_track_pos').stripped_strings)
        except StopIteration:
            continue
        if '-' in pos:
            disc_num, _ = pos.split('-')
            disc_num = int(disc_num)
        else:
            disc_num = None
        title_td = row.find('td', class_='tracklist_track_title')
        title = next(title_td.stripped_strings)
        time_td = row.find('meta', itemprop='duration').find_next_sibling('span')
        time = next(time_td.stripped_strings)
        track_info.append((title, time, disc_num))

    return convert_to_tracks(track_info, artist=artist, album=album, year=year)

def parse_tracklist_from_url(url):
    domain = url_re.match(url).group(1).lower()
    if domain not in parsers:
        raise KeyError("No parser defined for domain %r" % domain)

    result = None
    request = requests.get(url, headers=hdr)

    html = request.text
    soup = BeautifulSoup(html, "lxml")
    result = parsers[domain](soup)

    return result