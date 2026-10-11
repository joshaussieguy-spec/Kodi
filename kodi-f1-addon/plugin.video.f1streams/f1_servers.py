# -*- coding: utf-8 -*-
"""f1_servers.py — Sky F1 backup servers (GB/DE/ES) + event banner. F1 Streams 2.8.7.

Agenda:  https://tvsport.guide/proxy.php?source=index  (JSON; startTimestamp = epoch ms)
Servers: vertex.st / nexa.st / kora.st  ch7=Sky Sports F1 (GB), ch19=Sky Sport F1 (DE),
         ch30=DAZN F1 (ES).  Chain: {host}/ch?id=N -> player/embed .php -> matchli.st
         embed page -> signed m3u8 (hls.hockey.do). Playlist needs *any* Referer
         (proxy supplies watchfa.st); segments are header-free. Sigs expire fast
         (short window) => resolve FRESH on every play. kora embed is a base64 blob
         (best-effort, may fail) — vertex/nexa are the proven ones (2026-10-11).
"""
import json
import os
import re
import subprocess
import time

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
CURL = os.path.join(ADDON_DIR, 'bin', 'curl-impersonate.exe')
_SUB_KW = {'creationflags': 0x08000000} if os.name == 'nt' else {}  # CREATE_NO_WINDOW
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
AGENDA_URL = 'https://tvsport.guide/proxy.php?source=index'
PROVIDERS = (('vertex', 'vertex.st'), ('nexa', 'nexa.st'), ('kora', 'kora.st'))
REFERER_PLAYLIST = 'https://watchfa.st/'
FEEDS = (
    ('vertex', 7, 'Sky F1 UK'), ('nexa', 7, 'Sky F1 UK'), ('kora', 7, 'Sky F1 UK'),
    ('nexa', 19, 'Sky F1 DE'), ('vertex', 19, 'Sky F1 DE'),
    ('nexa', 30, 'F1 ES (DAZN)'),
)
M3U8_RE = re.compile(r'(https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*)')
PLAYER_RE = re.compile(r'((?:https?://[^"\'\s<>]+)?/[\w./-]*(?:player|embed)[\w.-]*\.php\?[\w=&%-]+)')


def _de_esc(s):
    if '\\u' in s or '\\/' in s:
        s = s.replace('\\/', '/').replace('\\u0026', '&').replace('\\u003d', '=')
        s = s.replace('\\u003F', '?').replace('\\u003f', '?').replace('\\u002F', '/')
        if '\\u' in s:
            try:
                s = s.encode('latin-1', 'replace').decode('unicode_escape')
            except Exception:
                pass
    return s


def _http(url, referer=None, timeout=25):
    exe = CURL if os.path.exists(CURL) else 'curl'
    args = [exe, '-sS', '-L', '--max-time', str(timeout), '-A', UA]
    if referer:
        args += ['-e', referer]
    args.append(url)
    try:
        return subprocess.check_output(args, timeout=timeout + 5, **_SUB_KW)
    except Exception:
        try:
            import urllib.request
            req = urllib.request.Request(url)
            req.add_header('User-Agent', UA)
            if referer:
                req.add_header('Referer', referer)
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception:
            return b''


def fetch_schedule(timeout=25):
    """Return list of {'ts': ms, 'name': str, 'league': str, 'channels': [...]}."""
    raw = _http(AGENDA_URL, timeout=timeout)
    try:
        j = json.loads(raw.decode('utf-8', 'replace'))
    except Exception:
        return []
    now = time.time() * 1000.0
    evs = []
    for m in j.get('matches') or []:
        try:
            ts = float(m.get('startTimestamp') or 0)
        except (TypeError, ValueError):
            continue
        if not ts or abs(ts - now) > 26 * 3600000:
            continue
        name = m.get('matchstr') or m.get('team1') or ''
        if not (m.get('channels') or []):
            continue
        evs.append({'ts': ts, 'name': name.strip(), 'league': m.get('league') or '',
                    'channels': m.get('channels')})
    evs.sort(key=lambda x: x['ts'])
    return evs


def adelaide_label(ts_ms):
    """Epoch ms -> '10:30pm' in Adelaide time (ACDT +10:30 Oct-Apr, ACST +9:30 Apr-Oct)."""
    import datetime as dtmod
    t = dtmod.datetime.fromtimestamp(ts_ms / 1000.0, dtmod.timezone.utc)
    # AEST = UTC+9:30 fixed; ACDT = UTC+10:30 (first Sun Oct -> first Sun Apr)
    mo = t.month
    if mo in (10, 11, 12, 1, 2, 3):
        off = dtmod.timedelta(hours=10, minutes=30)   # ACDT
        tag = 'ACDT'
    else:
        off = dtmod.timedelta(hours=9, minutes=30)    # ACST
        tag = 'ACST'
    loc = t + off
    lab = loc.strftime('%I:%M%p')
    lab = lab[:-2] + lab[-2].lower() + lab[-1].lower()  # AM->am, PM->pm
    if lab.startswith('0'):
        lab = lab[1:]
    return lab, tag


def pick_event(evs=None):
    """Most relevant Formula 1 event: live > next future > most recent past."""
    evs = evs if evs is not None else fetch_schedule()
    f1 = [e for e in evs if e.get('league', '').lower() == 'formula 1']
    if not f1:
        return None
    now = time.time() * 1000.0
    live = [e for e in f1 if abs(e['ts'] - now) < 3.5 * 3600000]
    if live:
        return live[0]
    fut = [e for e in f1 if e['ts'] > now]
    if fut:
        return fut[0]
    return f1[-1]


def banner_text(evs=None):
    """e.g. 'Singapore Grand Prix - Race · starts 10:30pm ACDT' / '· LIVE (started 10:30pm)'."""
    e = pick_event(evs)
    if not e:
        return None
    lab, tag = adelaide_label(e['ts'])
    n = e['name']
    n = re.sub(r'^\W*\w+:\s*', '', n)  # strip 'Motorsport:' style prefixes
    now = time.time() * 1000.0
    if now - 3.5 * 3600000 <= e['ts'] <= now + 15 * 60000:
        return u'%s · LIVE (started %s %s)' % (n, lab, tag)
    if e['ts'] > now:
        return u'%s · starts %s %s' % (n, lab, tag)
    return u'%s · was at %s %s' % (n, lab, tag)


def resolve(provider, ch=7, timeout=25):
    """provider in {vertex,nexa,kora} -> final m3u8 URL str, or None.
    Chain: {base}/api/player.php?id={ch} -> JSON {"url": matchli embed}
           -> embed page -> signed m3u8.  (kora: atob blob, best-effort.)"""
    host = dict(PROVIDERS).get(provider)
    if not host:
        return None
    base = 'https://' + host
    ref = '%s/ch?id=%s' % (base, ch)

    def _final_m3u8(html):
        m3 = M3U8_RE.findall(_de_esc(html))
        return _de_esc(m3[-1]) if m3 else None

    pjson = _http('%s/api/player.php?id=%s' % (base, ch), referer=ref, timeout=timeout).decode('utf-8', 'replace')
    jm = re.search(r'"url"\s*:\s*"([^"]+)"', pjson)
    if jm:
        emb = _de_esc(jm.group(1))
        if emb.startswith('/'):
            emb = base + emb
        fp = _http(emb, referer=ref, timeout=timeout).decode('utf-8', 'replace')
        u = _final_m3u8(fp)
        if u:
            return u
    # generic fallback: scrape the channel page itself
    page = _http(ref, timeout=timeout).decode('utf-8', 'replace')
    u = _final_m3u8(page)
    if u:
        return u
    cand = PLAYER_RE.findall(page)
    for c in cand:
        c = _de_esc(c)
        if c.startswith('/'):
            c = base + c
    # kora-style: whole page is base64/atob blob
    mb = re.search(r'atob\("([^"]+)"\)', page)
    if mb:
        import base64
        try:
            dec = base64.b64decode(mb.group(1)).decode('utf-8', 'replace')
            u = _final_m3u8(dec)
            if u:
                return u
        except Exception:
            pass
    return None


# ---- plain-HLS relay proxy (2.8.7, backup servers) -------------------------
# Mirrors main.UnwrapProxy's architecture (append-only ledger, refresher
# thread, local ThreadingHTTPServer) minus the PNG pixel-unwrap: vertex/nexa
# feeds are ordinary HLS. Kodi plays http://127.0.0.1:<port>/plain/stream.m3u8,
# which is an absolute-ledger sliding window -> /plain/seg/<n>.ts.
# v2.8.7: upstream m3u8 signatures expire (~30 min) — refresher pre-emptively
# re-resolves inside SIG_MARGIN, hard failures / frozen window trigger the
# heal thread (full re-resolve + verify) so playback rides host rotation.
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

RELAY_PORT = 0            # 0 → pick free ephemeral port
SEG_TIMEOUT = 20
NOTIFY = None             # main.py assigns its log() here (after import)


class _RelayHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _serve(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        relay = self.server.relay
        try:
            if self.path.startswith(('/plain/stream.m3u8', '/stream.m3u8')):
                self._serve(relay.refresh_manifest().encode('utf-8'),
                            'application/vnd.apple.mpegurl')
            elif self.path.startswith('/plain/seg/'):
                try:
                    idx = int(self.path.rsplit('/', 1)[1].split('.')[0])
                except (ValueError, IndexError):
                    idx = -1
                relay.note_request(idx)
                ts = relay.fetch_segment(idx)
                if ts is None:
                    self.send_response(502)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                self._serve(ts, 'video/mp2t')
            else:
                self.send_response(404)
                self.send_header('Content-Length', '0')
                self.end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass    # Kodi reader hung up mid-body — routine on live windows

    def log_message(self, *a):
        pass


class HLSRelay(object):
    WINDOW = 6
    POLL_MIN = 2.5
    SIG_MARGIN = 180        # re-resolve when upstream sig expires within this
    HEAL_FROZEN = 45        # seconds without new segments => heal
    HEAL_FAILURES = 3
    MAX_HOLD = 96           # ledger front-trim threshold
    PLAY_LAG = 32.0         # v2.8.9: manifest ends this many seconds behind
                            # ledger head — delay-watch; prefetch thread keeps
                            # the window pre-downloaded so upstream flap
                            # bursts never starve Kodi's buffer

    def __init__(self):
        self.server = None
        self._lock = threading.Lock()
        self.provider = None
        self.ch = None
        self.upstream_m3u8 = None
        self.sig_exp = 0.0
        self.ledger = []    # [(idx, url, dur)]
        self.next_idx = 0
        self.cache = {}     # idx -> ts bytes
        self._done = set()  # v2.8.9: idx once fetched-attempted (no restorm)
        self.max_served = -1
        self.last_change = time.time()
        self.poll_failures = 0
        self.seen = set()
        self._healing = threading.Event()

    def _say(self, msg):
        if NOTIFY:
            try:
                NOTIFY('relay: %s' % msg)
            except Exception:
                pass

    def ensure(self, provider, ch):
        """Switch/confirm the upstream for provider+ch. Returns (port, url)."""
        with self._lock:
            same = (self.provider == provider and self.ch == ch
                    and self.upstream_m3u8 and self.server)
        if same:
            with self._lock:
                return (self.server.server_address[1], self.upstream_m3u8)
        url = resolve(provider, ch)
        if not url:
            # resolve failed — keep any existing session intact, tell caller
            return (0, '')
        with self._lock:
            self.provider, self.ch = provider, ch
            if url and url != self.upstream_m3u8:
                self.ledger, self.cache, self.seen = [], {}, set()
                self.next_idx, self.max_served, self.sig_exp = 0, -1, 0.0
            self.upstream_m3u8 = url
            self._healing.clear()
            if not self.server:
                self._start()
            port = self.server.server_address[1] if self.server else 0
        return (port, url)

    def _start(self):
        srv = ThreadingHTTPServer(('127.0.0.1', RELAY_PORT), _RelayHandler)
        srv.relay = self
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        threading.Thread(target=self._refresh_loop, daemon=True).start()
        threading.Thread(target=self._prefetch_loop, daemon=True).start()
        self.server = srv

    @staticmethod
    def _sig_of(url):
        m = re.search(r'[?&]e=(\d{9,12})', url or '')
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return 0.0

    def _reresolve(self):
        """Fresh signed upstream; returns True on swap."""
        try:
            url = resolve(self.provider, self.ch)
        except Exception:
            return False
        if url and url != self.upstream_m3u8:
            with self._lock:
                self.upstream_m3u8 = url
                self.sig_exp = self._sig_of(url)
            self._say('hot-swapped upstream %s' % url[:80])
        return bool(url)

    def _poll(self):
        """Fetch the upstream playlist, append unseen segments to the ledger."""
        up = self.upstream_m3u8
        if not up:
            return
        exp = self._sig_of(up)
        try:
            body = _http(up, referer=REFERER_PLAYLIST, timeout=15
                         ).decode('utf-8', 'replace')
        except Exception:
            body = ''
        if '#EXTM3U' not in body:
            with self._lock:
                self.poll_failures += 1
            self._say('poll failed (%d)' % self.poll_failures)
            return
        self._ingest(body, up)
        if exp and (exp - time.time()) < self.SIG_MARGIN:
            self._say('sig expires soon (e=%.0f) — pre-emptive re-resolve' % exp)
            self._reresolve()

    def _ingest(self, body, up):
        pend_dur = 4.0
        added = 0
        with self._lock:
            for line in body.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#EXTINF:'):
                    try:
                        pend_dur = float(line[8:].split(',')[0])
                    except (ValueError, IndexError):
                        pend_dur = 4.0
                    continue
                if line.startswith('#'):
                    continue
                seg = urllib.parse.urljoin(up, line)
                if seg not in self.seen:
                    self.seen.add(seg)
                    self.ledger.append((self.next_idx, seg, pend_dur))
                    self.next_idx += 1
                    added += 1
            if added:
                self.last_change = time.time()
                self.poll_failures = 0
            if len(self.ledger) > self.MAX_HOLD:
                self.ledger = self.ledger[-self.MAX_HOLD:]
        if added:
            self._say('poll +%d seg (ledger n=%d)' % (added, len(self.ledger)))

    def refresh_manifest(self):
        if not self.ledger:
            self._poll()          # inline first poll: playback starts instantly
        with self._lock:
            if not self.ledger:
                return '#EXTM3U\n#EXT-X-ENDLIST\n'
            head = self.ledger[-1][0]
            # v2.8.9 delay-watch: cut the window PLAY_LAG s behind ledger head
            cut = head
            acc = 0.0
            for idx, _u, d in reversed(self.ledger):
                if acc + d > self.PLAY_LAG and cut != head:
                    break
                acc += d
                cut = idx
            window = [e for e in self.ledger if cut <= e[0] <= head]
            first = window[0][0]
            dur = max(4, int(round(max(d for _i, _u, d in window))))
            lines = ['#EXTM3U', '#EXT-X-VERSION:3',
                     '#EXT-X-TARGETDURATION:%d' % dur,
                     '#EXT-X-MEDIA-SEQUENCE:%d' % first]
            for idx, _u, d in window:
                lines.append('#EXTINF:%.3f,' % d)
                lines.append('/plain/seg/%d.ts' % idx)
            self.max_served = max(self.max_served, window[-1][0])
            return '\n'.join(lines) + '\n'

    def note_request(self, idx):
        with self._lock:
            if idx > self.max_served:
                self.max_served = idx

    def fetch_segment(self, idx):
        if idx in self.cache:
            return self.cache[idx]
        with self._lock:
            url = next((u for i, u, _d in self.ledger if i == idx), None)
        if url is None:
            self._poll()          # maybe upstream rotated; re-sync
            with self._lock:
                url = next((u for i, u, _d in self.ledger if i == idx), None)
        if url is None:
            return None
        ts = None
        for attempt in (1, 2):
            ts = _http(url, timeout=SEG_TIMEOUT)
            if ts and len(ts) > 4096:
                with self._lock:
                    self.cache[idx] = ts
                    self._done.add(idx)
                return ts
            time.sleep(0.5)
        self._say('seg %d fetch failed' % idx)
        self._done.add(idx)
        # on-demand fallback also starved → heal (restores old resiliency)
        if idx > self.max_served or (self.max_served == -1):
            pass
        self._heal_check_ondemand(idx)
        return ts

    def _heal_check_ondemand(self, idx):
        """Heal only if the failing seg is near the play edge (not a stale
        backlog seg whose upstream rotated away)."""
        with self._lock:
            head = self.ledger[-1][0] if self.ledger else -1
        if head >= 0 and (head - idx) <= self.WINDOW:
            self._heal_async()

    def _health(self):
        now = time.time()
        with self._lock:
            frozen = (now - self.last_change) > self.HEAL_FROZEN
            fails = self.poll_failures
        if fails >= self.HEAL_FAILURES or (frozen and fails >= 1):
            self._say('HEAL: failures=%d frozen=%s — re-resolving %s ch%s'
                      % (fails, frozen, self.provider, self.ch))
            self._heal_async()

    def _heal_async(self):
        if self._healing.is_set():
            return
        self._healing.set()
        threading.Thread(target=self._heal, daemon=True).start()

    def _heal(self):
        tries = 0
        while self._healing.is_set():
            tries += 1
            url = None
            try:
                url = resolve(self.provider, self.ch)
            except Exception:
                url = None
            if url:
                try:
                    body = _http(url, referer=REFERER_PLAYLIST,
                                 timeout=15).decode('utf-8', 'replace')
                except Exception:
                    body = ''
                if '#EXTM3U' in body:
                    with self._lock:
                        self.upstream_m3u8 = url
                        self.sig_exp = self._sig_of(url)
                    self._poll()
                    self._healing.clear()
                    self._say('HEAL ok after %d tries' % tries)
                    return
            time.sleep(15)

    def _prefetch_loop(self):
        """v2.8.9 delay-watch: pre-download the backlog window so Kodi never
        waits on upstream mid-play. A seg failing prefetch stays retryable via
        Kodi's on-demand fetch; extended upstream freezes are handled by the
        heal thread (same as before)."""
        while True:
            try:
                if self.upstream_m3u8:
                    with self._lock:
                        ledger = list(self.ledger)
                        head = ledger[-1][0] if ledger else -1
                        cut = head
                        acc = 0.0
                        for idx, _u, d in reversed(ledger):
                            if acc + d > self.PLAY_LAG and cut != head:
                                break
                            acc += d
                            cut = idx
                        todo = [(idx, u) for idx, u, _d in ledger
                                if cut <= idx <= head
                                and idx not in self.cache
                                and idx not in self._done]
                    for idx, u in todo:
                        ts = _http(u, timeout=SEG_TIMEOUT)
                        if ts and len(ts) > 4096:
                            with self._lock:
                                self.cache[idx] = ts
                                self._done.add(idx)
                        else:
                            with self._lock:
                                self._done.add(idx)
            except Exception as e:
                self._say('prefetch error %r' % e)
            time.sleep(1.0)

    def _refresh_loop(self):
        while True:
            try:
                if self.upstream_m3u8:
                    self._poll()
                    self._health()
            except Exception as e:
                self._say('loop error %r' % e)
            time.sleep(self.POLL_MIN if self.poll_failures < 3
                       else self.POLL_MIN * 3)


def get_relay():
    """Singleton relay so repeated plays reuse the same server."""
    global _RELAY
    try:
        _RELAY
    except NameError:
        _RELAY = HLSRelay()
    return _RELAY


if __name__ == '__main__':
    b = banner_text()
    print('banner:', b)
    for p, c, _t in FEEDS[:2]:
        u = resolve(p, c)
        print(p, c, 'OK' if u else 'FAIL', (u[:110] if u else ''))