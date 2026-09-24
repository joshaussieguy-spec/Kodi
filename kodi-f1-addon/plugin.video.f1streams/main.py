"""
F1 Streams Kodi Addon v2.7.1
Zero external dependencies — uses only Python builtins.
Live streams from dlive.sx + race replays from fullraces.com.
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
# v2.6.0 — daddy2.php now 403 (upstream daddylive change). SportHD fallback added.
# v2.7.0 — daddylive.mov channels.json DEAD, streamxhd.com SportHD DEAD. New primary:
#          dlive.sx (current DaddyLive). 24/7 channels at /watch.php?id=N.
#          Only 2 channels kept (Josh's lineup): 60 Sky Sports F1 UK (English),
#          537 DAZN F1 ES (Spanish). Resolver chain: watch.php -> iframe ->
#          window._econfig blob -> decode -> stream_url_nop2p m3u8.
CHANNELS = [
    {'id': '60',  'title': 'Sky Sports F1 UK [English]'},
    {'id': '537', 'title': 'DAZN F1 ES [Spanish]'},
]

DLIVE_BASE = 'https://dlive.sx'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def log(msg):
    xbmc.log("[%s] %s" % (ADDON_NAME, msg), xbmc.LOGDEBUG)


def get_url(params):
    return "%s?%s" % (ADDON_URL, urllib.parse.urlencode(params))


def fetch_page(url, headers=None, timeout=20):
    """Fetch HTML page using urllib."""
    try:
        h = headers or {'User-Agent': UA, 'Referer': DLIVE_BASE + '/',
                        'Accept': 'text/html,application/xhtml+xml,*/*'}
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log("Page fetch error: %s" % e)
        return None


# ============ LIVE STREAM FUNCTIONS ============

def get_live_channels():
    """Static 2-channel lineup (v2.7.0): Sky F1 UK first, DAZN F1 ES second."""
    return [{
        'channel_id': ch['id'],
        'title': ch['title'],
        'league': 'F1 Live',
        'event': ch['title'],
        'stream_label': '',
        'date': '',
        'time': '',
        'iframe_url': '',
        'match_id': ch['id'],
        'league_logo': '',
    } for ch in CHANNELS]


def filter_f1(matches):
    """Lineup is fixed; nothing to filter."""
    return matches


def _decode_econfig(blob):
    """Decode assetrage.net window._econfig blob -> JSON config string.

    Chain (reverse-engineered from stream.js 0.0.26 _0x1b7ade):
      1. base64-decode blob -> string s
      2. split s into ceil(len/4)-sized quarters
      3. strip the char at index 3 from each quarter
      4. base64-decode each quarter (they were separately encoded)
      5. slot assignment: quarter i goes to slot order[i] where order=[2,0,3,1]
      6. concat slots in slot order 0..3, base64-decode the join -> JSON
    """
    import base64
    import math
    s = base64.b64decode(blob).decode('latin-1')
    quarter = int(math.ceil(len(s) / 4.0))
    pieces = []
    pos = 0
    for _ in range(4):
        chunk = s[pos:pos + quarter]
        pos += quarter
        pieces.append(chunk[:3] + chunk[4:])
    order = [2, 0, 3, 1]
    slots = [None] * 4
    for i in range(4):
        slots[order[i]] = base64.b64decode(pieces[i] + '===').decode('latin-1')
    return base64.b64decode(''.join(slots) + '===').decode('utf-8', errors='replace')


def resolve_live_stream(channel_id):
    """Resolve a dlive.sx 24/7 channel id (e.g. '60') to a playable m3u8 URL.

    Chain: /watch.php?id=N -> page embeds /stream/stream-N.php in an iframe
    -> that page embeds the player iframe -> window._econfig blob ->
    _decode_econfig -> JSON with stream_url_nop2p (direct HLS, no p2p).
    """
    if not channel_id:
        return None
    try:
        # Step 1: watch.php page -> stream page iframe
        watch_url = DLIVE_BASE + '/watch.php?id=' + channel_id
        watch_html = fetch_page(watch_url)
        if not watch_html:
            log("watch.php fetch failed for %s" % channel_id)
            return None
        iframe_m = re.search(r'<iframe[^>]+src="(https?://[^"]*stream-\d+\.php[^"]*)"', watch_html)
        if not iframe_m:
            log("No stream iframe in watch.php for %s" % channel_id)
            return None
        stream_page_url = iframe_m.group(1)

        # Step 2: stream page -> player iframe
        page_html = fetch_page(stream_page_url)
        if not page_html:
            log("stream page fetch failed for %s" % channel_id)
            return None
        iframe_m = re.search(r'<iframe src="([^"]+)"', page_html)
        if not iframe_m:
            log("No iframe in stream page for %s" % channel_id)
            return None

        # Step 3: iframe -> _econfig blob
        iframe_html = fetch_page(iframe_m.group(1))
        if not iframe_html:
            log("iframe fetch failed for %s" % channel_id)
            return None
        blob_m = re.search(r"window\._econfig='([^']+)'", iframe_html)
        if not blob_m:
            log("No _econfig in iframe for %s" % channel_id)
            return None

        # Step 4: decode -> JSON -> m3u8
        cfg = json.loads(_decode_econfig(blob_m.group(1)))
        stream_url = cfg.get('stream_url_nop2p') or cfg.get('stream_url')
        if stream_url and stream_url.startswith('http'):
            log("Resolved channel %s -> %s" % (channel_id, stream_url[:100]))
            return stream_url
        log("No stream_url in config for %s: keys=%s" % (channel_id, list(cfg.keys())))
        return None
    except Exception as e:
        log("Stream resolve error (dlive.sx): %s" % e)
        return None


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
    channels = get_live_channels()
    show_matches(channels)


def search_events():
    keyboard = xbmc.Keyboard('', 'Search channels...')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText().lower().strip()
        if query:
            channels = get_live_channels()
            filtered = [c for c in channels
                        if query in c['title'].lower()]
            show_matches(filtered)


def play_live_stream(channel_id):
    if not channel_id:
        xbmcgui.Dialog().notification(ADDON_NAME, "No channel ID available",
                                       xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return

    # dlive.sx resolver (v2.7.0) — Referer must be the dlive.sx stream page
    stream_url = resolve_live_stream(channel_id)
    m3u8_referer = DLIVE_BASE + '/'

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