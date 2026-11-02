#!/usr/bin/env python3
"""fullraces_android.py — replays for the Android flavor (v2.8.14, 2026-11-02).

WHY THIS EXISTS
    fullraces.com (the replay catalog) sits behind Cloudflare and 403s any
    stdlib client, while the PC flavor bypasses it with the bundled
    curl-impersonate.exe. Android has no exe, no curl_cffi under Kodi's
    python3.8 — but the *playback* half of the chain is pure stdlib and was
    verified 2026-11-02 end-to-end from this repo:
        ok.ru video page  -> stdlib 200 (truncated mid-stream at ~1.0-1.1 MB,
                            harmless — data-options JSON is inside the first
                            chunk; tolerant read required, see _robust_get)
        data-options      -> flashvars.metadata -> videos[] (mobile..full)
        direct MP4        -> 206 Partial Content, ftypisom magic, Kodi/ffmpeg
                            UAs all accepted, no referer needed
    Only the CATALOG scrape is PC-only. Fix: publish the catalog as static
    JSON in the GitHub repo (raw.githubusercontent — the feed this repo's
    law already designates primary) and fill it hourly-ish on the PC side
    (PC can scrape fullraces with the exe). Android fetches the catalog via
    stdlib, then serves the exact same race→parts→okru flow as PC.

INTERFACE CONTRACT (kept identical to fullraces.PC for main.py):
    resolve_okru(video_id)    -> {'url','quality','type'} | None
    scrape_race_page(url)     -> {'title','ok_ru':[ids],'filemoon':[...]}
                                 (Dailymotion stripped 2026-11-02)
    scrape_category(slug)     -> [ {'title','url','thumb'} ]
    fetch_page(url)           -> text | None   (only used for ok.ru pages)
    PC_REPLAYS stays False in the Android main.py — the menu block that used
    to be behind it is what this module re-opens by hand in main.py's Android
    replays section (see sync-flavors.py MAIN_PATCH).
"""
import json
import re
import ssl
import http.client
import urllib.parse
import urllib.request

BASE_URL = 'https://fullraces.com'

# raw.githubusercontent catalog (primary feed per repo law; jsDelivr is
# the mirror, NOT the source of truth)
CATALOG_URL = ('https://raw.githubusercontent.com/joshaussieguy-spec/Kodi/'
               'main/kodi-f1-addon/replay-catalog.json')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
HEADERS = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def _robust_get(url, maxbytes=2_400_000):
    """stdlib GET tolerant of mid-stream truncation (ok.ru is verified to
    reset connections after ~1.0-1.1 MB; the data-options JSON we need sits
    well inside the first MB — 2026-11-02 ground truth)."""
    p = url.split('/', 3)
    host, path = p[2], '/' + (p[3] if len(p) > 3 else '')
    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(host, timeout=30, context=ctx)
    try:
        conn.request('GET', path, headers=dict(HEADERS,
                                               AcceptEncoding='identity',
                                               Connection='close'))
        resp = conn.getresponse()
        chunks, total = [], 0
        while total < maxbytes:
            try:
                c = resp.read(65536)
            except Exception:
                break  # mid-stream reset: keep what we have
            if not c:
                break
            chunks.append(c)
            total += len(c)
        return resp.status, b''.join(chunks)
    finally:
        conn.close()


def fetch_page(url, timeout=15):
    """ok.ru video pages (and anything else) via tolerant stdlib path.
    Mirrors fullraces.fetch_page's signature; never reaches fullraces.com."""
    try:
        code, body = _robust_get(url)
        if code == 200 and body:
            return body.decode('utf-8', errors='replace')
    except Exception:
        pass
    return None


# ========================================================= ok.ru resolver
# (identical logic to fullraces.resolve_okru — kept here so the Android
# flavor has no PC-only imports; verified byte-equal behaviour 2026-11-02)

def resolve_okru(video_id):
    """Resolve an ok.ru video ID to a direct MP4 URL (stdlib-safe)."""
    url = 'https://ok.ru/video/%s' % video_id
    html_text = fetch_page(url)
    if not html_text:
        return None

    m = re.search(r'data-options="([^"]+)"', html_text)
    if not m:
        return None

    try:
        data = json.loads(_html_unescape(m.group(1)))
        flashvars = data.get('flashvars', {})
        metadata = flashvars.get('metadata', '')
        md = json.loads(metadata) if isinstance(metadata, str) else metadata
        videos = md.get('videos', [])
        priority = ['full', 'hd', 'sd', 'low', 'lowest', 'mobile']
        for qual in priority:
            for v in videos:
                if v.get('name') == qual and v.get('url'):
                    return {'url': v['url'], 'quality': qual, 'type': 'mp4'}
        if videos:
            return {'url': videos[0].get('url', ''),
                    'quality': videos[0].get('name', '?'), 'type': 'mp4'}
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


def _html_unescape(s):
    import html as _h
    return _h.unescape(s)


# ========================================================= catalog

class _Catalog:
    """Static race catalog fetched from raw.githubusercontent with a
    filesystem cache so menus stay instant and offline-tolerant."""

    def __init__(self):
        self._data = None

    def load(self, fresh=False):
        if self._data is not None and not fresh:
            return self._data
        # 1. cache
        cache = None
        try:
            import xbmcaddon
            import xbmcvfs
            cache = xbmcvfs.translatePath(
                xbmcaddon.Addon().getAddonInfo('profile'))
            cache = os.path.join(cache, 'replay-catalog.json')
        except Exception:
            cache = None
        if cache and not fresh and os.path.isfile(cache):
            try:
                with open(cache, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                return self._data
            except Exception:
                self._data = None
        # 2. network
        try:
            req = urllib.request.Request(CATALOG_URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                self._data = json.loads(resp.read().decode('utf-8'))
            if cache:
                try:
                    os.makedirs(os.path.dirname(cache), exist_ok=True)
                    with open(cache, 'w', encoding='utf-8') as f:
                        json.dump(self._data, f)
                except Exception:
                    pass
        except Exception:
            self._data = self._data or {'races': []}
        return self._data

    def races(self, cat='2026'):
        """Catalog shape (v1, 2026-11-02): entries have title/url/thumb but no
        cats[] field — the seed catalog only covers '2026'. Filter: an entry
        with explicit cats[] must contain cat; an entry WITHOUT cats[] is
        treated as F1-full-races and matched by title year tag ('F1 2026'),
        falling through to the default bucket only when cat=='2026'."""
        data = self.load()
        out = []
        for r in data.get('races', []):
            cats = r.get('cats')
            if cats is not None:
                if cat in cats:
                    out.append({'title': r['title'], 'url': r['url'],
                                'thumb': r.get('thumb', '')})
                continue
            # no cats[]: default bucket = F1 current season
            m = re.search(r'F1 (20\d\d)', r['title'])
            if (m and m.group(1) == cat) or (not m and cat == '2026'):
                out.append({'title': r['title'], 'url': r['url'],
                            'thumb': r.get('thumb', '')})
        return out


_catalog = _Catalog()


def scrape_category(slug, page=1):
    """Android: catalog-backed listing (page param accepted & ignored)."""
    return _catalog.races(slug)


# --- category visibility (v2.8.15) -------------------------------------
# The shared main.py renders 12 static category folders (site slugs). The
# seed catalog only carries cats: ['2026'], so on Android 11 of 12 folders
# would open as "No replays found". Expose which categories actually have
# entries so main.py can hide the empty ones (PC/live mode ignores this
# and keeps the static list).

_CATALOG_CAT_LABELS = {
    '2026': 'F1 2026 Race Replays',
    '2025': 'F1 2025 Race Replays',
    'watch/formula_1/formula_1_2024/21': 'F1 2024 Race Replays',
    'formula1-2022': 'F1 Classic Archive (2022)',
    'f2-full-races': 'Formula 2 Replays',
    'f3-full-races': 'Formula 3 Replays',
    'formula-e': 'Formula E Replays',
    'nascar': 'NASCAR Replays',
    'indycar': 'IndyCar Replays',
    'wsbk': 'World Superbike Replays',
    'wrc': 'World Rally Championship',
}


def available_cats():
    """Return [(slug, label)] for categories that currently have races."""
    data = _catalog.load()
    out = []
    for slug, label in _CATALOG_CAT_LABELS.items():
        if _catalog.races(slug):
            out.append((slug, label))
    return out


def scrape_race_page(race_url):
    """Race detail. Two tiers:
    1. If the catalog entry carries ok_ru ids directly (catalog v2), use them.
    2. Otherwise scrape the fullraces race page itself — stdlib is 403'd by
       fullraces.com, so this tier only succeeds when the race page is
       cached by a CDN-friendly mirror; in practice tier 1 is the path.
    Kept signature-compatible with fullraces.scrape_race_page."""
    entry = _catalog.entry_for_url(race_url)
    if entry and entry.get('ok_ru'):
        return {'title': entry.get('title', 'Race Replay'),
                'ok_ru': entry['ok_ru'],
                'filemoon': []}

    # Tier 2: try stdlib anyway — some hosts whitelisted (e.g. via CDN edge)?
    # Same parsers as the PC module, duplicated to stay import-free.
    html_text = None
    try:
        req = urllib.request.Request(race_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_text = resp.read().decode('utf-8', errors='replace')
    except Exception:
        html_text = None
    if not html_text:
        return {'title': 'Race Replay', 'ok_ru': [], 'filemoon': []}
    return _parse_race_html(html_text)


def _parse_race_html(html_text):
    ok_ids = []
    for m in re.finditer(r'ok\.ru/video/(\d+)', html_text):
        if m.group(1) not in ok_ids:
            ok_ids.append(m.group(1))
    title_m = re.search(r'<title>([^<]+)</title>', html_text)
    title = title_m.group(1).strip() if title_m else 'Race Replay'
    return {'title': title, 'ok_ru': ok_ids, 'filemoon': []}


# attach entry lookup
def _entry_for_url(self, race_url):
    data = self.load()
    for r in data.get('races', []):
        if r.get('url') == race_url:
            return r
    return None


_Catalog.entry_for_url = _entry_for_url