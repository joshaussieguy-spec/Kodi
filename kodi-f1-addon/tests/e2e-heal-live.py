# Live E2E for v2.8.3 heal: real resolve -> proxy playing -> old edge URLs
# hard-fail (simulating rotation) -> _heal re-resolves on REAL network ->
# LEDGER appends -> playlist continues, sequence never breaks.
import sys, time, types, threading, io

sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\tests')
sys.argv = ['main.py', '0', 'noop']
xbmc = types.ModuleType('xbmc'); xbmc.LOGDEBUG=0; xbmc.LOGINFO=1; xbmc.LOGERROR=4
xbmc.log = lambda *a, **k: None
sys.modules['xbmc'] = xbmc
xbmcadd = types.ModuleType('xbmcaddon')
class _Addon:
    def getAddonInfo(self, k): return {'name': 'f1-e2e'}.get(k, '')
xbmcadd.Addon = _Addon
sys.modules['xbmcaddon'] = xbmcadd
xbmcplug = types.ModuleType('xbmcplugin')
for fn in ('setContent','addDirectoryItem','endOfDirectory','setResolvedUrl'):
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
xbmcgui.NOTIFICATION_ERROR=1; xbmcgui.NOTIFICATION_INFO=0; xbmcgui.NOTIFICATION_WARNING=2
sys.modules['xbmcgui'] = xbmcgui
import f1main
import urllib.request

logs = []
f1main.log = lambda m: logs.append(str(m)) or __import__('builtins').print('LOG: %s' % m)

pr = print
pr('== resolve (real dlive.sx chain) ==')
man, m3u8, hdrs = f1main.resolve_upstream_fresh('60')
pr('manifest %dB, upstream %s' % (len(man), m3u8))

p = f1main.get_unwrap_proxy()
p.channel_id = '60'
p.load_manifest(m3u8, man, hdrs)
if not p.refresher_thread or not p.refresher_thread.is_alive():
    p.refresher_thread = threading.Thread(target=p._refresh_loop, daemon=True)
    p.refresher_thread.start()

with p._lock:
    old_urls = [u for _i, u, _d in p.ledger]
    old_man_url = m3u8
pr('ledger: %d segs, edge=%s' % (len(old_urls), old_urls[0].split('/')[2]))

# baseline: one REAL segment fetch (full PNG-stego unwrap)
ts = p._fetch_unwrap(old_urls[0])
pr('BASELINE SEG OK: %dB 0x47=%s' % (len(ts), ts[:1] == b'\x47'))
assert ts and ts[:1] == b'\x47', 'baseline segment fetch failed'

# now install the kill-switch: the OLD manifest url + OLD segment urls die
kill = set(old_urls) | {old_man_url}
UNKILL_AT = time.time() + 20  # upstream "recovers" after 20s (real rotations end)
real_urlopen = urllib.request.urlopen
def dying_urlopen(req, *a, **kw):
    url = req.full_url if hasattr(req, 'full_url') else str(req)
    if url in kill and time.time() < UNKILL_AT:
        raise urllib.error.URLError('simulated upstream death')
    return real_urlopen(req, *a, **kw)
f1main.urllib.request.urlopen = dying_urlopen

def seq_of(txt):
    for l in txt.splitlines():
        if l.startswith('#EXT-X-MEDIA-SEQUENCE:'):
            return int(l.split(':')[1])
    return -1

seqs = [seq_of(p.refresh_manifest())]
deadline = time.time() + 120
append_seen = healed = False
while time.time() < deadline:
    seqs.append(seq_of(p.refresh_manifest()))
    if any('HEAL: upstream dead' in m for m in logs):
        healed = True
    if any('appended' in m for m in logs):
        append_seen = True
    with p._lock:
        n = len(p.ledger)
        last_u = p.ledger[-1][1] if p.ledger else None
    if append_seen and healed and n > len(old_urls):
        break
    time.sleep(1.0)

# final proof: newest appended segment fetches clean (fresh url, allowed)
with p._lock:
    last = p.ledger[-1]
ts2 = p._fetch_unwrap(last[1])
pr('NEW SEG: %dB 0x47=%s' % (len(ts2) if ts2 else -1, bool(ts2) and ts2[:1] == b'\x47'))

contig = None
with p._lock:
    idxs = [i for i, _u, _d in p.ledger]
    contig = idxs == list(range(idxs[0], idxs[-1] + 1)) if idxs else False
mono = seqs == sorted(seqs)
pr('ledger=%d contiguous=%s seq-monotonic=%s heal=%s append=%s final-seq=%s' %
   (len(p.ledger), contig, mono, healed, append_seen, seqs[-1]))
heal_logs = [m for m in logs if 'HEAL' in m or 'appended' in m][:8]
pr('HEAL-TRAIL: %s' % ' | '.join(heal_logs))
ok = all([healed, append_seen, contig, mono, bool(ts2) and ts2[:1] == b'\x47'])
pr('VERDICT: %s' % ('PASS' if ok else 'FAIL'))
sys.exit(0 if ok else 1)