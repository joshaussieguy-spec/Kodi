# Offline heal drill: upstream manifest dies mid-play -> HEAL triggers ->
# resolve chain re-run (stubbed) -> fresh segments APPEND with contiguous
# indices -> MEDIA-SEQUENCE never goes backwards. No real network.
import sys, time, threading, types, io
sys.path.insert(0, '.')
sys.argv = ['main.py', '0', 'noop']

# Kodi module stubs (same block as resolve-deadhost.py)
xbmc = types.ModuleType('xbmc'); xbmc.LOGDEBUG = 0; xbmc.LOGINFO = 1; xbmc.LOGERROR = 4
xbmc.log = lambda *a, **k: None
sys.modules['xbmc'] = xbmc
xbmcadd = types.ModuleType('xbmcaddon')
class _Addon:
    def getAddonInfo(self, k): return {'name': 'f1-heal-test'}.get(k, '')
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

captured = []
f1main.log = lambda m: (captured.append(str(m)), __import__('builtins').print('LOG: %s' % m))[0] is None

# --- stub the network layer --------------------------------------------
real_urlopen = f1main.urllib.request.urlopen
OLD_MAN = '#EXTM3U\n#EXT-X-TARGETDURATION:4\n'
OLD_SEGS = ['https://oldedge.sbs/live.s%02d.ts' % i for i in range(5)]
NEW_HOST = 'https://newedge.live/'

def stub_urlopen(req, timeout=None, context=None, **kw):
    url = req.full_url if hasattr(req, 'full_url') else str(req)
    if url.startswith('https://oldedge.sbs/live.m3u8'):
        raise f1main.urllib.error.URLError('upstream gone')   # old manifest DEAD
    if url == NEW_HOST + 'fresh.m3u8':
        # manifest alive: latest window has seen segs + one brand new one
        body = OLD_MAN + ''.join('#EXTINF:4.0,\n%s\n' % (NEW_HOST + 'f%02d.ts' % i) for i in range(6))
        import io as _io
        return _io.BytesIO(body.encode())
    raise f1main.urllib.error.URLError('stub: unhandled %s' % url[:60])

f1main.urllib.request.urlopen = stub_urlopen

# stub resolve chain: heals with manifest on the NEW host
fresh_man = OLD_MAN + ''.join('#EXTINF:4.0,\n%s\n' % (NEW_HOST + 'f%02d.ts' % i) for i in range(5))
def fake_resolve(cid):
    assert cid == '60', 'healer must re-resolve with the SAME channel id'
    time.sleep(1.0)  # heal takes measurable time, proves it's background
    return fresh_man, NEW_HOST + 'fresh.m3u8', {'User-Agent': 'UA', 'Referer': 'https://x/'}
f1main.resolve_upstream_fresh, real_resolve = fake_resolve, f1main.resolve_upstream_fresh

# --- run ----------------------------------------------------------------
old_man = OLD_MAN + ''.join('#EXTINF:4.0,\n%s\n' % u for u in OLD_SEGS)
p = f1main.get_unwrap_proxy()
p.channel_id = '60'
p.load_manifest('https://oldedge.sbs/live.m3u8', old_man, {'User-Agent': 'UA'})
if not p.refresher_thread or not p.refresher_thread.is_alive():
    p.refresher_thread = threading.Thread(target=p._refresh_loop, daemon=True)
    p.refresher_thread.start()

def window_seq():
    txt = p.refresh_manifest()
    for line in txt.splitlines():
        if line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
            return int(line.split(':')[1])
    return -1

seqs, deadline = [], time.time() + 40
while time.time() < deadline:
    seqs.append(window_seq())
    txt = p.refresh_manifest()
    if any('newedge' in l for l in txt.splitlines() if l and not l.startswith('#')):
        break
    time.sleep(0.5)

with p._lock:
    n = len(p.ledger); idxs = [i for i, _u, _d in p.ledger]
    has_new = any('newedge' in u for _i, u, _d in p.ledger)
healed = any('HEAL: upstream dead' in m for m in captured)
swapped = any('appended' in m for m in captured)
contig = idxs == list(range(len(idxs)))
monotonic = seqs == sorted(seqs)

print2 = __import__('builtins').print
print2('%s' % ('PASS' if all([healed, swapped, has_new, contig, monotonic]) else 'FAIL'))
print2('heal-logged=%s append-logged=%s new-segs=%s contiguous=%s seq-monotonic=%s' % (healed, swapped, has_new, contig, monotonic))
print2('ledger=%d indices=%s last-seq=%s' % (n, (idxs[0], idxs[-1]) if idxs else None, seqs[-1] if seqs else None))
sys.exit(0 if all([healed, swapped, has_new, contig, monotonic]) else 1)