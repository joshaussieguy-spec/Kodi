"""Offline drill: embed host dies (dembed.top scenario), fallback host walk
must still resolve. Monkeypatches fetch_page; no real network except the
local unwrap proxy on 127.0.0.1."""
import sys, os, types

sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\tests')
sys.argv = ['main.py', '0', 'noop']

# Kodi module stubs (same as repro_15s.py)
xbmc = types.ModuleType('xbmc'); xbmc.LOGDEBUG = 0; xbmc.LOGINFO = 1; xbmc.LOGERROR = 4
xbmc.log = lambda *a, **k: None
sys.modules['xbmc'] = xbmc
xbmcadd = types.ModuleType('xbmcaddon')
class _Addon:
    def getAddonInfo(self, k): return {'name': 'f1-deadhost-test'}.get(k, '')
xbmcadd.Addon = _Addon
sys.modules['xbmcaddon'] = xbmcadd
xbmcplug = types.ModuleType('xbmcplugin')
for fn in ('setContent', 'addDirectoryItem', 'endOfDirectory', 'setResolvedUrl'):
    setattr(xbmcplug, fn, lambda *a, **k: None)
sys.modules['xbmcplugin'] = xbmcplug
xbmcgui = types.ModuleType('xbmcgui')
class _LI:
    def __init__(self, label=None): pass
    def setArt(self, *a): pass
    def setInfo(self, *a): pass
    def setProperty(self, *a): pass
class _Dlg:
    def notification(self, *a): pass
xbmcgui.ListItem = _LI; xbmcgui.Dialog = _Dlg
xbmcgui.NOTIFICATION_ERROR = 1; xbmcgui.NOTIFICATION_INFO = 0
xbmcgui.NOTIFICATION_WARNING = 2
sys.modules['xbmcgui'] = xbmcgui

import f1main
logs = []
f1main.log = lambda m, l=0: (logs.append(m), print('LOG: %s' % m))

# ---- Fake pages ----
WATCH = '<iframe src="https://dlive.sx/stream/stream-60.php"></iframe>'
STREAM = '<iframe src="https://dembed.top/premiumtv/daddy.php?id=60"></iframe>'
PLAYER = '<script>const SRC = "https://edge.cowedd4855ws.sbs/premium60/index.m3u8";</script>'
MANIFEST = '#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6.0,\nseg1.png\n#EXTINF:6.0,\nseg2.png\n'

FETCHED = []
def fake_fetch(url, headers=None, timeout=20):
    FETCHED.append(url)
    if 'watch.php?id=60' in url: return WATCH
    if 'stream-60.php' in url: return STREAM
    if 'dembed.top' in url:
        return None            # <- DNS death, exactly like tonight
    if 'daddyliveplayer.st' in url: return PLAYER
    if url.endswith('index.m3u8'): return MANIFEST
    return None
f1main.fetch_page = fake_fetch

url = f1main.resolve_live_stream('60')
print()
print('candidates tried:', [u for u in FETCHED if 'daddy.php' in u])
assert url and url.startswith('http://127.0.0.1:'), 'FAIL: no local url'
assert any('dembed.top' in u for u in FETCHED), 'FAIL: never tried dead page host'
assert any('daddyliveplayer.st' in u for u in FETCHED), 'FAIL: never walked fallback'
print('RESOLVED:', url)
print('VERDICT: PASS — dead embed host skipped, fallback walked, proxy started')