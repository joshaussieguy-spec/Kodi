import sys, types, os, json
for name in ('xbmc', 'xbmcaddon', 'xbmcvfs', 'xbmcgui', 'xbmcplugin'):
    sys.modules[name] = types.ModuleType(name)
import xbmcaddon
_addon = type('A', (), {'getAddonInfo': lambda self, x: 'special://profile/'})()
xbmcaddon.Addon = lambda *a, **k: _addon
import xbmcvfs
# map special:// back to a real dir so the cache read/write hits a real path
HOME = os.environ['USERPROFILE']
PROFILE = os.path.join(HOME, 'AppData', 'Roaming', 'Kodi', 'userdata', 'addon_data', 'plugin.video.f1streams')
os.makedirs(PROFILE, exist_ok=True)
xbmcvfs.translatePath = lambda p: p.replace('special://profile/', PROFILE + os.sep).replace('special://', PROFILE + os.sep)
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces_android as fa

data = fa._catalog.load(fresh=True)
print('fresh GH load keys:', list(data.keys()), 'races:', len(data.get('races', [])))
races = fa.scrape_category('2026')
print('category 2026:', len(races))
for r in races[:3]:
    print(' -', r['title'][:60])
e = fa._catalog.entry_for_url(races[0]['url'])
print('entry ok_ru:', (e or {}).get('ok_ru'))
page = fa.scrape_race_page(races[0]['url'])
print('race page ok_ru:', page.get('ok_ru'), '| title:', page['title'][:50])
res = fa.resolve_okru(page['ok_ru'][0])
print('resolved:', (res or {}).get('type'), (res or {}).get('quality'))