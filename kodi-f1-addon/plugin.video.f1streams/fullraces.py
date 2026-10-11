"""
Fullraces.com scraper — resolves race replay video URLs from ok.ru and Dailymotion embeds.
Zero external dependencies — uses only Python builtins (urllib, html.parser, re, json).
"""

import re
import html
import json
import os
import sys
import subprocess
import gzip
import zlib
import urllib.request
from html.parser import HTMLParser

# Vendored cf-bypass lib (_lib/ in addon dir) — curl_cffi w/ Chrome TLS impersonation
# passes the Cloudflare managed challenge that urllib/cloudscraper cannot. On Kodi's
# embedded py3.8 the cp38 _cffi_backend pyd can't load (Kodi ships python3.8.dll,
# CPython pyds link python38.dll) — so exe-first is the primary path there.
_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_lib')
_cf_requests = None
if os.path.isdir(_LIB):
    if _LIB not in sys.path:
        sys.path.insert(0, _LIB)
    try:
        from curl_cffi import requests as _cf_requests
    except Exception:
        # Vendored pyd is cp38 (Kodi's embedded Python). On other interpreters
        # the abi3 curl_cffi in site-packages may still work — retry without _lib.
        sys.path.remove(_LIB)
        try:
            from curl_cffi import requests as _cf_requests
        except Exception:
            _cf_requests = None

# Native curl-impersonate exe (bin/curl-impersonate.exe, lexiforest v2.2.3): Chrome TLS
# + HTTP/2 fingerprint via subprocess — no Python DLL linking, so it works under Kodi's
# dotted-DLL python3.8.dll. Primary fetch path; curl_cffi is the dev-box fallback.
_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'curl-impersonate.exe')

_CHROME120_ARGS = [
    '--ciphers', 'TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA:AES256-SHA',
    '-H', 'sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    '-H', 'sec-ch-ua-mobile: ?0',
    '-H', 'sec-ch-ua-platform: "Windows"',
    '-H', 'Upgrade-Insecure-Requests: 1',
    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    '-H', 'Sec-Fetch-Site: none',
    '-H', 'Sec-Fetch-Mode: navigate',
    '-H', 'Sec-Fetch-User: ?1',
    '-H', 'Sec-Fetch-Dest: document',
    '-H', 'Accept-Encoding: gzip, deflate, br',
    '-H', 'Accept-Language: en-US,en;q=0.9',
    '--http2',
    '--http2-settings', '1:65536;2:0;4:6291456;6:262144',
    '--http2-window-update', '15663105',
    '--http2-stream-weight', '256',
    '--http2-stream-exclusive', '1',
    '--compressed',
]
_CURL_META = '__CURLMETA__'


def _meta_split(raw):
    """Split curl's trailing -w meta off the body; decompress if curl didn't."""
    if _CURL_META.encode() in raw:
        raw, meta = raw.rsplit(_CURL_META.encode(), 1)
    else:
        meta = b'?'
    if raw[:2] == b'\x1f\x8b':
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
    elif raw[:1] == b'\x78':
        try:
            raw = zlib.decompress(raw, 32 + 15)
        except Exception:
            pass
    return meta.decode('ascii', 'replace').strip(), raw


# Windows: hide child-process console windows. Kodi is a GUI app — spawning the
# curl-impersonate console exe without these flags flashes a conhost window on
# every menu click.
_SUB_KWARGS = {}
try:
    _SUB_KWARGS['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    try:
        _si = subprocess.STARTUPINFO()
        _si.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 0x00000001)
        _si.wShowWindow = 0  # SW_HIDE
        _SUB_KWARGS['startupinfo'] = _si
    except Exception:
        pass
except Exception:
    pass


def _exe_fetch(url, timeout=15):
    """Return (http_code, text) via curl-impersonate.exe, or (None, '') if unavailable."""
    if not os.path.isfile(_EXE):
        return None, ''
    cmd = [_EXE] + _CHROME120_ARGS + [
        '-s', '--max-time', str(timeout),
        '-w', _CURL_META + '%{http_code}',
        url,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 10, **_SUB_KWARGS)
    except Exception:
        return None, ''
    meta, raw = _meta_split(p.stdout)
    try:
        code = int(meta.split(':')[0])
    except Exception:
        code = 0
    return code, raw.decode('utf-8', errors='replace')


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
    """Fetch HTML page. Priority: curl-impersonate.exe subprocess (works under
    Kodi's py3.8 — no DLL linking) → curl_cffi Chrome-TLS impersonation (dev
    box) → urllib fallback for offline/dev stubbing."""
    code, html = _exe_fetch(url, timeout)
    if code == 200 and 'Just a moment' not in html[:800]:
        return html
    if _cf_requests is not None:
        try:
            r = _cf_requests.get(url, impersonate='chrome120', timeout=timeout)
            if r.status_code == 200 and 'Just a moment' not in r.text[:800]:
                return r.text
        except Exception:
            pass
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

    def _abs(href):
        """Site now emits relative hrefs (/race-...) — resolve to absolute."""
        return urllib.parse.urljoin(BASE_URL + '/', href)

    # Method 1: h3 > a links. URL may be relative; title may sit inside a
    # nested <a>, so capture permissively then strip tags.
    for m in re.finditer(r'<h3[^>]*>\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>', html_text, re.DOTALL):
        href, raw_title = m.group(1), m.group(2)
        title = re.sub(r'<[^>]+>', '', raw_title).strip() or \
            (href.rstrip('/').split('/')[-1].replace('-', ' ').title())
        if 'fullraces.com' not in urllib.parse.urlparse(href).netloc:
            href = _abs(href)
        if 'fullraces.com' in urllib.parse.urlparse(href).netloc and href not in seen \
                and title and len(title) > 10:
            seen.add(href)
            races.append({'title': title, 'url': href, 'thumb': ''})

    # Method 2: inf_raited blocks — img anchor carries the link+thumb, title
    # anchor lives inside inf_raited_title.
    for m in re.finditer(
        r'<div\s+class="inf_raited_img">\s*<a\s+href="([^"]+)"[^>]*>'
        r'<img\s+src="([^"]*)"[^>]*>.*?'
        r'<div\s+class="inf_raited_title"[^>]*>\s*(?:<a[^>]*>)?(.*?)(?:</a>)?\s*</div>',
        html_text, re.DOTALL
    ):
        href, thumb, raw_title = m.group(1), m.group(2), m.group(3)
        title = re.sub(r'<[^>]+>', '', raw_title).strip()
        href = _abs(href)
        if href not in seen and title:
            seen.add(href)
            races.append({'title': title, 'url': href, 'thumb': thumb if thumb.startswith('http') else urllib.parse.urljoin(BASE_URL + '/', thumb)})

    # Method 3: Simple href extraction fallback (relative or absolute)
    if not races:
        for m in re.finditer(r'href="((?:https?://fullraces\.com)?/(?:race|watch|video)[^"]*)"', html_text):
            href = _abs(m.group(1))
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
    filemoon = []

    # ok.ru — iframes AND su-buttons (protocol-relative //ok.ru/videoembed/N)
    for m in re.finditer(r'(?:iframe[^>]+src=|href=)["\'](?:https?:)?//ok\.ru/(?:videoembed|video)/(\d+)', html_text):
        if m.group(1) not in ok_ru_ids:
            ok_ru_ids.append(m.group(1))

    # Dailymotion — su-button class carries style suffixes; hrefs use
    # geo.dailymotion.com/player.html?video=ID (and plain /embed/video/ID)
    for m in re.finditer(
        r'<a[^>]*class="[^"]*su-button[^"]*"[^>]*href="[^"]*(?:dailymotion\.com[^"]*video=|dailymotion\.com/embed/video/)([a-zA-Z0-9]+)[^"]*"[^>]*>(.*?)</a>',
        html_text, re.DOTALL
    ):
        vid = m.group(1)
        label = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if not any(p['id'] == vid for p in dm_parts):
            dm_parts.append({'id': vid, 'label': label or 'Part %d' % (len(dm_parts) + 1)})

    # Fallback 1: geo.dailymotion player iframes/buttons regardless of class
    if not dm_parts:
        for m in re.finditer(r'geo\.dailymotion\.com/[a-z./]+\?video=([a-zA-Z0-9]+)', html_text):
            vid = m.group(1)
            if not any(p['id'] == vid for p in dm_parts):
                dm_parts.append({'id': vid, 'label': 'Part %d' % (len(dm_parts) + 1)})

    # Fallback 2: plain dailymotion embed urls
    if not dm_parts:
        for m in re.finditer(r'dailymotion\.com/embed/video/([a-zA-Z0-9]+)', html_text):
            vid = m.group(1)
            if not any(p['id'] == vid for p in dm_parts):
                dm_parts.append({'id': vid, 'label': 'Part %d' % (len(dm_parts) + 1)})

    # Filemoon-style hosts — capture but not playable in-Kodi (PoW gate); kept in dict
    for m in re.finditer(r'href="https?://([^/"\']+\.com|[^/"\']+\.sbs)/d/([a-z0-9]+)"', html_text):
        host, vid = m.group(1), m.group(2)
        if host not in ('fullraces.com',):
            filemoon.append({'host': host, 'id': vid})

    return {'ok_ru': ok_ru_ids, 'dailymotion': dm_parts, 'filemoon': filemoon, 'title': title}


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