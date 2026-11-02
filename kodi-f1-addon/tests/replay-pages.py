"""Live-fire: Italian GP race page — ok.ru sources (Dailymotion stripped 2026-11-02)."""
import sys, json
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

URL = 'https://fullraces.com/race-f1-2026-italian-grand-prix-full-race-replay-september-6-2026-formula-1'
print('cf lib loaded:', bool(getattr(fr, '_cf_requests', False)))

src = fr.scrape_race_page(URL)
print('title:', src['title'])
print('ok_ru (%d):' % len(src['ok_ru']), src['ok_ru'])
print('filemoon (%d):' % len(src.get('filemoon', [])), src.get('filemoon', []))

ok = (len(src['ok_ru']) >= 2)
print('PARSE CHECK (>=2 ok.ru):', 'PASS' if ok else 'FAIL')

# resolve ok.ru ids
for vid in src['ok_ru']:
    r = fr.resolve_okru(vid)
    print('okru %s ->' % vid, ('PLAYABLE q=%s type=%s' % (r['quality'], r['type'])) if r else 'NONE')