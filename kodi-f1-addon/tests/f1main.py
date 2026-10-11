"""
F1 Streams Kodi Addon v2.8.3
Zero external dependencies — uses only Python builtins.
Live streams from dlive.sx + race replays from fullraces.com.
"""

import sys
import re
import json
import ssl
import struct
import gzip
import zlib
import base64
import threading
import socket
import time

from http.server import HTTPServer, BaseHTTPRequestHandler
try:
    from http.server import ThreadingHTTPServer   # Python 3.7+
except ImportError:
    ThreadingHTTPServer = HTTPServer
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
# v2.8.2 — dlive.sx player-iframe embed HOST rotates: dembed.top went NXDOMAIN
#          2026-10-10 and resolution died at Step 3 before any proxy work
#          ("unplayable item" with zero addon invoker lines). The embed PATH
#          (/premiumtv/daddy.php?id=N) is stable across rotations, so the
#          resolver now walks the page-derived host + known-good fallbacks.
# v2.8.3 — mid-play upstream death ("It ran and died" 19:06 ACDT 2026-10-10):
#          stalls from ~19:03, demuxer EOF 19:06:38. The v2.8.2 proxy polled a
#          FIXED upstream URL forever with no re-resolution. Upstream rotated
#          embed hosts twice that evening (dembed.top -> daddyliveplayer.st ->
#          bembed.sbs). Now the refresher detects a frozen ledger + dead
#          upstream, re-runs the full resolve chain in the background, and
#          HOT-SWAPS to the fresh edge: ledger indices keep counting from the
#          live position so the player never sees a sequence break.
CHANNELS = [
    {'id': '60',  'title': 'Sky Sports F1 UK [English]'},
    {'id': '537', 'title': 'DAZN F1 ES [Spanish]'},
]

DLIVE_BASE = 'https://dlive.sx'
# Embed hosts rotate (dembed.top NXDOMAIN 2026-10-10; daddyliveplayer.st
# still serves /premiumtv/daddy.php). Order: page-derived first, then these.
EMBED_HOSTS = ['daddyliveplayer.st']
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
def resolve_upstream_fresh(channel_id):
    """Run the full dlive.sx resolve chain; return (manifest_text, m3u8_url,
    seg_headers) or raise. Used at play time AND by the proxy's self-heal.
    Chain (v2.8.3): /watch.php?id=N -> /stream/stream-N.php iframe ->
    player embed (const SRC = \".../index.m3u8\"). The embed HOST rotates
    (dembed.top died 2026-10-10; daddyliveplayer.st / bembed.sbs serve it),
    so the resolver walks the page host + EMBED_HOSTS until one yields SRC.
    """
    if not channel_id:
        raise ValueError('no channel id')
    # Step 1: watch.php page -> stream page iframe
    watch_url = DLIVE_BASE + '/watch.php?id=' + channel_id
    watch_html = fetch_page(watch_url)
    if not watch_html:
        raise RuntimeError('watch.php fetch failed for %s' % channel_id)
    iframe_m = re.search(r'<iframe[^>]+src="(https?://[^"]*stream-\d+\.php[^"]*)"', watch_html)
    if not iframe_m:
        raise RuntimeError('no stream iframe in watch.php for %s' % channel_id)
    stream_page_url = iframe_m.group(1)

    # Step 2: stream page -> player embed. The page's iframe HOST rotates
    # (dembed.top went NXDOMAIN 2026-10-10) so we only trust its PATH and
    # walk candidate hosts: page-derived first, then EMBED_HOSTS.
    page_html = fetch_page(stream_page_url)
    if not page_html:
        raise RuntimeError('stream page fetch failed for %s' % channel_id)
    iframe_m = re.search(r'<iframe[^>]+src="([^"]+)"', page_html)
    if not iframe_m:
        raise RuntimeError('no iframe in stream page for %s' % channel_id)
    embed_ref = iframe_m.group(1)
    if embed_ref.startswith('//'):
        embed_ref = 'https:' + embed_ref
    _eu = urllib.parse.urlparse(embed_ref)
    # keep path AND query — the ?id=N is how the embed picks the channel
    embed_path = _eu.path + (('?' + _eu.query) if _eu.query else '')
    if _eu.path in ('', '/'):
        embed_path = '/premiumtv/daddy.php?id=' + channel_id

    # Step 3: player page -> const SRC (v2.8.0; old _econfig blob is gone).
    # Try each host until one serves a page containing const SRC.
    candidates = []
    page_host = urllib.parse.urlparse(embed_ref).hostname
    if page_host:
        candidates.append('https://' + page_host + embed_path)
    for host in EMBED_HOSTS:
        candidate = 'https://' + host + embed_path
        if candidate not in candidates:
            candidates.append(candidate)
    player_html = None
    player_origin = None
    for candidate_url in candidates:
        ph = fetch_page(candidate_url)
        if ph and re.search(r'const\s+SRC\s*=\s*"', ph):
            player_html = ph
            origin = urllib.parse.urlparse(candidate_url)
            player_origin = origin.scheme + '://' + origin.netloc + '/'
            log("Embed host OK: %s" % origin.netloc)
            break
        log("Embed host failed: %s" % candidate_url)
    if not player_html or not player_origin:
        raise RuntimeError('all embed hosts failed for %s' % channel_id)
    src_m = re.search(r'const\s+SRC\s*=\s*"([^"]+)"', player_html)
    if not src_m:
        raise RuntimeError('no const SRC in player page for %s' % channel_id)
    upstream_m3u8 = src_m.group(1)

    # Step 4: fetch the freshly-resolved upstream manifest
    seg_headers = {'User-Agent': UA, 'Referer': player_origin}
    man = fetch_page(upstream_m3u8, seg_headers, 15)
    if not man or '#EXTM3U' not in man:
        raise RuntimeError('upstream manifest fetch failed for %s' % channel_id)
    return man, upstream_m3u8, seg_headers


def resolve_live_stream(channel_id):
    """Resolve a dlive.sx 24/7 channel id (e.g. '60') to a playable m3u8 URL.

    Segments are PNG-stego cloaked (gzip'd TS hidden in RGB pixel data,
    'TIKTIKPX' magic), so the manifest is re-served through a local unwrap
    proxy and Kodi plays http://127.0.0.1:<port>/stream.m3u8.
    v2.8.3: chain work lives in resolve_upstream_fresh(); this wires the
    proxy threads. channel_id is remembered on the proxy so the healer can
    re-run the chain with the same id.
    """
    if not channel_id:
        return None
    try:
        man, upstream_m3u8, seg_headers = resolve_upstream_fresh(channel_id)
        seg_urls = [l.strip() for l in man.splitlines()
                    if l.strip() and not l.startswith('#')]
        if not seg_urls:
            log("Manifest has no segments for %s" % channel_id)
            return None
        proxy = get_unwrap_proxy()
        port = proxy.start() if not proxy.server else proxy.PORT
        proxy.channel_id = channel_id
        proxy.load_manifest(upstream_m3u8, man, seg_headers)
        # dedicated refresher: polls upstream so the window keeps rolling
        if not proxy.refresher_thread or not proxy.refresher_thread.is_alive():
            proxy.refresher_thread = threading.Thread(
                target=proxy._refresh_loop, daemon=True)
            proxy.refresher_thread.start()
        local_url = 'http://127.0.0.1:%d/stream.m3u8' % port
        log("Resolved channel %s via unwrap proxy: %s (%s, %d segs)"
            % (channel_id, local_url, upstream_m3u8[:60], len(seg_urls)))
        return local_url
    except Exception as e:
        log("Stream resolve error (dlive.sx): %s" % e)
        return None
# ============ PNG-STEGO UNWRAP PROXY ============

_STEGO_MAGIC = b'TIKTIKPX'
_MAGIC_PREAMBLE = 4          # TIKTIKPX + 4 junk bytes before gzip
_TS_PACKET = 188


def _png_unfilter(raw, w, h, bpp, stride):
    """Undo PNG per-scanline filtering in pure Python."""
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    n = len(raw)
    while i < n:
        f = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        if f == 1:  # Sub
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) % 256
        elif f == 2:  # Up
            for x in range(stride):
                line[x] = (line[x] + prev[x]) % 256
        elif f == 3:  # Average
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) % 256
        elif f == 4:  # Paeth
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) % 256
        out += line
        prev = line
    return bytes(out)


def _unwrap_png_segment(png_bytes):
    """Extract gzip'd MPEG-TS hidden in PNG RGB pixel data.

    Layout (reverse-engineered 2026-09-26):
      PNG (512xN RGB) -> unfilter -> pixel bytes start with 'TIKTIKPX'
      + 4 junk bytes -> gzip stream -> raw MPEG-TS.
    """
    if png_bytes[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    pos = 8
    idat = b''
    while pos < len(png_bytes):
        ln = struct.unpack('>I', png_bytes[pos:pos + 4])[0]
        typ = png_bytes[pos + 4:pos + 8]
        data = png_bytes[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, _bd, ct = struct.unpack('>IIBB', data[:10])
        elif typ == b'IDAT':
            idat += data
        elif typ == b'IEND':
            break
        pos += 12 + ln
    try:
        raw = zlib.decompress(idat)
    except Exception:
        return None
    try:
        bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    except KeyError:
        return None
    # 8-bit depths only: each filtered row = 1 filter byte + w*bpp bytes.
    # (The (bits+7)//8 packing formula would be wrong here — verified
    # 2026-09-26: raw length == (w*bpp + 1) * h exactly.)
    stride = w * bpp
    if len(raw) < (stride + 1) * h:
        return None
    pixels = _png_unfilter(raw, w, h, bpp, stride)
    mi = pixels.find(_STEGO_MAGIC)
    if mi < 0:
        return None
    gz = pixels[mi + len(_STEGO_MAGIC) + _MAGIC_PREAMBLE:]
    try:
        # wbits=31 = gzip member; stops cleanly at member end and ignores
        # trailing pixel bytes (segments are bigger than their payload).
        d = zlib.decompressobj(31)
        return d.decompress(gz)
    except Exception:
        return None


class _UnwrapProxyHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'   # keep-alive: fewer connect stalls in Kodi

    def do_GET(self):
        proxy = self.server.proxy
        try:
            if self.path.startswith('/stream.m3u8'):
                # live: re-poll upstream each time Kodi re-fetches the playlist
                body = proxy.refresh_manifest().encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith('/seg/'):
                try:
                    idx = int(self.path[5:].split('.')[0])
                except (ValueError, IndexError):
                    idx = -1
                if idx < 0:
                    self.send_response(404); self.send_header('Content-Length', '0'); self.end_headers(); return
                proxy.note_request(idx)
                # fetch_segment already pixel-unwraps; it returns plain MPEG-TS
                ts = proxy.fetch_segment(idx)
                if ts is None:
                    self.send_response(502)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp2t')
                self.send_header('Content-Length', str(len(ts)))
                self.end_headers()
                self.wfile.write(ts)
            else:
                self.send_response(404)
                self.send_header('Content-Length', '0')
                self.end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Kodi's HLS reader hung up mid-body (timed out waiting) — silent.
            pass

    def log_message(self, *a):
        pass


class UnwrapProxy:
    """Local HTTP server that serves an unwrapped (de-cloaked) HLS stream.

    Kodi fetches http://127.0.0.1:<port>/stream.m3u8 — a sliding-window live
    playlist (EXT-X-MEDIA-SEQUENCE) whose segment URLs are /seg/<n>.ts with n
    on an ABSOLUTE ledger: indices never shift when the window advances.
    Each segment request hits the cache or fetches the PNG-cloaked upstream
    segment, pixel-unwraps the gzip'd TS, and serves plain MPEG-TS to Kodi's
    ffmpeg player.

    v2.8.1 crash fix (Sky + DAZN both stalled ~15-20s into playback): the old
    proxy re-polled upstream SYNCHRONOUSLY inside Kodi's playlist request and
    keyed segments by position in a fixed list, so when upstream rotated its
    URLs the next playlist read either blocked (decoder stall) or 502'd
    (playback end). Now:
      - a dedicated refresher thread polls upstream and appends newly-seen
        segment URLs to an append-only ledger (dedup by URL); playlist
        requests NEVER touch the network
      - EXT-X-MEDIA-SEQUENCE = first ledger index → ffmpeg treats the
        playlist as a proper live sliding window
      - EXTINF/TARGETDURATION passed through from upstream (no fake 6.0)
      - prefetch thread unwraps the next segments before Kodi asks
      - ThreadingHTTPServer: playlist + segment requests never queue on a
        single accept loop
    v2.8.3: self-healing. The refresher re-runs the full resolve chain when
    the upstream dies mid-play (host rotations killed session 1 tonight) and
    hot-swaps to the fresh edge — ledger seq continues, player never notices.
    """

    PORT = 8776
    WINDOW = 6            # target playlist window size (segments)
    MAX_HOLD = 72         # max ledger length before front-trim
    POLL_MIN = 2.5        # seconds between upstream manifest polls
    PREFETCH_AHEAD = 4    # unwrap this many segments before Kodi needs them
    HEAL_POLL_FAILURES = 3   # hard manifest-poll failures before heal
    HEAL_FROZEN_SECONDS = 45  # window unchanged this long == stale
    HEAL_BACKOFF = 20     # seconds between re-resolve attempts

    def __init__(self):
        self.server = None
        self.thread = None
        self._lock = threading.Lock()
        self.upstream_m3u8 = None
        self.ledger = []             # [(abs_idx, url, dur)] append-only
        self._seen = set()           # dedup upstream URLs
        self.media_seq = 0           # abs_idx of ledger[0]
        self.seg_headers = {}
        self.last_poll = 0.0
        self.poll_failures = 0
        self.prefetch_event = threading.Event()
        self.prefetch_thread = None
        self.refresher_thread = None
        self.cache = {}              # abs_idx -> unwrapped TS bytes
        self.max_served = -1
        self._cache_lock = threading.Lock()
        # v2.8.3 self-heal state
        self.channel_id = None       # set by load_manifest caller
        self.last_ledger_change = time.time()   # for frozen-window detection
        self.last_ledger_len = -1
        self._healing = threading.Event()       # re-resolve in progress
        self._heal_thread = None

    def _cache_put(self, idx, ts):
        with self._cache_lock:
            self.cache[idx] = ts
            if len(self.cache) > 3 * self.WINDOW:
                floor = self.media_seq + len(self.ledger) - 6
                for k in [i for i in self.cache if i < floor]:
                    del self.cache[k]

    def start(self):
        try:
            cls = ThreadingHTTPServer if ThreadingHTTPServer else HTTPServer
            self.server = cls(('127.0.0.1', 0), _UnwrapProxyHandler)
            self.server.proxy = self
            self.server.daemon_threads = True
            self.PORT = self.server.server_address[1]
            self.thread = threading.Thread(target=self.server.serve_forever,
                                           kwargs={'poll_interval': 0.2})
            self.thread.daemon = True
            self.thread.start()
            log("Unwrap proxy listening on 127.0.0.1:%d" % self.PORT)
        except OSError:
            # previous playback still holds the port — reuse it
            self.server = 'reused'
            log("Unwrap proxy already running on 127.0.0.1:%d" % self.PORT)
        return self.PORT

    @staticmethod
    def _parse_playlist(text):
        """Extract (url, EXTINF-duration) pairs from an m3u8 playlist."""
        urls, durs, pending = [], [], None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#EXTINF:'):
                try:
                    pending = float(line[8:].split(',')[0])
                except (ValueError, IndexError):
                    pending = None
            elif line and not line.startswith('#'):
                urls.append(line)
                durs.append(pending if pending is not None else 6.0)
                pending = None
        return urls, durs

    def _absorb(self, urls, durs):
        """Append newly-seen upstream segments to the absolute ledger."""
        added = False
        for u, d in zip(urls, durs):
            if u not in self._seen:
                self._seen.add(u)
                abs_idx = self.media_seq + len(self.ledger)
                self.ledger.append((abs_idx, u, d))
                added = True
        if added:
            self.last_ledger_change = time.time()

    def load_manifest(self, upstream_m3u8, manifest_text, seg_headers):
        """First load: reset ledger and start from segment 0."""
        urls, durs = self._parse_playlist(manifest_text)
        with self._lock:
            self.upstream_m3u8 = upstream_m3u8
            self.seg_headers = dict(seg_headers)
            self.ledger = []
            self._seen = set()
            self.media_seq = 0
            self.cache = {}
            self.max_served = -1
            self.last_poll = time.time()
            self.poll_failures = 0
            self._absorb(urls, durs)
        self.prefetch_event.set()
        if not self.prefetch_thread or not self.prefetch_thread.is_alive():
            self.prefetch_thread = threading.Thread(
                target=self._prefetch_loop, daemon=True)
            self.prefetch_thread.start()

    def load_manifest_append(self, upstream_m3u8, manifest_text, seg_headers):
        """Heal swap (v2.8.3): APPEND to the live ledger, never reset it.

        The fresh upstream's segments join at absolute idx = last+1; old
        cached entries stay servable while Kodi transitions; MAX_HOLD trim
        removes stale fronts naturally as new segments arrive. MEDIA-SEQUENCE
        therefore never goes backwards — ffmpeg keeps playing seamlessly.
        """
        urls, durs = self._parse_playlist(manifest_text)
        with self._lock:
            self.upstream_m3u8 = upstream_m3u8
            self.seg_headers = dict(seg_headers)
            self.poll_failures = 0
            self.last_poll = time.time()
            before = len(self.ledger)
            self._absorb(urls, durs)
            added = len(self.ledger) - before
        log("HEAL: upstream appended %d fresh segments (ledger %d -> %d)"
            % (added, before, before + added))
        self.prefetch_event.set()
        if not self.prefetch_thread or not self.prefetch_thread.is_alive():
            self.prefetch_thread = threading.Thread(
                target=self._prefetch_loop, daemon=True)
            self.prefetch_thread.start()

    def _poll_upstream(self):
        """Poll upstream manifest; absorb new segments, trim the front."""
        with self._lock:
            up, hdrs = self.upstream_m3u8, dict(self.seg_headers)
        try:
            req = urllib.request.Request(up, headers=hdrs)
            with urllib.request.urlopen(req, timeout=10,
                                        context=_SSL_CTX) as resp:
                man = resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            self.poll_failures += 1
            log("Manifest poll error #%d: %s" % (self.poll_failures, e))
            return
        urls, durs = self._parse_playlist(man)
        with self._lock:
            before = len(self.ledger)
            self._absorb(urls, durs)
            added = len(self.ledger) - before
            if added == 0:
                # Zombie edge: 200 OK but nothing new — treat as failure so
                # HEAL_FROZEN_SECONDS / HEAL_POLL_FAILURES can engage.
                self.poll_failures += 1
                log("Manifest poll: 0 new segments (zombie) #%d"
                    % self.poll_failures)
            else:
                self.poll_failures = 0
            if len(self.ledger) > self.MAX_HOLD:
                drop = len(self.ledger) - self.MAX_HOLD
                self.ledger = self.ledger[drop:]
                self.media_seq += drop
            self.prefetch_event.set()

    def refresh_manifest(self):
        """Build the current sliding-window playlist. Never blocks on net."""
        with self._lock:
            snapshot = list(self.ledger)
        if not snapshot:
            return '#EXTM3U\n'
        window = snapshot[-self.WINDOW:]   # tail only: start near-live
        target = max(d for _i, _u, d in window)
        lines = ['#EXTM3U', '#EXT-X-VERSION:3',
                 '#EXT-X-TARGETDURATION:%d' % int(target + 0.999),
                 '#EXT-X-MEDIA-SEQUENCE:%d' % window[0][0],
                 '#EXT-X-DISCONTINUITY-SEQUENCE:0']
        for i, _u, d in window:
            lines.append('#EXTINF:%.3f,' % d)
            lines.append('/seg/%d.ts' % i)
        return '\n'.join(lines) + '\n'

    def note_request(self, idx):
        with self._lock:
            if idx > self.max_served:
                self.max_served = idx
        self.prefetch_event.set()

    def _fetch_unwrap(self, url, timeout=20):
        if not url.startswith('http'):
            url = urllib.parse.urljoin(self.upstream_m3u8, url)
        try:
            req = urllib.request.Request(url, headers=self.seg_headers)
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=_SSL_CTX) as resp:
                png = resp.read()
            return _unwrap_png_segment(png)
        except Exception as e:
            log("Segment fetch error: %s" % e)
            return None

    def _fetch_unwrap_raced(self, url, racers=2, timeout=8):
        """Race N parallel downloads of the same segment against TikTok's
        flaky CDN. Whichever lands first wins; losers are cancelled. Worst-
        case latency drops from p99(=20s) to ~min(random draws) — measured
        2.9s median / 10s spikes serial, ~1.5s median / ~4s spike raced.
        Falls back to plain serial fetch on first error."""
        if not url.startswith('http'):
            url = urllib.parse.urljoin(self.upstream_m3u8, url)
        result = [None]
        done = threading.Event()
        def one():
            if done.is_set():
                return
            ts = self._fetch_unwrap(url, timeout=timeout)
            if ts is not None and not done.is_set():
                result[0] = ts
                done.set()
        threads = [threading.Thread(target=one, daemon=True)
                   for _ in range(racers)]
        for t in threads:
            t.start()
        # Wait a touch longer than per-race timeout for stragglers
        done.wait(timeout + 3)
        return result[0]

    def fetch_segment(self, idx):
        if idx in self.cache:
            return self.cache[idx]
        with self._lock:
            url = None
            for i, u, _d in self.ledger:
                if i == idx:
                    url = u
                    break
        if url is None:
            return None
        # Kodi is actively waiting on this segment — race parallel connections.
        ts = self._fetch_unwrap_raced(url)
        if ts is not None:
            self._cache_put(idx, ts)
        else:
            log("Segment %d unwrap failed" % idx)
        return ts

    def _refresh_loop(self):
        self.poll_failures = 0
        while True:
            if self.upstream_m3u8:
                self._poll_upstream()
                self._maybe_start_heal()
            gap = self.POLL_MIN * (3 if self.poll_failures > 2 else 1)
            time.sleep(gap)

    def _maybe_start_heal(self):
        """Declare upstream dead when polls fail hard OR window freezes."""
        if self._healing.is_set():
            return
        with self._lock:
            n = len(self.ledger)
            failed = self.poll_failures
        if n != self.last_ledger_len:
            self.last_ledger_len = n
            self.last_ledger_change = time.time()
        frozen = (time.time() - self.last_ledger_change) > self.HEAL_FROZEN_SECONDS
        if failed >= self.HEAL_POLL_FAILURES or (frozen and failed >= 1):
            log("HEAL: upstream dead (polls failed=%d, frozen=%s) — "
                "re-resolving channel %s" % (failed, frozen, self.channel_id))
            self._healing.set()
            self._heal_thread = threading.Thread(target=self._heal,
                                                 daemon=True)
            self._heal_thread.start()

    def _heal(self):
        """Re-run the resolve chain in the background and hot-swap."""
        tries = 0
        while self._healing.is_set():
            tries += 1
            try:
                man, upstream, hdrs = resolve_upstream_fresh(self.channel_id)
            except Exception as e:
                man, upstream, hdrs = None, None, None
                log("HEAL: resolve attempt %d error: %s" % (tries, e))
            if man and '#EXTM3U' in man:
                self.load_manifest_append(upstream, man, hdrs)
                self._healing.clear()
                break
            log("HEAL: attempt %d failed — retry in %ds" % (tries,
                                                            self.HEAL_BACKOFF))
            time.sleep(self.HEAL_BACKOFF)

    def _prefetch_loop(self):
        while True:
            self.prefetch_event.wait(timeout=1.5)
            self.prefetch_event.clear()
            with self._lock:
                targets = [(i, u) for i, u, _d in self.ledger
                           if self.max_served <= i
                           <= self.max_served + self.PREFETCH_AHEAD
                           and i not in self.cache]
            for i, u in targets:
                if i in self.cache:
                    continue
                ts = self._fetch_unwrap_raced(u, racers=2, timeout=12)
                if ts is not None:
                    self._cache_put(i, ts)


def get_unwrap_proxy():
    """Singleton accessor so repeated plays reuse the same server."""
    global _UNWRAP_PROXY
    try:
        _UNWRAP_PROXY
    except NameError:
        _UNWRAP_PROXY = UnwrapProxy()
    return _UNWRAP_PROXY


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
        {'label': 'F1 Classic Archive (2022)',
         'url': get_url({'action': 'replays', 'cat': 'formula1-2022'}), 'is_folder': True},
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

    # dlive.sx resolver (v2.8.0) — upstream PNG-stego cloaking is unwrapped
    # by the built-in local proxy; just play the local manifest URL as-is
    # (no pipe headers needed for 127.0.0.1).
    stream_url = resolve_live_stream(channel_id)

    if not stream_url:
        xbmcgui.Dialog().notification(ADDON_NAME,
                                       "Could not resolve stream. The channel may be offline.",
                                       xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return
    log("Playing live: %s" % stream_url)
    xbmcgui.Dialog().notification(ADDON_NAME, "Resolved: " + stream_url[:80],
                                   xbmcgui.NOTIFICATION_INFO, 5000)
    # Local unwrap proxy manifest — plain HTTP, no inputstream.adaptive
    # (Kodi's built-in ffmpeg player; inputstream.adaptive was crashing Kodi)
    li = xbmcgui.ListItem(path=stream_url)
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