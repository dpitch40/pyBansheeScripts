import requests
import re
import os.path
from io import BytesIO

from PIL import Image
from bs4 import BeautifulSoup

from .util import parse_time_str, convert_to_tracks, parse_date_str
from core.metadata import Metadata
import config

# regex for the domain name of a url
url_re = re.compile(r"^http(?:s)?://(?:www\.)?(?:[^\.]+\.)*([^\.]+)\.(com|org|net)")
cd_re = re.compile(r"^CD(\d+)")

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

art_downloaders = dict()
def register_art_downloader(site):
    def _inner(func):
        art_downloaders[site] = func
        return func
    return _inner

def _download_art(url, artist, album):
    result = requests.get(url)
    art = Image.open(BytesIO(result.content))
    w, h = art.size
    max_dim = max((w, h))
    if max_dim > config.MaxArtSize:
        w, h = w * config.MaxArtSize // max_dim, h * config.MaxArtSize // max_dim
        art = art.resize((w, h))
    dest_dir = os.path.dirname(Metadata({'album': album, 'artist': artist, 'title': 'a'})
        .calculate_fname())
    dest = os.path.join(dest_dir, 'cover.jpg')
    with open(dest, 'wb') as fobj:
        art.save(fobj)

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
        track_info.append((track_title, None, length, disc_num))

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
                track_info.append((title, None, track_len, disc_num+1))
            else:
                track_info.append((title, None, track_len, None))

    return convert_to_tracks(track_info, artist=artist, album=album, year=year)

@register_parser("bandcamp")
@register_parser("silentseason")
def parse_bandcamp_tracklist(soup):
    name_section = soup.find('div', id='name-section')
    album = next(name_section.find('h2', class_='trackTitle').stripped_strings)
    artist = next(name_section.find('span').stripped_strings)
    year = int(next(soup.find('div', class_='tralbum-credits').stripped_strings).split()[-1])

    track_table = soup.find('table', id='track_table')
    track_info = list()
    disc_num = None
    for row in track_table.find_all('tr', class_='track_row_view'):
        # TODO: Support multiple discs
        title = next(row.find('span', class_='track-title').stripped_strings)
        time = next(row.find('span', class_='time').stripped_strings)
        track_info.append((title, None, time, disc_num))

    return convert_to_tracks(track_info, artist=artist, album=album, year=year)


@register_art_downloader('bandcamp')
@register_art_downloader('silentseason')
def download_bandcamp_art(soup):
    # Bonus: download album art
    return soup.find('div', id='tralbumArt').find('a').attrs['href']

@register_parser('discogs')
def parse_discogs_tracklist(soup):
    profile = soup.find('div', class_='profile')
    itemprops = profile.find_all('spanitemprop')
    if not itemprops:
        itemprops = profile.find_all('span')
    album_span = itemprops[-1]
    album_artist = ', '.join([next(a.stripped_strings) for a in
                             profile.find('span').find_all('a')])
    m = re.search(r"( \(\d+\))$", album_artist)
    if m:
        album_artist = album_artist[:-len(m.group(1))]
    album = next(album_span.stripped_strings)
    year_str = None
    for div in profile.find_all('div', class_='head'):
        s = next(div.stripped_strings)
        if s in ("Released:", "Year:"):
            try:
                year_str = next(div.find_next_sibling('div').stripped_strings)
                break
            except StopIteration:
                pass
    year = parse_date_str(year_str)

    tl_table = soup.find('div', id='tracklist').find('table')
    track_info = list()
    for row in tl_table.find_all('tr'):
        td = row.find('td', class_='tracklist_track_pos')
        if td is not None:
            try:
                pos = next(td.stripped_strings)
            except StopIteration:
                continue

            if pos.startswith("CD"):
                disc_num = int(cd_re.match(pos).group(1))
            elif pos.startswith("DVD"):
                continue
            elif '-' in pos:
                disc_num, _ = pos.split('-')
                disc_num = int(disc_num)
            elif '.' in pos:
                disc_num, _ = pos.split('.')
                disc_num = int(disc_num)
            else:
                disc_num = None
        else:
            disc_num = None

        artist_td = row.find('td', class_='tracklist_track_artists')
        if artist_td:
            a = artist_td.find('a')
            if a:
                artist = a.string
            else:
                artist = album_artist
        else:
            artist = album_artist
        title_td = row.find('td', class_='tracklist_track_title')
        title = next(title_td.stripped_strings)
        try:
            time_td = row.find('td', class_='tracklist_track_duration').find('span')
            time = next(time_td.stripped_strings)
        except StopIteration:
            time = 0
        track_info.append((title, artist, time, disc_num))

    kwargs = {'album': album,
              'year': year}
    if not all(t[1] == album_artist for t in track_info):
        kwargs['albumartist'] = album_artist
    return convert_to_tracks(track_info, **kwargs)

@register_parser('vgmdb')
def parse_vgmdb_tracklist(soup):
    album = soup.find('span', class_='albumtitle').string

    info_table = soup.find(id='album_infobit_large')

    info = dict()
    for row in info_table.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) == 2:
            name_td, value_td = row.find_all('td')
            info[''.join(name_td.stripped_strings)] = ''.join(value_td.stripped_strings)

    year = parse_date_str(info['Release Date'])
    artist = ""
    for key in ("Composed By", "Composer", "Composer/Composer"):
        if key in info:
            artist = re.sub(r'\s*,(\S)', r', \1', info[key])

    tracklist_span = soup.find(id="tracklist").find(class_='tl')
    discs = list()
    for table in tracklist_span.find_all('table'):
        disc_tracks = list()
        for row in table.find_all('tr'):
            tn, title, time = list(row.stripped_strings)
            disc_tracks.append((title, parse_time_str(time)))
        discs.append(disc_tracks)

    multiple = len(discs) > 1
    tracklist = list()
    for disc_num, disc_tracks in enumerate(discs):
        tracklist.extend([(t, artist, time, disc_num + 1 if multiple else None)
                          for t, time in disc_tracks])

    kwargs = {'album': album,
              'year': year,
              'genre': 'Game Soundtrack'}

    return convert_to_tracks(tracklist, **kwargs)

def run_parser(url, d):
    domain = url_re.match(url).group(1).lower()
    if domain not in d:
        raise KeyError("No parser defined for domain %r" % domain)

    result = None
    r = requests.get(url, headers=hdr)
    r.encoding = 'utf8'

    html = r.text
    soup = BeautifulSoup(html, "lxml")
    result = d[domain](soup)

    return result

def parse_tracklist_from_url(url):
    return run_parser(url, parsers)

def download_album_art(url, artist, album):
    try:
        art_url = run_parser(url, art_downloaders)
    except KeyError:
        pass
    else:
        _download_art(art_url, artist, album)
