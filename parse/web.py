import requests
import re
import os.path
from io import BytesIO
import urllib.parse

from PIL import Image
from bs4 import BeautifulSoup

from .util import parse_time_str, convert_to_tracks, parse_date_str
from core.metadata import Metadata
import config

# regex for the domain name of a url
url_re = re.compile(r"^http(?:s)?://(?:www\.)?(?:[^\.]+\.)*([^\.]+)\.(com|org|net|co\.uk)")
cd_re = re.compile(r"^CD(\d+)")
hyphen_artist_re = re.compile(r"^([^\-]+) \- (.+)$")

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

def download_album_art(url, artist, album):
    result = requests.get(url)
    art = Image.open(BytesIO(result.content))
    w, h = art.size
    min_dim, max_dim = sorted([w, h])
    if min_dim < config.MinArtSize:
        print('Skipping album art download as the art is too small')
        return

    if max_dim > config.MaxArtSize:
        w, h = w * config.MaxArtSize // max_dim, h * config.MaxArtSize // max_dim
        art = art.resize((w, h))
    dest_dir = os.path.dirname(Metadata({'album': album, 'artist': artist, 'title': 'a'})
        .calculate_fname())
    dest = os.path.join(dest_dir, 'cover.jpg')
    with open(dest, 'wb') as fobj:
        art.save(fobj, quality=85)

@register_parser("metal-archives")
def parse_ma_tracklist(soup, extra_args):
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
        track_info.append({'title': track_title, 'length': length, 'dn': disc_num})

    kwargs = {'album': album,
              'year': year,
              'artist': artist}
    kwargs.update(extra_args)
    return convert_to_tracks(track_info, **kwargs)

@register_parser("allmusic")
def parse_allmusic_tracklist(soup, extra_args):
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

            d = {'title': title, 'length': track_len}
            if has_multiple_disc:
                d['dn'] = disc_num + 1
            track_info.append(d)

    kwargs = {'album': album,
              'year': year,
              'artist': artist}
    kwargs.update(extra_args)
    return convert_to_tracks(track_info, **kwargs)

@register_parser("bandcamp")
@register_parser("silentseason")
def parse_bandcamp_tracklist(soup, extra_args):
    name_section = soup.find('div', id='name-section')
    album = next(name_section.find('h2', class_='trackTitle').stripped_strings)
    album_artist = next(name_section.find('span').stripped_strings)
    year = int(next(soup.find('div', class_='tralbum-credits').stripped_strings).split()[-1])

    track_table = soup.find('table', id='track_table')
    if track_table is None:
        track_info = [(album, None, 0, None)]
    else:
        track_info = list()
        disc_num = None
        for row in track_table.find_all('tr', class_='track_row_view'):
            # TODO: Support multiple discs
            artist = None
            title = next(row.find('span', class_='track-title').stripped_strings)
            m = hyphen_artist_re.match(title)
            if m:
                artist, title = m.groups()
            time = next(row.find('span', class_='time').stripped_strings)
            track_info.append({'title': title, 'artist': artist, 'length': time, 'dn': disc_num})

    kwargs = {'album': album,
              'year': year,
              'albumartist': album_artist}
    kwargs.update(extra_args)
    return convert_to_tracks(track_info, **kwargs)


@register_art_downloader('bandcamp')
@register_art_downloader('silentseason')
def download_bandcamp_art(soup, extra_args):
    # Bonus: download album art
    return soup.find('div', id='tralbumArt').find('a').attrs['href']

def _parse_oldstyle_discogs_tracklist(soup):
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

            try:
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
            except ValueError:
                continue
        else:
            disc_num = None

        artist_td = row.find('td', class_='tracklist_track_artists')
        if artist_td:
            strs = list(artist_td.stripped_strings)
            if artist_td.contents[0]['class'] == ['tracklist_content_multi_artist_dash']:
                del strs[0]
            artist = ' '.join(strs)
        else:
            artist = album_artist
        title_td = row.find('td', class_='tracklist_track_title')
        title = next(title_td.stripped_strings)
        try:
            time_td = row.find('td', class_='tracklist_track_duration')
            if time_td is None:
                continue
            time = next(time_td.find('span').stripped_strings)
        except StopIteration:
            time = 0
        track_info.append({'title': title, 'artist': artist, 'length': time, 'dn': disc_num})

    kwargs = {'album': album,
              'year': year,
              'albumartist': album_artist}
    kwargs.update(extra_args)
    return convert_to_tracks(track_info, **kwargs)

def _parse_newstyle_discogs_tracklist(soup, extra_args):
    # Is it deliberately obfuscated somehow?
    release_header_div = soup.find(id='release-header')
    release_header = release_header_div.find('h1')
    header_strings = list(release_header.stripped_strings)
    album_artist = header_strings[0]
    album = header_strings[-1]

    year = None
    for d in release_header_div.find_all('div'):
        s = list(d.stripped_strings)
        if s and s[0] == 'Released':
            year = parse_date_str(s[-1])
            break

    track_info = list()
    rows = soup.find(id='release-tracklist').find('tbody').find_all('tr')
    for row in rows:
        number_td = row.find(class_=re.compile(r'^trackPos'))
        title_td = row.find(class_=re.compile(r'^trackTitle'))
        duration_td = row.find(class_=re.compile(r'^duration'))
        title = list(title_td.stripped_strings)[0]
        if duration_td:
            duration = parse_time_str(duration_td.string)
        else:
            duration = 0
        track_info.append({'title': title, 'length': duration})

    kwargs = {'albumartist': album_artist,
              'year': year,
              'album': album}
    kwargs.update(extra_args)
    return convert_to_tracks(track_info, **kwargs)


@register_parser('discogs')
def parse_discogs_tracklist(soup, extra_args):
    if soup.find('div', class_='profile'):
        return _parse_oldstyle_discogs_tracklist(soup, extra_args)
    else:
        return _parse_newstyle_discogs_tracklist(soup, extra_args)

@register_parser('vgmdb')
def parse_vgmdb_tracklist(soup, extra_args):
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
            strings = list(row.stripped_strings)
            if len(strings) < 2:
                continue
            elif len(strings) == 2:
                tn, title = strings
                time = '0:00'
            else:
                tn, title, time = list(row.stripped_strings)
            disc_tracks.append((title, parse_time_str(time)))
        discs.append(disc_tracks)

    multiple = len(discs) > 1
    tracklist = list()
    for disc_num, disc_tracks in enumerate(discs):
        tracklist.extend([{'title': t, 'artist': artist, 'length': time,
                           'dn': disc_num + 1 if multiple else None}
                          for t, time in disc_tracks])

    kwargs = {'album': album,
              'year': year,
              'genre': 'Game Soundtrack',
              'albumartist': artist}
    kwargs.update(extra_args)
    return convert_to_tracks(tracklist, **kwargs)

@register_parser('vocadb')
def parse_vocadb(soup, extra_args):
    vocaloid_names = {'初音ミク': 'Hatsune Miku',
                      '巡音ルカ': 'Megurine Luka',
                      '結月ゆかり': 'Yuzuki Yukari',
                      '鏡音リン': 'Kagamine Rin',
                      '鏡音レン': 'Kagamine Len',
                      'さとうささら': 'Satou Sasara',
                      '闇音レンリ': 'Yamine Renri'}

    def multireplace(s):
        if s is None:
            return s
        for japanese, english in vocaloid_names.items():
            s = s.replace(japanese, english)
        return s

    title = soup.find('h1', class_='page-title')
    album, album_artist = list(title.stripped_strings)
    album_artist, _ = re.match(r'^(.+?)(?: feat\. .+)? \(([^\)]+)\)$', album_artist).groups()
    
    props_table = soup.find('table', class_='properties')
    props = dict()
    for row in props_table.find_all('tr'):
        field, value = row.find_all('td')
        props[field.string] = ' '.join(value.stripped_strings)
    year = parse_date_str(props['Release date'].split()[0])

    tracklist_div = soup.find('div', class_='tracklist')
    discs = tracklist_div.find_all('ul')
    if len(discs) == 1:
        disc_nums = [None]
    else:
        disc_nums = range(1, len(discs) + 1)

    track_info = list()
    for disc_num, l in zip(disc_nums, discs):
        tracks = l.find_all('li', class_='tracklist-track')
        for track in tracks:
            d = {'dn': disc_num}
            tn = int(track.find('div', class_='tracklist-trackNumber').string)
            title_div = track.find('div', class_='tracklist-trackTitle')
            strings = list(title_div.stripped_strings)
            d['title'], time = strings[:2]
            artist = multireplace(strings[-1])
            if ' feat. ' in artist:
                artist, d['performer'] = artist.split(' feat. ')
                d['grouping'] = 'Vocaloid'
            d['length'] = parse_time_str(time.strip('()'))
            d['artist'] = artist
            track_info.append(d)

    kwargs = {'album': multireplace(album),
              'year': year,
              'albumartist': multireplace(album_artist)}
    kwargs.update(extra_args)
    return convert_to_tracks(track_info, **kwargs)

@register_art_downloader('vocadb')
def download_vocadb_art(soup, extra_args):
    return soup.find('img', class_='coverPic').parent.attrs['href']

def run_parser(url, d, extra_args, domain=None):
    if domain is None:
        domain = url_re.match(url).group(1).lower()
        if domain not in d:
            raise KeyError("No parser defined for domain %r" % domain)

    result = None
    r = requests.get(url, headers=hdr)
    r.encoding = 'utf8'

    html = r.text
    soup = BeautifulSoup(html, "lxml")
    result = d[domain](soup, extra_args)

    return result

def parse_tracklist_from_url(url, extra_args, domain=None):
    return run_parser(url, parsers, extra_args, domain)

def get_art_url(url):
    try:
        art_url = run_parser(url, art_downloaders, {})
        if art_url.startswith('/'):
            parsed = urllib.parse.urlparse(url)
            art_url = urllib.parse.urljoin(f'{parsed[0]}://{parsed[1]}', art_url)
        return art_url
    except KeyError:
        return None
