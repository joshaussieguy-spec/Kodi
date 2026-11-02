"""Live-fire 2.8.19: resolve the 3 new dlive lanes through the REAL addon
code path (resolve_upstream_fresh + unwrap-proxy manifest), offline-safe."""
import os, sys, importlib, types

# Fake the xbmc modules so main.py imports cleanly outside Kodi (same trick
# the existing test harness uses).
xbmc = types.ModuleType('xbmc'); xbmc.LOGDEBUG = 4
def _logstub(*a, **k): pass
xbmc.log = _logstub
class _Addon:
    def __init__(self, *a, **k): self.id = 'plugin.video.f1streams'
    def getAddonInfo(self, name):
        return {'id': 'plugin.video.f1streams', 'name': 'F1 Streams',
                'path': os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     '..', 'plugin.video.f1streams'),
                'version': '2.8.19-test'}.get(name, '')
    def getSetting(self, *a, **k): return ''
xbmcaddon = types.ModuleType('xbmcaddon'); xbmcaddon.Addon = _Addon
xbmcgui = types.ModuleType('xbmcgui')
xc = types.ModuleType('xbmcplugin')
sys.modules['xbmc'] = xbmc; sys.modules['xbmcaddon'] = xbmcaddon
sys.modules['xbmcgui'] = xbmcgui
sys.modules['xbmcplugin'] = xc

sys.argv = ['plugin://plugin.video.f1streams/', '1', '?action=live']
ADDON_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         '..', 'plugin.video.f1streams'))
sys.path.insert(0, ADDON_DIR)
import main  # noqa: E402

lanes = ['38', '449', '424', '60']
print('CHANNELS:', [(c['id'], c['title'][:34]) for c in main.CHANNELS])
for cid in lanes:
    try:
        man, up, segs = main.resolve_upstream_fresh(cid)
        print('ch%-4s MANIFEST ok  segs=%-3d upstream=%s' % (cid, len(segs), up[:64]))
    except Exception as e:
        print('ch%-4s FAIL %r' % (cid, e))