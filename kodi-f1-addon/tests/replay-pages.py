"""Live-fire: Italian GP race page — the 7-source page (DM parts 1-5, 2x ok.ru, Filemoon)."""
import sys, json
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

URL = 'https://fullraces.com/race-f1-2026-italian-grand-prix-full-race-replay-september-6-2026-formula-1'
print('cf lib loaded:', bool(getattr(fr, '_cf_requests', False)))

src = fr.scrape_race_page(URL)
print('title:', src['title'])
print('ok_ru (%d):' % len(src['ok_ru']), src['ok_ru'])
print('dailymotion (%d):' % len(src['dailymotion']), json.dumps(src['dailymotion']))
print('filemoon (%d):' % len(src['filemoon']), src['filemoon'])

ok = (len(src['ok_ru']) >= 2 and len(src['dailymotion']) >= 5)
print('PARSE CHECK (>=2 ok.ru, >=5 DM parts):', 'PASS' if ok else 'FAIL')

# resolve both ok.ru ids
for vid in src['ok_ru']:
    r = fr.resolve_okru(vid)
    print('okru %s ->' % vid, ('PLAYABLE q=%s type=%s' % (r['quality'], r['type'])) if r else 'NONE')

# resolve one DM part
if src['dailymotion']:
    dm = src['dailymotion'][0]
    r = fr.resolve_dailymotion(dm['id'])
    print('dm %s (%s) ->' % (dm['id'], dm['label']),
          ('%s %s...' % (r.get('type'), r.get('url', '')[:45])) if r else 'NONE')