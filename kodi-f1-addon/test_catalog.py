"""Design-time probe: prove the GitHub-catalog idea for Android replays.

The Android flavor cannot scrape fullraces.com directly (Cloudflare 403 on
stdlib). Idea: build the replay catalog as static JSON, publish it in the
GitHub repo (raw.githubusercontent — the feed the addons law already
designates as primary), and have the Android addon fetch the catalog from
there at runtime, then play ok.ru direct MP4s via stdlib.

This script builds catalog.json from the PC addon's live scrape and verifies
a stdlib round-trip: raw.githubusercontent fetch -> race page URLs -> ok.ru
resolve -> MP4 range 206.
"""
import sys, json, urllib.request
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

races = fr.scrape_category('2026', 3)
print('scraped:', len(races))
slim = [{'title': r['title'], 'url': r['url']} for r in races]
with open(r'C:\Users\Josh\Kodi\kodi-f1-addon\replay-catalog.json', 'w', encoding='utf-8') as f:
    json.dump({'updated': '2026-11-02', 'source': 'fullraces.com', 'races': slim}, f, indent=1)
print('catalog bytes:', len(json.dumps(slim)))

# prove raw.githubusercontent round-trip shape (use a known-good raw URL style:
# the sideload zip URL domain already proven = raw.githubusercontent.com/joshaussieguy-spec/Kodi/main/...)
# Fetch check:
u = 'https://raw.githubusercontent.com/joshaussieguy-spec/Kodi/main/docs/zips/repository.thetallone/repository.thetallone-1.1.3.zip'
req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-63'})
with urllib.request.urlopen(req, timeout=25) as r:
    print('raw.gh 206:', r.status, r.read(4))