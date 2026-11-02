import sys, types, json
for name in ('xbmc', 'xbmcaddon', 'xbmcvfs', 'xbmcgui', 'xbmcplugin'):
    sys.modules[name] = types.ModuleType(name)
import xbmcaddon
xbmcaddon.Addon = lambda *a, **k: type('A', (), {'getAddonInfo': lambda self, x: 'special://profile/'})()
import xbmc
xbmc.translatePath = lambda p: p.replace('special://', 'C:/Users/Josh/AppData/Local/')
import os
# point the cache at a file that does NOT exist locally (it would cache from GH URL fetch fail path)
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces_android as fa
print('CATALOG_URL:', fa.CATALOG_URL)
try:
    data = fa._catalog.load(fresh=True)
    print('GH catalog load keys:', list(data.keys()))
    print('GH races:', len(data.get('races', [])))
    races = fa.scrape_category('2026')
    print('category via real GH fetch:', len(races))
    if races:
        print('first:', races[0]['title'][:70])
except Exception as e:
    print('FAIL:', type(e).__name__, str(e)[:300])