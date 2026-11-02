"""Throwaway: Android+PC harness for replay wiring (2.8.15/2.8.18).

Usage: python test_android_menu.py [android|pc]
  android -> loads ../plugin.video.f1streams.android/main.py (synced copy)
  pc      -> loads ../plugin.video.f1streams/main.py with exe assumed present
"""
import types, sys, os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WHICH = sys.argv[1] if len(sys.argv) > 1 else 'android'
BASE = os.path.abspath(os.path.join(HERE, '..', 'plugin.video.f1streams'
                                    if WHICH == 'pc' else
                                    'plugin.video.f1streams.android'))

def stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

class _Any:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return _Any()
    def __call__(self, *a, **k): return _Any()
    def get(self, *a, **k): return ''
    def __contains__(self, n): return False
    def __bool__(self): return False

class _List(_Any):
    def __init__(self, label='', **kw): self.label = label
    def setProperty(self, *a, **k): pass
    def setArt(self, *a, **k): pass

class _Keyboard:
    def __init__(self, *a, **k): pass
    def doModal(self): pass
    def isConfirmed(self): return False   # skip search in headless run
    def getText(self): return ''

stub('xbmc', LOGERROR=1, LOGINFO=0, LOGWARNING=2, LOGDEBUG=0,
     Keyboard=lambda *a, **k: _Keyboard(),
     log=lambda *a, **k: None, executebuiltin=lambda *a, **k: None,
     getCondVisibility=lambda *a, **k: False, translatePath=lambda p: '.')
_xa = stub('xbmcaddon')

class _Addon(_Any):
    def getSetting(self, *a): return ''
    def getAddonInfo(self, k): return {
        'id': ('plugin.video.f1streams' if WHICH == 'pc' else
               'plugin.video.f1streams.android'),
        'version': '2.8.18' if WHICH == 'pc' else '2.8.15',
        'path': BASE, 'profile': '.'}.get(k, '')

_xa.Addon = _Addon
ITEMS = []
RESOLVED = []

def _addDir(handle, url, li, isFolder, totalItems=0):
    ITEMS.append((li.label, 'playable' if not isFolder else 'folder'))
    if isFolder and url:
        LAST_URLS.append(url)

LAST_URLS = []
stub('xbmcplugin', addDirectoryItem=_addDir,
     endOfDirectory=lambda *a, **k: None, setContent=lambda *a, **k: None,
     addSortMethod=lambda *a, **k: None, SORT_LABEL=10)
stub('xbmcgui', ListItem=_List, DialogProgress=_Any, Dialog=_Any,
     DialogOK=_Any, TextInputDialog=_Any, WindowXMLDialog=_Any,
     WindowXML=_Any, Window=_Any, Keyboard=_Keyboard,
     NOTIFICATION_INFO=0)

sys.argv = ['main.py', '1',
            'plugin://plugin.video.f1streams'
            + ('' if WHICH == 'pc' else '.android') + '/', '']
sys.path.insert(0, BASE)
spec = importlib.util.spec_from_file_location(
    'm_under_test', os.path.join(BASE, 'main.py'))
m = importlib.util.module_from_spec(spec)
sys.modules['m_under_test'] = m
spec.loader.exec_module(m)

print('== %s ==' % WHICH)
print('PC_REPLAYS=%s CATALOG_MODE=%s backend=%s' %
      (m.PC_REPLAYS, m.CATALOG_MODE,
       m.fr.__name__ if m.fr else None))

print('--- main menu (%d items) ---' % len(ITEMS if False else []))
ITEMS.clear(); LAST_URLS.clear()
m.show_main_menu()
for lbl, kind in ITEMS:
    print(kind, '|', lbl[:60])

def drill(qs):
    ITEMS.clear(); LAST_URLS.clear()
    m.router(qs)
    return ITEMS

# 1. into first replay category
cat_url = next((u for u in LAST_URLS if 'action=replays&' in u), None)
if cat_url:
    qs = cat_url.split('?', 1)[-1]
    print('--- cat:', qs[:60])
    drill(qs)
    print('   %d races' % len(ITEMS))
    for lbl, kind in ITEMS[:3]:
        print('  ', kind, '|', lbl[:70])

    # 2. into first race -> parts
    race_url = next((u for u in LAST_URLS if 'race_parts' in u), None)
    if race_url:
        qs = race_url.split('?', 1)[-1]
        print('--- parts:', qs[:70])
        drill(qs)
        for lbl, kind in ITEMS:
            print('  ', kind, '|', lbl[:78])

        # 3. resolve ok.ru playable
        play = next((u for u in LAST_URLS if 'play_okru' in u), None)
        if play:
            qs = play.split('?', 1)[-1]
            print('--- resolve:', qs[:70])
            drill(qs)
            for r in RESOLVED:
                print('   RESOLVED:', r[:90])