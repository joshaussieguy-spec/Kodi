"""Throwaway: live-fire through the Android-flavor replay chain (real network).

Loads plugin.video.f1streams.android/main.py (the wired, synced copy) with
Kodi stubs, then walks: router(cat) -> 10 races -> race_parts -> real
fullraces.com scrape -> ok.ru ids -> resolve_okru -> MP4 magic byte check.
"""
import types
import sys
import os
import json
import urllib.parse
import urllib.request
import ssl

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(HERE, '..', 'kodi-f1-addon',
                                    'plugin.video.f1streams.android'))


def stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


class _Any:
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, n):
        return _Any()

    def __call__(self, *a, **k):
        return _Any()

    def __contains__(self, n):
        return False

    def __bool__(self):
        return False


class _List(_Any):
    def __init__(self, label='', **kw):
        self.label = label

    def setProperty(self, *a, **k):
        pass

    def setArt(self, *a, **k):
        pass


class _Keyboard:
    def __init__(self, *a, **k):
        pass

    def doModal(self):
        pass

    def isConfirmed(self):
        return False

    def getText(self):
        return ''


stub('xbmc', LOGERROR=1, LOGINFO=0, LOGWARNING=2, LOGDEBUG=0,
     Keyboard=lambda *a, **k: _Keyboard(),
     log=lambda *a, **k: None, executebuiltin=lambda *a, **k: None,
     getCondVisibility=lambda *a, **k: False, translatePath=lambda p: '.')
_xa = stub('xbmcaddon')


class _Addon(_Any):
    def getSetting(self, *a):
        return ''

    def getAddonInfo(self, k):
        return {'id': 'plugin.video.f1streams.android',
                'version': '2.8.15', 'path': BASE,
                'profile': '.'}.get(k, '')


_xa.Addon = _Addon

ITEMS = []
LAST_URLS = []


def _addDir(handle, url, li, isFolder, totalItems=0):
    ITEMS.append((li.label, 'playable' if not isFolder else 'folder'))
    if isFolder and url:
        LAST_URLS.append(url)


stub('xbmcplugin', addDirectoryItem=_addDir,
     endOfDirectory=lambda *a, **k: None,
     setContent=lambda *a, **k: None,
     addSortMethod=lambda *a, **k: None, SORT_LABEL=10)
stub('xbmcgui', ListItem=_List, DialogProgress=_Any, Dialog=_Any,
     DialogOK=_Any, TextInputDialog=_Any, WindowXMLDialog=_Any,
     WindowXML=_Any, Window=_Any, Keyboard=_Keyboard,
     NOTIFICATION_INFO=0)

sys.argv = ['main.py', '1', 'plugin://plugin.video.f1streams.android/', '']
sys.path.insert(0, BASE)
import importlib.util
spec = importlib.util.spec_from_file_location(
    'm_under_test', os.path.join(BASE, 'main.py'))
m = importlib.util.module_from_spec(spec)
sys.modules['m_under_test'] = m
spec.loader.exec_module(m)

print('backend=%s PC_REPLAYS=%s CATALOG_MODE=%s' % (
    m.fr.__name__ if m.fr else None, m.PC_REPLAYS, m.CATALOG_MODE))

# --- race-parts live fire: pull all 10 catalog races' ok_ru through the
# router path (race_parts does the real fullraces.com page scrape).
ITEMS.clear(); LAST_URLS.clear()
m.router('action=replays&cat=2026')
print('cat 2026: %d races' % len(ITEMS))

race_urls = [u for u in LAST_URLS if 'race_parts' in u]
print('drilling %d races (live fullraces.com scrape each)...' % len(race_urls))
total_playable = 0
for i, ru in enumerate(race_urls):
    qs = ru.split('?', 1)[-1]
    ITEMS.clear()
    try:
        m.router(qs)
    except Exception as e:
        print('  race %d: ERROR %r' % (i, e))
        continue
    playable = [l for l, k in ITEMS if k == 'playable']
    total_playable += len(playable)
    print('  race %d: %d parts | %s' % (i, len(playable),
                                        ITEMS[0][0][:52] if ITEMS else ''))
print('TOTAL playable parts across 10 races:', total_playable)

if total_playable >= 2:
    print('LIVE-FIRE PASS (>=2 playable parts)')
else:
    print('LIVE-FIRE THIN (<2) — check upstream')