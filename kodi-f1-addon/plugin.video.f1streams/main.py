"""
F1 Streams Kodi Addon v2.1.0
Zero external dependencies — uses only Python builtins.
Live streams from daddylive + race replays from fullraces.com.
"""

import sys
import re
import json
import ssl
import urllib.parse
import urllib.request
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc

# Bypass SSL cert verification issues common on Windows Kodi
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# Local scraper module
import fullraces as fr

# --- Constants ---
ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_HANDLE = int(sys.argv[1])
ADDON_URL = sys.argv[0]

# v2.5.0 — Added SportHD F1 backup streams (DAZN F1, Disney+, FOX Sports AR)
# v2.6.0 — daddy2.php now 403 (upstream daddylive change). Live streams now come
#          from SportHD (streamxhd.com) via eventos.json: all active F1 servers
#          (Disney+/FOX/DAZN) resolved dynamically. daddylive kept as directory source.
CHANNELS_API = 'https://daddylive.mov/cache/channels.json'
CHANNELS_REFERER = 'https://daddylive.mov/'

# Legacy daddylive resolution (currently 403 upstream; kept for fallback)
STREAM_PLAYER_URL = 'https://hamis.romponalis.st/premiumtv/daddy2.php?id={cid}'
STREAM_PAGE_REFERER = 'https://dlstreams.st/stream/stream-{cid}.php'
STREAM_M3U8_REFERER = 'https://hamis.romponalis.st/'

# SportHD backup streams (streamxhd.com)
SPORTHD_EVENTS_API = 'https://streamxhd.com/eventos.json'
SPORTHD_LIVE_PAGE = 'https://streamxhd.com/live1.php?stream={stream}'
SPORTHD_REFERER = 'https://streamxhd.com/'
SPORTHD_M3U8_REFERER = 'https://streamxhd.com/'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
HEADERS = {
    'User-Agent': UA,
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': CHANNELS_REFERER,
}

MOTORSPORT_KEYWORDS = [
    'grand prix', 'f1', 'formula 1', 'formula1', 'motorsport',
    'motor sports', 'gp ', 'race', 'qualifying', 'practice', 'sprint',
]

# Pre-known F1/motorsport channel IDs from daddylive.mov channels.json
# These are always available (24/7 channels), not just when races are live
MOTORSPORT_CHANNEL_IDS = [
    '60',    # Sky Sports F1 UK
    '3007',  # Sky Sports F1 (alt)
    '274',   # Sky Sports F1 DE
    '577',   # Sky Sport F1 Italy
    '537',   # DAZN F1 ES
    '273',   # Canal+ Formula 1
    '3030',  # DAZN MotoGP ES
    '575',   # Sky Sport MotoGP Italy
    '3046',  # Sky Sport MotoGP IT
    '271',   # Canal+ MotoGP France
    '554',   # Sky Sports Racing UK
    '555',   # Racing Tv UK
    '424',   # SuperSport Motorsport
    '3037',  # Fox Sports Racing
    '272',   # V Sport Motor Sweden
    '702',   # TV4 Motor
    '252',   # FloRacing
    '5018',  # FloRacing II
    '608',   # Dubai Racing 2 UAE
]


def log(msg):
    xbmc.log("[%s] %s" % (ADDON_NAME, msg), xbmc.LOGDEBUG)


def get_url(params):
    return "%s?%s" % (ADDON_URL, urllib.parse.urlencode(params))


def fetch_json(url, timeout=15):
    """Fetch JSON using urllib (no requests dependency)."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception as e:
        log("JSON fetch error: %s" % e)
        return None


def fetch_page(url, headers=None, timeout=15):
    """Fetch HTML page using urllib."""
    try:
        h = headers or EMBED_HEADERS
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log("Page fetch error: %s" % e)
        return None


# ============ LIVE STREAM FUNCTIONS ============

def get_motorsport_channels():
    """Fetch all motorsport channels from daddylive.mov channels.json"""
    data = fetch_json(CHANNELS_API)
    if not data or not isinstance(data, list):
        return []
    channels = []
    for item in data:
        cid = (item.get('id') or '').strip()
        title = (item.get('title') or '').strip()
        if not cid or not title:
            continue
        title_lower = title.lower()
        if any(kw in title_lower for kw in MOTORSPORT_KEYWORDS) or cid in MOTORSPORT_CHANNEL_IDS:
            channels.append({
                'channel_id': cid,
                'title': title,
                'league': 'Motorsport',
                'event': title,
                'stream_label': '',
                'date': '',
                'time': '',
                'iframe_url': '',  # Not used anymore
                'match_id': cid,
                'league_logo': '',
            })
    return channels


def filter_f1(matches):
    """With the new channels.json approach, all matches are already F1/motorsport."""
    return matches


def resolve_live_stream(channel_id):
    """Resolve a daddylive channel ID to an m3u8 URL via direct daddy2.php scraping.
    
    The old chat.cfbu247.sbs proxy API was returning 503. Instead we fetch
    daddy2.php directly, which contains a Clappr player with a base64-encoded
    m3u8 URL in atob('...'). The decoded URL is a direct HLS stream that
    requires a Referer header from hamis.romponalis.st.
    """
    import base64
    if not channel_id:
        return None
    try:
        player_url = STREAM_PLAYER_URL.format(cid=channel_id)
        referer = STREAM_PAGE_REFERER.format(cid=channel_id)
        req = urllib.request.Request(player_url, headers={
            'User-Agent': UA,
            'Referer': referer,
            'Accept': 'text/html,application/xhtml+xml,*/*',
        })
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        # Extract base64 from atob('...')
        match = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", html)
        if not match:
            log("No atob() found in daddy2.php for channel %s" % channel_id)
            return None
        m3u8_url = base64.b64decode(match.group(1)).decode('utf-8')
        if m3u8_url.startswith('http'):
            log("Resolved channel %s -> %s" % (channel_id, m3u8_url[:100]))
            return m3u8_url
        log("Decoded URL doesn't start with http: %s" % m3u8_url[:80])
        return None
    except Exception as e:
        log("Stream resolve error (direct): %s" % e)
        return None


def resolve_sporthd_stream(stream_name):
    """Resolve a SportHD stream (streamxhd.com) to a playable m3u8 URL.

    SportHD uses a JS obfuscation scheme: the page contains an array of
    [index, base64_string] pairs and two functions that return numbers.
    The decode: base64_decode(b64) -> extract digits -> parseInt - k,
    where k = func1() + func2(). Each result is a char code that forms
    the playback URL when joined.
    """
    import base64
    if not stream_name:
        return None
    try:
        page_url = SPORTHD_LIVE_PAGE.format(stream=stream_name)
        req = urllib.request.Request(page_url, headers={
            'User-Agent': UA,
            'Referer': SPORTHD_REFERER,
            'Accept': 'text/html,application/xhtml+xml,*/*',
        })
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
            html = resp.read().decode('utf-8', errors='replace')

        # Find inline script with the playbackURL builder
        scripts = re.findall(r'<script>(.+?)</script>', html, re.DOTALL)
        for s in scripts:
            if 'playbackURL' not in s:
                continue

            # Extract k = func1() + func2()
            k_match = re.search(r'var k=(\w+)\(\)\+(\w+)\(\)', s)
            if not k_match:
                continue
            f1_name, f2_name = k_match.group(1), k_match.group(2)
            f1_ret = re.search(r'function ' + re.escape(f1_name) + r'\(\)\{return (\d+);', s)
            f2_ret = re.search(r'function ' + re.escape(f2_name) + r'\(\)\{return (\d+);', s)
            if not f1_ret or not f2_ret:
                continue
            k = int(f1_ret.group(1)) + int(f2_ret.group(1))

            # Find the array var used in forEach that builds playbackURL
            fe_match = re.search(r'(\w+)\.forEach\(e=>\{ let v=e\[1\]; playbackURL', s)
            if not fe_match:
                fe_match = re.search(r'(\w+)\.forEach\(e=>\{let v=e\[1\]; playbackURL', s)
            if not fe_match:
                continue
            arr_var = fe_match.group(1)

            # Get the data array (the one with [[ pairs)
            arr_start = s.find(arr_var + '=[[')
            if arr_start < 0:
                continue
            bracket_count = 0
            arr_end = arr_start
            for j in range(arr_start, len(s)):
                if s[j] == '[':
                    bracket_count += 1
                elif s[j] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        arr_end = j + 2
                        break
            arr_text = s[arr_start:arr_end]
            pairs = re.findall(r'\[(\d+),"([^"]+)"\]', arr_text)
            if not pairs:
                continue

            # Sort by index and decode
            pairs_sorted = sorted(pairs, key=lambda x: int(x[0]))
            decoded_chars = []
            for _idx, b64_str in pairs_sorted:
                try:
                    decoded_b64 = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                    digits = re.sub(r'\D', '', decoded_b64)
                    if digits:
                        char_code = int(digits) - k
                        decoded_chars.append(chr(char_code))
                except Exception:
                    pass

            playback_url = ''.join(decoded_chars)
            if playback_url.startswith('http'):
                log("SportHD resolved %s -> %s" % (stream_name, playback_url[:100]))
                return playback_url
            log("SportHD decode didn't produce URL: %s" % playback_url[:80])
            return None

        log("No playbackURL script found in SportHD page for %s" % stream_name)
        return None
    except Exception as e:
        log("SportHD resolve error: %s" % e)
        return None


def get_sporthd_f1_streams():
    """Return SportHD F1 streams from the live eventos.json API.

    eventos.json lists today's events with active servers (Disney+, FOX, DAZN).
    Falls back to hardcoded channels if the API is down.
    """
    import json as _json
    known = [
        ('daznf1', 'DAZN F1 [English]'),
        ('disney1', 'Disney+ F1 [Spanish]'),
        ('fox1ar', 'FOX Sports 1 AR [Spanish]'),
    ]
    channels = []
    seen = set()
    try:
        req = urllib.request.Request(SPORTHD_EVENTS_API, headers={
            'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
            data = _json.loads(resp.read().decode('utf-8', errors='replace'))
        for ev in data:
            if ev.get('code') != 'F1':
                continue
            for sv in ev.get('servers', []):
                if not sv.get('active'):
                    continue
                slug = sv['url'].split('stream=')[-1]
                if slug in seen:
                    continue
                seen.add(slug)
                channels.append({
                    'channel_id': 'sporthd_%s' % slug,
                    'title': '%s — F1 %s' % (sv['name'], ev.get('title', '')),
                    'league': 'SportHD F1',
                    'event': sv['name'],
                    'stream_label': sv['name'],
                    'date': '', 'time': '',
                    'iframe_url': '',
                    'match_id': 'sporthd_%s' % slug,
                    'league_logo': ev.get('image', ''),
                })
    except Exception as e:
        log("SportHD eventos.json error: %s" % e)
    # Fallback: hardcoded set for anything the API missed
    for stream_name, label in known:
        if stream_name in seen:
            continue
        seen.add(stream_name)
        channels.append({
            'channel_id': 'sporthd_%s' % stream_name,
            'title': label,
            'league': 'SportHD F1',
            'event': '%s — SportHD Backup' % label,
            'stream_label': label,
            'date': '', 'time': '',
            'iframe_url': '',
            'match_id': 'sporthd_%s' % stream_name,
            'league_logo': '',
        })
    return channels


# ============ UI FUNCTIONS ============

def show_main_menu():
    items = [
        {'label': 'Live F1 / Motorsport Streams',
         'url': get_url({'action': 'f1_live'}), 'is_folder': True},
        {'label': 'F1 2026 Race Replays',
         'url': get_url({'action': 'replays', 'cat': '2026'}), 'is_folder': True},
        {'label': 'F1 2025 Race Replays',
         'url': get_url({'action': 'replays', 'cat': '2025'}), 'is_folder': True},
        {'label': 'F1 2024 Race Replays',
         'url': get_url({'action': 'replays', 'cat': 'watch/formula_1/formula_1_2024/21'}), 'is_folder': True},
        {'label': 'F1 Classic Archive',
         'url': get_url({'action': 'replays', 'cat': 'formula1-archive-races'}), 'is_folder': True},
        {'label': 'Formula 2 Replays',
         'url': get_url({'action': 'replays', 'cat': 'f2-full-races'}), 'is_folder': True},
        {'label': 'Formula 3 Replays',
         'url': get_url({'action': 'replays', 'cat': 'f3-full-races'}), 'is_folder': True},
        {'label': 'Formula E Replays',
         'url': get_url({'action': 'replays', 'cat': 'formula-e'}), 'is_folder': True},
        {'label': 'NASCAR Replays',
         'url': get_url({'action': 'replays', 'cat': 'nascar'}), 'is_folder': True},
        {'label': 'IndyCar Replays',
         'url': get_url({'action': 'replays', 'cat': 'indycar'}), 'is_folder': True},
        {'label': 'World Superbike Replays',
         'url': get_url({'action': 'replays', 'cat': 'wsbk'}), 'is_folder': True},
        {'label': 'World Rally Championship',
         'url': get_url({'action': 'replays', 'cat': 'wrc'}), 'is_folder': True},
        {'label': 'Search Replays',
         'url': get_url({'action': 'search_replays'}), 'is_folder': True},
        {'label': 'Settings',
         'url': get_url({'action': 'settings'}), 'is_folder': False},
    ]
    for item in items:
        li = xbmcgui.ListItem(label=item['label'])
        li.setArt({'icon': 'DefaultVideo.png'})
        li.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, item['url'], li, item['is_folder'])
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


from datetime import datetime, timedelta, timezone

# Adelaide is UTC+9:30 (standard) / UTC+10:30 (daylight saving, Oct-Apr)
# We compute it dynamically to handle DST correctly.
try:
    import zoneinfo
    ADELAIDE_TZ = zoneinfo.ZoneInfo('Australia/Adelaide')
except Exception:
    ADELAIDE_TZ = timezone(timedelta(hours=9, minutes=30))  # fallback: ACST


def to_adelaide(time_str):
    """Convert 'HH:MM PM' (UTC) to 'HH:MM ADL' string."""
    if not time_str:
        return ''
    try:
        # Strip 'PM'/'AM' suffix — API returns 24h format with redundant AM/PM
        t = time_str.strip().rstrip('APM').strip()
        h, m = t.split(':')[:2]
        hour, minute = int(h), int(m)
        utc_dt = datetime.now(timezone.utc).replace(
            hour=hour, minute=minute, second=0, microsecond=0)
        adl_dt = utc_dt.astimezone(ADELAIDE_TZ)
        return adl_dt.strftime('%H:%M')
    except Exception:
        return None


def show_matches(matches, content_type='videos'):
    xbmcplugin.setContent(ADDON_HANDLE, content_type)
    if not matches:
        li = xbmcgui.ListItem(label="No motorsport channels found right now.")
        li.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, '', li, False)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return

    for m in matches:
        label = m['event']
        if m.get('stream_label'):
            label += " (%s)" % m['stream_label']

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': 'DefaultVideo.png', 'thumb': m.get('league_logo', 'DefaultVideo.png')})
        plot = "Channel: %s" % m['event']
        li.setInfo('video', {'title': label, 'plot': plot, 'studio': m.get('league', 'Motorsport')})
        li.setProperty('IsPlayable', 'true')
        play_url = get_url({'action': 'play_live', 'channel_id': m['channel_id']})
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, play_url, li, False)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def show_f1_streams():
    channels = get_motorsport_channels()
    # Append SportHD backup F1 streams
    try:
        sporthd = get_sporthd_f1_streams()
        if sporthd:
            channels.extend(sporthd)
            log("Added %d SportHD F1 backup streams" % len(sporthd))
    except Exception as e:
        log("SportHD fetch error: %s" % e)
    show_matches(channels)


def search_events():
    keyboard = xbmc.Keyboard('', 'Search motorsport channels...')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText().lower().strip()
        if query:
            channels = get_motorsport_channels()
            filtered = [c for c in channels
                        if query in c['title'].lower()]
            show_matches(filtered)


def play_live_stream(channel_id):
    if not channel_id:
        xbmcgui.Dialog().notification(ADDON_NAME, "No channel ID available",
                                       xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return

    # Route SportHD streams to SportHD resolver
    if channel_id.startswith('sporthd_'):
        stream_name = channel_id[len('sporthd_'):]
        stream_url = resolve_sporthd_stream(stream_name)
        m3u8_referer = SPORTHD_M3U8_REFERER
    else:
        # Legacy daddylive flow (currently 403 upstream) — try once, fall back to SportHD DAZN
        stream_url = resolve_live_stream(channel_id)
        m3u8_referer = STREAM_M3U8_REFERER
        if not stream_url:
            log("daddylive resolve failed for %s, falling back to SportHD daznf1" % channel_id)
            stream_url = resolve_sporthd_stream('daznf1')
            m3u8_referer = SPORTHD_M3U8_REFERER

    if not stream_url:
        xbmcgui.Dialog().notification(ADDON_NAME,
                                       "Could not resolve stream. The channel may be offline.",
                                       xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return
    log("Playing live: %s" % stream_url)
    xbmcgui.Dialog().notification(ADDON_NAME, "Resolved: " + stream_url[:80],
                                   xbmcgui.NOTIFICATION_INFO, 5000)
    # Pipe syntax for HTTP headers (url|Header=Value&Header2=Value2)
    # No inputstream.adaptive — use Kodi's built-in ffmpeg player
    # (inputstream.adaptive was crashing Kodi)
    stream_headers = {'Referer': m3u8_referer, 'User-Agent': UA}
    header_url = "{}|{}".format(stream_url, urllib.parse.urlencode(stream_headers))
    li = xbmcgui.ListItem(path=header_url)
    li.setProperty("IsPlayable", "true")
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


# ============ REPLAY FUNCTIONS ============

def show_replays(cat_slug):
    xbmcplugin.setContent(ADDON_HANDLE, 'videos')
    races = fr.scrape_category(cat_slug)
    if not races:
        li = xbmcgui.ListItem(label="No replays found in this category.")
        li.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, '', li, False)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return

    for race in races:
        li = xbmcgui.ListItem(label=race['title'])
        li.setArt({'icon': 'DefaultVideo.png', 'thumb': race.get('thumb', 'DefaultVideo.png')})
        li.setInfo('video', {'title': race['title'], 'plot': race['title']})
        li.setProperty('IsPlayable', 'false')
        url = get_url({'action': 'race_parts', 'url': race['url']})
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, li, True)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def show_race_parts(race_url):
    xbmcplugin.setContent(ADDON_HANDLE, 'videos')
    info = fr.scrape_race_page(race_url)
    title = info.get('title', 'Race Replay')

    for idx, vid in enumerate(info['ok_ru']):
        label = title
        if len(info['ok_ru']) > 1:
            label += " (Video %d)" % (idx + 1)
        label += " [ok.ru]"
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': 'DefaultVideo.png'})
        li.setInfo('video', {'title': label, 'plot': "Full replay via ok.ru (direct MP4)"})
        li.setProperty('IsPlayable', 'true')
        play_url = get_url({'action': 'play_okru', 'video_id': vid, 'title': title})
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, play_url, li, False)

    for dm in info['dailymotion']:
        label = "%s - %s [Dailymotion]" % (title, dm['label'])
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': 'DefaultVideo.png'})
        li.setInfo('video', {'title': label, 'plot': "Replay part via Dailymotion (HLS stream)"})
        li.setProperty('IsPlayable', 'true')
        play_url = get_url({'action': 'play_dm', 'video_id': dm['id'], 'title': title})
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, play_url, li, False)

    if not info['ok_ru'] and not info['dailymotion']:
        li = xbmcgui.ListItem(label="No video sources found for this race.")
        li.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, '', li, False)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def play_okru(video_id, title=''):
    result = fr.resolve_okru(video_id)
    if not result:
        xbmcgui.Dialog().notification(ADDON_NAME,
                                       "Could not resolve ok.ru video. It may have been removed.",
                                       xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return
    log("Playing ok.ru [%s]: %s..." % (result['quality'], result['url'][:80]))
    li = xbmcgui.ListItem(path=result['url'])
    li.setInfo('video', {'title': title or 'F1 Replay'})
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


def play_dailymotion(video_id, title=''):
    result = fr.resolve_dailymotion(video_id)
    if not result:
        xbmcgui.Dialog().notification(ADDON_NAME,
                                       "Could not resolve Dailymotion video. It may have been removed.",
                                       xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return
    log("Playing DM HLS: %s..." % result['url'][:80])
    li = xbmcgui.ListItem(path=result['url'])
    li.setInfo('video', {'title': title or 'F1 Replay'})
    try:
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
    except Exception:
        pass
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


def search_replays():
    keyboard = xbmc.Keyboard('', 'Search replays (e.g. "Belgian GP 2026")...')
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return
    query = keyboard.getText().lower().strip()
    if not query:
        return

    xbmcplugin.setContent(ADDON_HANDLE, 'videos')
    xbmcgui.Dialog().notification(ADDON_NAME, "Searching all categories...",
                                   xbmcgui.NOTIFICATION_INFO, 2000)

    search_cats = ['2026', '2025', 'watch/formula_1/formula_1_2024/21',
                   'f2-full-races', 'f3-full-races', 'nascar', 'indycar', 'formula-e']
    seen = set()
    for cat in search_cats:
        races = fr.scrape_category(cat)
        for race in races:
            if query in race['title'].lower() and race['url'] not in seen:
                seen.add(race['url'])
                li = xbmcgui.ListItem(label=race['title'])
                li.setArt({'icon': 'DefaultVideo.png', 'thumb': race.get('thumb', '')})
                li.setProperty('IsPlayable', 'false')
                url = get_url({'action': 'race_parts', 'url': race['url']})
                xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, li, True)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


# ============ ROUTER ============

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    action = params.get('action', '')

    if action == 'f1_live':
        show_f1_streams()
    elif action == 'play_live':
        play_live_stream(params.get('channel_id', ''))
    elif action == 'replays':
        show_replays(params.get('cat', '2026'))
    elif action == 'race_parts':
        show_race_parts(params.get('url', ''))
    elif action == 'play_okru':
        play_okru(params.get('video_id', ''), params.get('title', ''))
    elif action == 'play_dm':
        play_dailymotion(params.get('video_id', ''), params.get('title', ''))
    elif action == 'search_replays':
        search_replays()
    elif action == 'settings':
        ADDON.openSettings()
    else:
        show_main_menu()


if __name__ == '__main__':
    paramstring = sys.argv[2][1:] if len(sys.argv) > 2 else ''
    router(paramstring)