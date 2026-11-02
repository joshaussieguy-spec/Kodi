"""Throwaway 2: where do ok.ru ids live on a race page (full source-order dump)?"""
import sys, re
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

url = 'https://fullraces.com/race-f1-2026-mexico-city-grand-prix-full-race-replay-november-1-2026-formula-1'
html = fr.fetch_page(url)
text = html.decode('utf-8', 'replace') if isinstance(html, bytes) else html
print('bytes:', len(text))

# Every host mention in source order
pat = re.compile(r'.{90}(ok\.ru|video\.ok\.ru|dailymotion\.com|bysesukior\.com|vidara\.to|g8w90qhngo\.com|filemoon).{60}', re.DOTALL)
seen = []
for m in pat.finditer(text):
    ctx = re.sub(r'\s+', ' ', m.group(0))
    seen.append((m.start(), m.group(1), ctx))
print('total host mentions:', len(seen))
for off, host, ctx in seen[:25]:
    print('%6d %-22s %s' % (off, host, ctx[:180]))

# Also: how scrape_race_page finds ok_ru
print('\n--- ok_ru regex in fullraces.py ---')
import inspect, fullraces
src = inspect.getsource(fullraces.scrape_race_page)
for line in src.splitlines():
    if 'ok' in line.lower() and ('re.' in line or 'finditer' in line or 'ok_ru' in line):
        print(line.strip()[:160])