"""Local repro of the 2.8.0 ~15s crash through the rewritten unwrap proxy.

Fake upstream: rotates HLS window like dlive.sx, segments are PNG-stego
(TIKTIKPX -> gzip -> MPEG-TS). Simulated Kodi fetches the playlist every 3s
and every listed segment immediately. Pass = no 502s, valid 188-byte TS
packets, MEDIA-SEQUENCE advances, requests never block >2s.
"""
import sys, os, gzip, zlib, struct, socket, threading, time, io

sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
sys.argv = ['main.py', '0', 'noop']

# ---- Kodi module stubs ----
class _Log:
    LEVELS = {'LOGDEBUG': 0, 'LOGINFO': 1}
def log_stub(msg, level=None):
    pass

import types
xbmc = types.ModuleType('xbmc')
xbmc.LOGDEBUG = 0; xbmc.LOGINFO = 1; xbmc.LOGERROR = 4
xbmc.log = log_stub
sys.modules['xbmc'] = xbmc

xbmcadd = types.ModuleType('xbmcaddon')
class _Addon:
    def getAddonInfo(self, k):
        return {'name': 'f1streams-repro', 'version': 'test'}.get(k, '')
xbmcadd.Addon = _Addon
sys.modules['xbmcaddon'] = xbmcadd

xbmcplug = types.ModuleType('xbmcplugin')
xbmcplug.setContent = lambda *a: None
xbmcplug.addDirectoryItem = lambda *a: None
xbmcplug.endOfDirectory = lambda *a: None
sys.modules['xbmcplugin'] = xbmcplug

xbmcgui = types.ModuleType('xbmcgui')
class _LI:
    def __init__(self, label=None): pass
    def setArt(self, *a): pass
    def setInfo(self, *a): pass
    def setProperty(self, *a): pass
class _Dlg:
    def notification(self, *a): pass
xbmcgui.ListItem = _LI
xbmcgui.Dialog = _Dlg
xbmcgui.NOTIFICATION_ERROR = 1
sys.modules['xbmcgui'] = xbmcgui

import f1main
f1main.log = lambda m, l=0: print('LOG: %s' % m)

# ---- Build PNG-stego segment encoder (mirror of upstream format) ----
def make_ts(sec):
    """One synthetic 188*n-byte TS segment."""
    pkt = bytearray(188)
    pkt[0] = 0x47
    pkt[1] = 0x40  # PUSI
    pkt[3:5] = b'\x00\x00'
    payload = (b'F1SEG%04d|' % sec) * (188 // len(b'F1SEG%04d|') + 1)
    pkt[4:188] = payload[:184]
    return bytes(pkt) * 20  # 20 packets per segment

def make_png(ts_bytes):
    gz = gzip.compress(ts_bytes)
    payload = b'TIKTIKPX' + b'\x00' * 4 + gz + b'\x00' * 32
    w, h, bpp = 512, None, 3
    stride = w * bpp
    h = (len(payload) + stride) // stride + 1
    # rows with filter byte 0
    raw = bytearray()
    pos = 0
    for _ in range(h):
        row = payload[pos:pos + stride]
        pos += stride
        row = row + b'\x00' * (stride - len(row))
        raw += b'\x00' + bytes(row)
    def chunk(typ, data):
        c = struct.pack('>I', len(data)) + typ + data
        return c + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
    ihdr = struct.pack('>IIBB', w, h, 8, 2) + b'\x00\x00\x00'
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(bytes(raw))) + chunk(b'IEND', b'')
    return png

# sanity: addon's own unwrap must decode our fake
_ts = make_png(make_ts(0))
assert f1main._unwrap_png_segment(_ts) == make_ts(0), 'stego roundtrip FAILED'
print('STEGO-ROUNDTRIP-OK')

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

TOTAL_SEGS = 14
SEGS = {i: make_png(make_ts(i)) for i in range(TOTAL_SEGS)}
state = {'head': 3}          # upstream window = last 4 (head-3..head)
lock = threading.Lock()

class Up(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def do_GET(self):
        global lock
        with lock:
            if self.path.startswith('/live/ch60.m3u8'):
                if state['head'] < TOTAL_SEGS - 1:
                    state['head'] += 1
                head = state['head']
                win = range(max(0, head - 3), head + 1)
                man = '#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n'
                seq = max(0, head - 3)
                man += '#EXT-X-MEDIA-SEQUENCE:%d\n' % seq
                for i in win:
                    man += '#EXTINF:6.0,\n/seg/%d.png\n' % i
                body = man.encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith('/seg/'):
                idx = int(self.path[5:].split('.')[0])
                head = state['head']
                if idx > head or idx < head - 40:   # upstream drops old segs
                    self.send_response(404)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                body = SEGS[idx]
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.send_header('Content-Length', '0')
                self.end_headers()
    def log_message(self, *a): pass

upsrv = ThreadingHTTPServer(('127.0.0.1', 0), Up)
up_port = upsrv.server_address[1]
threading.Thread(target=upsrv.serve_forever, daemon=True).start()

UP = 'http://127.0.0.1:%d/live/ch60.m3u8' % up_port
HDRS = {'User-Agent': 'repro', 'Referer': 'http://127.0.0.1:%d/' % up_port}

# ---- Resolve through the addon path ----
man = f1main.fetch_page(UP, HDRS, 15)
assert man and '#EXTM3U' in man, 'fake upstream manifest failed'
proxy = f1main.get_unwrap_proxy()
port = proxy.start() if not proxy.server else proxy.PORT
proxy.load_manifest(UP, man, HDRS)
proxy.refresher_thread = threading.Thread(target=proxy._refresh_loop, daemon=True)
proxy.refresher_thread.start()
local = 'http://127.0.0.1:%d/stream.m3u8' % port
print('RESOLVED local_url=%s upstream=%s' % (local, UP))

# ---- Simulate Kodi playback loop ~30s ----
import urllib.request, urllib.error
ok, fail = 0, 0
fails = []
t0 = time.time()
last_seq = -1
while time.time() - t0 < 30:
    tic = time.time()
    try:
        with urllib.request.urlopen(local + '?r=%d' % int(time.time() * 1000), timeout=3) as r:
            pl = r.read().decode()
    except Exception as e:
        fail += 1; fails.append('PLAYLIST FETCH: %s' % e); break
    if time.time() - tic > 2.0:
        fails.append('PLAYLIST BLOCKED %.2fs' % (time.time() - tic))
    seq = int([l for l in pl.splitlines() if 'MEDIA-SEQUENCE' in l][0].split(':')[1])
    if seq < last_seq:
        fails.append('SEQ WENT BACKWARDS %d < %d' % (seq, last_seq))
    last_seq = seq
    for line in pl.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            idx = int(line.split('/')[2].split('.')[0])
            try:
                with urllib.request.urlopen('http://127.0.0.1:%d%s' % (port, line), timeout=5) as r:
                    ts = r.read()
                assert r.status == 200
                if len(ts) % 188 or ts[:1] != b'\x47':
                    fail += 1; fails.append('BAD TS idx=%d len=%d head=%s' % (idx, len(ts), ts[:4]))
                else:
                    ok += 1
            except urllib.error.HTTPError as e:
                fail += 1; fails.append('502/404 seg %d -> %s' % (idx, e.code))
            except Exception as e:
                fail += 1; fails.append('SEG ERR idx=%d: %s' % (idx, e))
    time.sleep(3)

print('PLAYED %ds: playlist_polls=%d' % (int(time.time() - t0), (30 // 3)))
print('SEGS-OK: %d  SEGS-FAIL: %d' % (ok, fail))
print('FINAL upstream seq: %d' % state['head'])
if fails:
    print('FAILURES:')
    for f in fails[:20]: print('  ' + f)
    print('VERDICT: FAIL')
    sys.exit(1)
print('VERDICT: PASS — window rolled %d segments, proxy held ~%d in ledger, no stalls, no 502s' % (state['head'], len(proxy.ledger)))