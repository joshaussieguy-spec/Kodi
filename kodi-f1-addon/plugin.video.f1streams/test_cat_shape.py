import sys, types, json, re
for name in ('xbmc', 'xbmcaddon', 'xbmcvfs', 'xbmcgui', 'xbmcplugin'):
    sys.modules[name] = types.ModuleType(name)
import xbmcaddon
xbmcaddon.Addon = lambda *a, **k: type('A', (), {'getAddonInfo': lambda self, x: 'special://profile/'})()
import xbmc
xbmc.translatePath = lambda p: p.replace('special://', 'C:/Users/Josh/AppData/Local/')
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces_android as fa

# catalog has v1 shape: races[] with title/url only, no 'cats' key.
# scrape_category filters on cats -> 0. Confirm + decide filter behavior:
cat = json.load(open(r'C:\Users\Josh\Kodi\kodi-f1-addon\replay-catalog.json'))
r0 = cat['races'][0]
print('entry keys:', list(r0.keys()))
# Check the title year signal for the 2026 filter:
import collections
years = collections.Counter()
for r in cat['races']:
    m = re.search(r'F1 20\d\d', r['title'])
    years[m.group(0) if m else 'none'] += 1
print('title F1 year counts:', dict(years))