"""Live-fire test: new multi-host parser vs real Italian GP race page."""
import sys, json
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

print('cf lib loaded:', getattr(fr, '_cf_requests', False))

# 1. Category listing -> newest races (current URLs, not stale ones)

# 2. F1 2026 season listing -> newest races (the /formula-1 slug is dead 404)
races = fr.scrape_category('2026')
print('f1 races found:', len(races))
if not races:
    sys.exit('NO RACES PARSED — investigate')

# 3. Pick the newest race page and scrape all hosts
target = races[0]
print('TARGET:', target['title'], '->', target['url'])
src = fr.scrape_race_page(target['url'])
print('title:', src['title'])
print('ok_ru ids (%d):' % len(src['ok_ru']), src['ok_ru'])
print('dailymotion parts (%d):' % len(src['dailymotion']), json.dumps(src['dailymotion']))
print('filemoon (%d):' % len(src['filemoon']), src['filemoon'])

ok = (len(src['ok_ru']) >= 2 and len(src['dailymotion']) >= 5)
print('PARSE CHECK (>=2 ok.ru, >=5 DM parts):', 'PASS' if ok else 'FAIL')

# 4. Resolve each ok.ru id -> playable?
for vid in src['ok_ru']:
    r = fr.resolve_okru(vid)
    print('okru %s ->' % vid, ('PLAYABLE q=%s type=%s url_ok=%s' % (r['quality'], r['type'], r['url'][:40] + '...')) if r else 'NONE')

# 5. Resolve one DM part
if src['dailymotion']:
    dm = src['dailymotion'][0]
    r = fr.resolve_dailymotion(dm['id'])
    print('dm %s ->' % dm['id'], (r or {}).get('type', 'NONE'), (r or {}).get('url', '')[:50])
    print('DM CHECK:', 'PASS' if r and r.get('url') else 'FAIL')