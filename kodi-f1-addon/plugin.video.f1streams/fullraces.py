"""
Fullraces.com scraper — resolves race replay video URLs from ok.ru and Dailymotion embeds.
Zero external dependencies — uses only Python builtins (urllib, html.parser, re, json).
"""

import re
import html
import json
import urllib.request
from html.parser import HTMLParser

BASE_URL = 'https://fullraces.com'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

CATEGORIES = [
    {'slug': '2026', 'label': 'Formula 1 2026'},
    {'slug': '2025', 'label': 'Formula 1 2025'},
    {'slug': 'watch/formula_1/formula_1_2024/21', 'label': 'Formula 1 2024'},
    {'slug': 'formula1-2023', 'label': 'Formula 1 2023'},
    {'slug': 'formula1-archive-races', 'label': 'F1 Classic Archive'},
    {'slug': 'f2-full-races', 'label': 'Formula 2'},
    {'slug': 'f3-full-races', 'label': 'Formula 3'},
    {'slug': 'formula-e', 'label': 'Formula E'},
    {'slug': 'nascar', 'label': 'NASCAR'},
    {'slug': 'indycar', 'label': 'IndyCar'},
    {'slug': 'wsbk', 'label': 'World Superbike'},
    {'slug': 'wrc', 'label': 'World Rally Championship'},
]


def fetch_page(url, timeout=15):
    """Fetch HTML page using urllib (no requests dependency)."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception:
        return None


def fetch_json(url, timeout=15):
    """Fetch JSON using urllib."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception:
        return None


class RaceListParser(HTMLParser):
    """Parse fullraces.com category page for race entries."""

    def __init__(self):
        super().__init__()
        self.races = []
        self.seen = set()
        self._in_h3 = False
        self._in_title_div = False
        self._current_href = None
        self._current_title = None
        self._current_thumb = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'h3':
            self._in_h3 = True
        elif tag == 'div' and attrs_dict.get('class', '') == 'inf_raited':
            self._in_title_div = True
        elif tag == 'a' and attrs_dict.get('href', '').startswith(BASE_URL):
            self._current_href = attrs_dict.get('href', '')
        elif tag == 'img' and self._current_href:
            self._current_thumb = attrs_dict.get('src', '')

    def handle_endtag(self, tag):
        if tag == 'h3' and self._in_h3:
            self._in_h3 = False
        elif tag == 'div' and self._in_title_div:
            self._in_title_div = False
        elif tag == 'a' and self._current_href and self._current_title:
            if self._current_href not in self.seen and len(self._current_title) > 10:
                self.seen.add(self._current_href)
                self.races.append({
                    'title': self._current_title,
                    'url': self._current_href,
                    'thumb': self._current_thumb or ''
                })
            self._current_href = None
            self._current_title = None
            self._current_thumb = None

    def handle_data(self, data):
        text = data.strip()
        if text and self._current_href and not self._current_title:
            self._current_title = text


def scrape_category(slug, page=1):
    """Fetch a category page and return a list of race entries."""
    if page > 1:
        url = "%s/%s?page%d" % (BASE_URL, slug, page)
    else:
        url = "%s/%s" % (BASE_URL, slug)

    html_text = fetch_page(url)
    if not html_text:
        return []

    races = []
    seen = set()

    # Method 1: Regex for h3 > a links (fast, no parser overhead)
    for m in re.finditer(r'<h3[^>]*>\s*<a\s+href="(https?://[^"]*fullraces\.com[^"]*)"[^>]*>([^<]+)</a>', html_text):
        href = m.group(1)
        title = m.group(2).strip()
        if href not in seen and title and len(title) > 10:
            seen.add(href)
            races.append({'title': title, 'url': href, 'thumb': ''})

    # Method 2: inf_raited blocks with thumbnails
    for m in re.finditer(
        r'<div\s+class="inf_raited"[^>]*>.*?<a\s+href="(https?://[^"]*fullraces\.com[^"]*)"[^>]*>'
        r'.*?<img\s+src="([^"]*)"[^>]*>.*?'
        r'<div\s+class="inf_raited_title"[^>]*>([^<]+)</div>',
        html_text, re.DOTALL
    ):
        href = m.group(1)
        thumb = m.group(2)
        title = m.group(3).strip()
        if href not in seen and title:
            seen.add(href)
            races.append({'title': title, 'url': href, 'thumb': thumb})

    # Method 3: Simple href extraction fallback
    if not races:
        for m in re.finditer(r'href="(https?://fullraces\.com/[^"]*(?:race|watch|video)[^"]*)"', html_text):
            href = m.group(1)
            if href not in seen:
                seen.add(href)
                races.append({'title': href.split('/')[-1].replace('-', ' ').title(), 'url': href, 'thumb': ''})

    return races


def scrape_race_page(url):
    """Parse a race page and extract video sources."""
    html_text = fetch_page(url)
    if not html_text:
        return {'ok_ru': [], 'dailymotion': [], 'title': ''}

    # Extract title
    title = ''
    m = re.search(r'<h1[^>]*class="h_title"[^>]*>([^<]+)</h1>', html_text)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r'<title>([^<]+)</title>', html_text)
        if m:
            title = m.group(1).strip()

    ok_ru_ids = []
    dm_parts = []

    # Extract ok.ru iframe embeds
    for m in re.finditer(r'<iframe[^>]+src="[^"]*ok\.ru/videoembed/(\d+)', html_text):
        ok_ru_ids.append(m.group(1))
    if not ok_ru_ids:
        for m in re.finditer(r'<iframe[^>]+src="[^"]*ok\.ru/video/(\d+)', html_text):
            ok_ru_ids.append(m.group(1))

    # Extract Dailymotion Part buttons
    for m in re.finditer(
        r'<a[^>]*class="su-button"[^>]*href="[^"]*dailymotion\.com[^"]*video=([a-zA-Z0-9]+)[^"]*"[^>]*>([^<]+)</a>',
        html_text
    ):
        dm_parts.append({'id': m.group(1), 'label': m.group(2).strip()})

    # Fallback: any dailymotion links
    if not dm_parts:
        for m in re.finditer(r'dailymotion\.com/embed/video/([a-zA-Z0-9]+)', html_text):
            dm_parts.append({'id': m.group(1), 'label': 'Part %d' % (len(dm_parts) + 1)})

    return {'ok_ru': ok_ru_ids, 'dailymotion': dm_parts, 'title': title}


def resolve_okru(video_id):
    """Resolve an ok.ru video ID to a direct MP4 URL."""
    url = "https://ok.ru/video/%s" % video_id
    html_text = fetch_page(url)
    if not html_text:
        return None

    m = re.search(r'data-options="([^"]+)"', html_text)
    if not m:
        return None

    try:
        data = json.loads(html.unescape(m.group(1)))
        flashvars = data.get('flashvars', {})
        metadata = flashvars.get('metadata', '')
        if metadata:
            md = json.loads(metadata) if isinstance(metadata, str) else metadata
            videos = md.get('videos', [])
            # Pick highest quality
            priority = ['full', 'hd', 'sd', 'low', 'lowest', 'mobile']
            for qual in priority:
                for v in videos:
                    if v.get('name') == qual and v.get('url'):
                        return {'url': v['url'], 'quality': qual, 'type': 'mp4'}
            if videos:
                return {'url': videos[0].get('url', ''), 'quality': videos[0].get('name', '?'), 'type': 'mp4'}
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return None


def resolve_dailymotion(video_id):
    """Resolve a Dailymotion video ID to an HLS m3u8 URL."""
    api_url = "https://www.dailymotion.com/player/metadata/video/%s" % video_id
    try:
        req = urllib.request.Request(api_url, headers={
            **HEADERS,
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='replace'))
        qualities = data.get('qualities', {})
        auto = qualities.get('auto', [])
        if auto and auto[0].get('url'):
            return {'url': auto[0]['url'], 'type': 'hls'}
    except Exception:
        pass
    return None