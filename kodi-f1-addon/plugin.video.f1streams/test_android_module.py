import sys, types, json, re
# stub xbmc family BEFORE the import
for name in ('xbmc', 'xbmcaddon', 'xbmcvfs', 'xbmcgui', 'xbmcplugin'):
    m = types.ModuleType(name)
    sys.modules[name] = m
import xbmcaddon
xbmcaddon.Addon = lambda *a, **k: type('A', (), {'getAddonInfo': lambda self, x: 'special://profile/'})()
import xbmc
xbmc.translatePath = lambda p: p.replace('special://', 'C:/Users/Josh/AppData/Local/')
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces_android as fa

# 1. category listing via catalog (simulates GH-loaded JSON)
races = fa.scrape_category('2026', 1)
print('category races:', len(races))
first = races[0] if races else None
print('first:', (first or {}).get('title', '?')[:70])

# 2. the catalog race -> tier1 needs ok_ru — our catalog v1 only has title/url.
# So resolve directly: mimic what show_race_parts would do on a v2 catalog.
# For the LIVE test, use the known Mexico GP ok id and full pipeline:
res = fa.resolve_okru('16714114796204')
print('resolve_okru:', (res or {}).get('quality'), (res or {}).get('type'))
print('url head:', (res or {}).get('url', 'NONE')[:80])

# 3. MP4 range through stdlib (what Kodi player will do)
import urllib.request
r2 = urllib.request.Request(res['url'], headers={'User-Agent': 'Kodi/20.5 (Windows; Windows 10 2004) Kodi/20.5', 'Range': 'bytes=0-31'})
with urllib.request.urlopen(r2, timeout=25) as resp:
    print('MP4:', resp.status, resp.read(32))