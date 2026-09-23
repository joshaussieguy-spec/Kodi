"""
AFL Streams — Kodi add-on for live Australian Football League matches via daddylive.
v1.0.0 — Zero external dependencies (urllib + re only).

Architecture:
  1. Scrape dlhd.st main page for AFL schedule entries
  2. Parse schedule: event title, time (UTC), channels (watch.php?id=XX)
  3. On play: follow watch.php → stream-XX.php → daddy.php?id=XX
  4. Extract base64-encoded m3u8 URL from Clappr player JS
  5. Resolve with Referer header required by CDN
  6. setResolvedUrl to hand m3u8 to Kodi's player

No external Python deps. All HTTP via urllib.request, parsing via regex.
"""

import sys
import os
import re
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon

# Adelaide TZ (UTC+9:30 winter, UTC+10:30 summer DST)
try:
    import zoneinfo
    ADELAIDE_TZ = zoneinfo.ZoneInfo('Australia/Adelaide')
except Exception:
    ADELAIDE_TZ = timezone(timedelta(hours=9, minutes=30))


ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_HANDLE = int(sys.argv[1])
ADDON_URL = sys.argv[0]

BASE_URL = 'https://dlhd.st'


def log(msg):
    xbmc.log(f"[AFL Streams] {msg}", xbmc.LOGDEBUG)


def get_url(params):
    """Build plugin URL with query params."""
    return f"{ADDON_URL}?{urllib.parse.urlencode(params)}"


def to_adelaide(time_str):
    """Convert 'HH:MM' (UTC) to 'HH:MM' Adelaide time."""
    if not time_str:
        return ''
    try:
        h, m = time_str.strip().split(':')[:2]
        hour, minute = int(h), int(m)
        utc_dt = datetime.now(timezone.utc).replace(
            hour=hour, minute=minute, second=0, microsecond=0)
        adl_dt = utc_dt.astimezone(ADELAIDE_TZ)
        return adl_dt.strftime('%H:%M')
    except Exception:
        return None


def fetch_url(url, referer=None, timeout=15):
    """Fetch URL with optional Referer header."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', errors='ignore')


def scrape_schedule():
    """
    Scrape dlhd.st main page for AFL / Aussie Rules matches.

    Returns list of dicts:
      {event, time (UTC 'HH:MM'), date, channels: [(channel_name, watch_id), ...]}
    """
    html = fetch_url(BASE_URL)

    # Schedule entries are in divs with data-title containing "afl" (lowercase)
    # Pattern: <div class="schedule__eventHeader" ... data-title="... afl : TEAM1 vs TEAM2 HH:MM">
    #   <span class="schedule__time" data-time="HH:MM">HH:MM</span>
    #   <span class="schedule__eventTitle">🏉 AFL : Team1 vs Team2</span>
    #   ...
    #   <div class="schedule__channels">
    #     <a href="/watch.php?id=XX" title="Channel Name">Channel Name</a>
    #   </div>

    # Find all AFL schedule blocks
    # Each event block: from schedule__eventHeader with data-title containing afl
    # to the next schedule__eventHeader or end

    # Regex to find AFL event blocks
    pattern = re.compile(
        r'data-title="[^"]*afl[^"]*"\s*>.*?<span class="schedule__time"[^>]*>(\d{2}:\d{2})</span>'
        r'.*?<span class="schedule__eventTitle">([^<]+)</span>'
        r'.*?<div class="schedule__channels">(.*?)</div>',
        re.DOTALL | re.IGNORECASE
    )

    matches = []
    for m in pattern.finditer(html):
        time_utc = m.group(1).strip()
        event_title = m.group(2).strip()
        # Clean up emoji and flags from title
        event_title = re.sub(r'[🏉🇦🇺]', '', event_title).strip()
        event_title = re.sub(r'\s+', ' ', event_title)

        # Parse channels from the channels block
        channels_block = m.group(3)
        channel_pattern = re.compile(
            r'href="(/watch\.php\?id=(\d+))"\s+title="([^"]+)"'
        )
        channels = []
        for cm in channel_pattern.finditer(channels_block):
            channels.append((cm.group(3).strip(), cm.group(2)))

        if channels:
            matches.append({
                'event': event_title,
                'time': time_utc,
                'channels': channels
            })

    return matches


def resolve_stream(watch_id):
    """
    Follow the 3-hop chain to get the m3u8 URL:
      1. /watch.php?id=XX → finds iframe src /stream/stream-XX.php
      2. /stream/stream-XX.php → finds iframe src to daddy.php
      3. daddy.php → base64-encoded m3u8 URL in Clappr player JS

    Returns (m3u8_url, daddy_url) tuple or (None, None).
    The daddy_url is needed as Referer for the CDN.
    """
    try:
        # Hop 1: watch.php
        url1 = f"{BASE_URL}/watch.php?id={watch_id}"
        html1 = fetch_url(url1, referer=BASE_URL)
        # Extract stream-XX.php URL
        stream_match = re.search(r'<iframe[^>]+src="([^"]*stream-\d+\.php[^"]*)"', html1)
        if not stream_match:
            log(f"No stream iframe found in watch.php?id={watch_id}")
            return None, None
        stream_url = stream_match.group(1)
        if stream_url.startswith('/'):
            stream_url = BASE_URL + stream_url

        # Hop 2: stream-XX.php
        html2 = fetch_url(stream_url, referer=url1)
        # Extract daddy*.php iframe URL (daddy.php, daddy3.php, daddy4.php, daddy5.php, etc.)
        daddy_match = re.search(r'<iframe[^>]+src="([^"]+daddy\w*\.php[^"]*)"', html2)
        if not daddy_match:
            log(f"No daddy.php iframe found in {stream_url}")
            return None, None
        daddy_url = daddy_match.group(1)

        # Hop 3: daddy.php — extract base64 m3u8
        html3 = fetch_url(daddy_url, referer=stream_url)

        # Look for window.atob('...') in Clappr player source
        b64_match = re.search(r"window\.atob\('([^']+)'\)", html3)
        if not b64_match:
            # Try alternative: source:'...' with base64
            b64_match = re.search(r"source:\s*window\.atob\('([^']+)'\)", html3)
        if not b64_match:
            log(f"No base64 m3u8 found in {daddy_url}")
            return None, None

        b64_str = b64_match.group(1)
        m3u8_url = base64.b64decode(b64_str).decode('utf-8').strip()
        if not m3u8_url.startswith('http'):
            log(f"Decoded URL is not valid: {m3u8_url[:100]}")
            return None, None

        return m3u8_url, daddy_url

    except Exception as e:
        log(f"resolve_stream error: {e}")
        return None, None


def build_url_with_referer(m3u8_url, referer):
    """Kodi needs the Referer header. Use the |Referer= syntax in the URL."""
    # Kodi's inputstream accepts headers via URL suffix:
    # http://stream.m3u8|Referer=https://example.com
    return f"{m3u8_url}|Referer={urllib.parse.quote(referer)}"


# Matt Huisman i.mjh.nz — Australian free-to-air direct m3u8 streams
# These need a special User-Agent header to play
MJH_USER_AGENT = 'otg/1.5.1 (AppleTv Apple TV 4; tvOS16.0; appletv.client) libcurl/7.58.0 OpenSSL/1.0.2o zlib/1.2.11 clib/1.8.56'

# 24/7 channels — direct m3u8 URLs via i.mjh.nz (not daddylive)
# Channel 7 broadcasts AFL nationally — different states show different games
CHANNELS_247 = [
    # === Channel 7 — all state variants (AFL coverage varies by state) ===
    ('Channel 7 Adelaide',    'https://i.mjh.nz/.r/seven-ade.m3u8', 'Seven SA — local AFL coverage'),
    ('Channel 7 Sydney',      'https://i.mjh.nz/.r/seven-syd.m3u8', 'Seven NSW — AFL coverage'),
    ('Channel 7 Melbourne',   'https://i.mjh.nz/.r/seven-mel.m3u8', 'Seven VIC — AFL coverage'),
    ('Channel 7 Brisbane',    'https://i.mjh.nz/.r/seven-bri.m3u8', 'Seven QLD — AFL coverage'),
    ('Channel 7 Perth',       'https://i.mjh.nz/.r/seven-per.m3u8', 'Seven WA — AFL coverage'),

    # === 7mate — all state variants (sport + AFL) ===
    ('7mate Adelaide',   'https://i.mjh.nz/.r/7mate-ade.m3u8', '7mate SA — AFL/sport'),
    ('7mate Sydney',     'https://i.mjh.nz/.r/7mate-syd.m3u8', '7mate NSW — AFL/sport'),
    ('7mate Melbourne',  'https://i.mjh.nz/.r/7mate-mel.m3u8', '7mate VIC — AFL/sport'),
    ('7mate Brisbane',   'https://i.mjh.nz/.r/7mate-bri.m3u8', '7mate QLD — AFL/sport'),
    ('7mate Perth',      'https://i.mjh.nz/.r/7mate-per.m3u8', '7mate WA — AFL/sport'),

    # === 7 AFL — dedicated 24/7 AFL channel ===
    ('7AFL',             'https://i.mjh.nz/.r/7afl-fast.m3u8', '24/7 AFL channel — replays, highlights, shows'),

    # === 7 sister channels ===
    ('7two Adelaide',    'https://i.mjh.nz/.r/7two-ade.m3u8', '7two SA'),
    ('7flix Adelaide',   'https://i.mjh.nz/.r/7flix-ade.m3u8', '7flix SA'),
    ('7Bravo',           'https://i.mjh.nz/.r/7bravo-fast.m3u8', '7 Bravo 24/7'),

    # === SBS (working direct streams — no more daddylive crashes) ===
    ('SBS',              'https://i.mjh.nz/.r/sbs-sbst.m3u8', 'SBS free-to-air'),
    ('SBS Viceland',     'https://i.mjh.nz/.r/sbs-2syd.m3u8', 'SBS Viceland'),
    ('NITV',             'https://i.mjh.nz/.r/sbs-5nsw.m3u8', 'NITV'),
    ('SBS World Movies', 'https://i.mjh.nz/.r/sbs-4syd.m3u8', 'SBS World Movies'),

    # === ABC ===
    ('ABC TV',           'https://c.mjh.nz/abc-sa.m3u8', 'ABC SA'),
    ('ABC News',         'https://c.mjh.nz/abc-news.m3u8', 'ABC News 24/7'),

    # === Sports channels ===
    ('Cricket Gold',     'https://i.mjh.nz/.r/cricketgold-fast.m3u8', '24/7 cricket channel'),
    ('Racing.com',       'https://i.mjh.nz/.r/racing-fast.m3u8', 'Horse racing'),
    ('Sky News',         'https://i.mjh.nz/.r/sky-news-now.m3u8', 'Sky News Australia'),

    # === Fox Sports AU (Foxtel channels via daddylive embed chain) ===
    ('Fox Footy',        '822', 'Fox Sports 504 AU — AFL coverage (via daddylive)'),
    ('Fox Sports 502',   '820', 'Fox Sports 502 AU (via daddylive)'),
    ('Fox Sports 503',   '821', 'Fox Sports 503 AU (via daddylive)'),
    ('Fox Sports 505',   '823', 'Fox Sports 505 AU (via daddylive)'),
    ('Fox Sports 506',   '824', 'Fox Sports 506 AU (via daddylive)'),
    ('Fox Sports 507',   '825', 'Fox Sports 507 AU (via daddylive)'),
    ('Fox Cricket',     '369', 'Fox Cricket AU (via daddylive)'),

    # === Adult (for fun — via daddylive) ===
    ('Fox Sports 569',   '504', 'Fox Sports 569 AU (via daddylive)'),
]


def show_main_menu():
    """Main menu: Live AFL Matches + 24/7 Channels."""
    xbmcplugin.setContent(ADDON_HANDLE, 'videos')

    # 24/7 Channels folder
    li = xbmcgui.ListItem(label="📺 24/7 Channels (Fox Footy / Channel 7 / SBS / ABC + More)")
    li.setInfo('video', {
        'title': '24/7 Channels',
        'plot': 'Fox Footy, Fox Sports 502-507, Fox Cricket, Channel 7 (all states), 7mate, 7AFL, SBS, ABC, Cricket Gold, Racing.com, Sky News + adult channel.',
        'studio': 'AFL'
    })
    li.setArt({'icon': 'DefaultVideo.png', 'thumb': 'DefaultVideo.png'})
    xbmcplugin.addDirectoryItem(ADDON_HANDLE, get_url({'action': 'channels247'}), li, isFolder=True)

    # Fetch live schedule
    matches = scrape_schedule()

    if not matches:
        li = xbmcgui.ListItem(label="No live AFL matches right now (see 24/7 Channels above)")
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, '', li)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return

    for m in matches:
        # Build label with Adelaide time
        adl = to_adelaide(m['time'])
        if adl:
            label = f"{m['event']} - {m['time']} UTC ({adl} ADL)"
        else:
            label = f"{m['event']} - {m['time']} UTC"

        # If multiple channels, show as folder; if single, playable
        if len(m['channels']) > 1:
            # Folder listing channels
            li = xbmcgui.ListItem(label=label)
            li.setInfo('video', {
                'title': label,
                'plot': f"AFL Match\n{m['event']}\nTime: {m['time']} UTC ({adl or '?'} ADL)\nChannels: {len(m['channels'])} available",
                'studio': 'AFL'
            })
            li.setArt({'icon': 'DefaultVideo.png', 'thumb': 'DefaultVideo.png'})
            # Pass channels as a parameter
            channel_data = '|'.join([f"{name}#{cid}" for name, cid in m['channels']])
            play_url = get_url({'action': 'channels', 'event': m['event'],
                                'time': m['time'], 'channels': channel_data})
            xbmcplugin.addDirectoryItem(ADDON_HANDLE, play_url, li, isFolder=True)
        else:
            # Single channel — playable directly
            ch_name, ch_id = m['channels'][0]
            li = xbmcgui.ListItem(label=label)
            li.setInfo('video', {
                'title': label,
                'plot': f"AFL Match\n{m['event']}\nTime: {m['time']} UTC ({adl or '?'} ADL)\nChannel: {ch_name}",
                'studio': 'AFL'
            })
            li.setArt({'icon': 'DefaultVideo.png', 'thumb': 'DefaultVideo.png'})
            li.setProperty('IsPlayable', 'true')
            play_url = get_url({'action': 'play', 'watch_id': ch_id,
                                'event': m['event'], 'channel': ch_name})
            xbmcplugin.addDirectoryItem(ADDON_HANDLE, play_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def show_channels(event, time_utc, channel_data):
    """Show channel selection for a match with multiple channels."""
    xbmcplugin.setContent(ADDON_HANDLE, 'videos')

    adl = to_adelaide(time_utc)
    for entry in channel_data.split('|'):
        if '#' not in entry:
            continue
        ch_name, ch_id = entry.split('#', 1)
        label = f"{ch_name} - {event}"
        if adl:
            label += f" ({time_utc} UTC / {adl} ADL)"

        li = xbmcgui.ListItem(label=label)
        li.setInfo('video', {
            'title': label,
            'plot': f"AFL Match\n{event}\nChannel: {ch_name}\nTime: {time_utc} UTC ({adl or '?'} ADL)",
            'studio': 'AFL'
        })
        li.setArt({'icon': 'DefaultVideo.png', 'thumb': 'DefaultVideo.png'})
        li.setProperty('IsPlayable', 'true')
        play_url = get_url({'action': 'play', 'watch_id': ch_id,
                            'event': event, 'channel': ch_name})
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, play_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def play_stream(watch_id, event, channel):
    """Resolve stream URL and hand to Kodi player."""
    m3u8_url, daddy_url = resolve_stream(watch_id)

    if not m3u8_url:
        xbmcgui.Dialog().notification(
            ADDON_NAME, f"Failed to resolve stream for {channel}",
            xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return

    # The CDN requires the daddy.php URL as Referer
    play_url = build_url_with_referer(m3u8_url, daddy_url)

    log(f"Resolved: {event} on {channel} -> {play_url[:120]}...")

    li = xbmcgui.ListItem(path=play_url)
    li.setInfo('video', {
        'title': f"{event} - {channel}",
        'studio': 'AFL'
    })
    li.setProperty('inputstreamaddon', 'inputstream.adaptive')
    li.setProperty('inputstream.adaptive.manifest_type', 'hls')
    li.setProperty('IsPlayable', 'true')

    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


def play_direct_m3u8(m3u8_url, event, channel):
    """Play a direct m3u8 URL (e.g. i.mjh.nz streams).
    These need a custom User-Agent header appended to the URL."""
    # Kodi supports |User-Agent= syntax in URL
    play_url = f"{m3u8_url}|User-Agent={urllib.parse.quote(MJH_USER_AGENT)}"

    log(f"Direct stream: {event} on {channel} -> {play_url[:120]}...")

    li = xbmcgui.ListItem(path=play_url)
    li.setInfo('video', {
        'title': f"{event} - {channel}",
        'studio': 'AFL'
    })
    li.setProperty('inputstreamaddon', 'inputstream.adaptive')
    li.setProperty('inputstream.adaptive.manifest_type', 'hls')
    li.setProperty('IsPlayable', 'true')

    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


def show_channels247():
    """Show 24/7 always-on channels (Channel 7, 7mate, SBS, ABC, etc.)."""
    xbmcplugin.setContent(ADDON_HANDLE, 'videos')

    for name, url, desc in CHANNELS_247:
        li = xbmcgui.ListItem(label=name)
        li.setInfo('video', {
            'title': name,
            'plot': desc,
            'studio': 'i.mjh.nz'
        })
        li.setArt({'icon': 'DefaultVideo.png', 'thumb': 'DefaultVideo.png'})
        li.setProperty('IsPlayable', 'true')
        # Use action=play_direct for m3u8 URLs, action=play for daddylive IDs
        if url.startswith('http'):
            play_url = get_url({'action': 'play_direct', 'm3u8_url': url,
                                'event': name, 'channel': name})
        else:
            play_url = get_url({'action': 'play', 'watch_id': url,
                                'event': name, 'channel': name})
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, play_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def router(params_str):
    """Route based on action parameter."""
    if not params_str:
        show_main_menu()
        return

    params = urllib.parse.parse_qs(params_str)
    action = params.get('action', [None])[0]

    if action is None:
        show_main_menu()
    elif action == 'channels247':
        show_channels247()
    elif action == 'channels':
        event = params.get('event', [''])[0]
        time_utc = params.get('time', [''])[0]
        channels = params.get('channels', [''])[0]
        show_channels(event, time_utc, channels)
    elif action == 'play':
        watch_id = params.get('watch_id', [''])[0]
        event = params.get('event', [''])[0]
        channel = params.get('channel', [''])[0]
        play_stream(watch_id, event, channel)
    elif action == 'play_direct':
        m3u8_url = params.get('m3u8_url', [''])[0]
        event = params.get('event', [''])[0]
        channel = params.get('channel', [''])[0]
        play_direct_m3u8(m3u8_url, event, channel)
    else:
        show_main_menu()


if __name__ == '__main__':
    # Parse query string from sys.argv[2]
    query = sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith('?') else ''
    router(query)