"""v2.8.20 functional test: catalog normalization + no-scrape fallthrough.
Runs the REAL lookup from the shipped module (no xbmc import needed)."""
import sys, os, io, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(HERE, '..', 'plugin.video.f1streams'))
import fullraces_android as fa

# Point the catalog at the real repo file (standalone: no xbmcvfs available)
fa._catalog._data = json.load(open(os.path.join(HERE, '..', 'replay-catalog.json'),
                                   encoding='utf-8'))

url0 = fa._catalog._data['races'][0]['url']
print('entry0 url:', url0[:70])

# 1. exact match
e = fa._catalog.entry_for_url(url0)
print('exact match:', bool(e))

# 2. near-miss variants that phones produce
u = url0
for fn in (lambda x: x.replace('https://', 'http://'),
           lambda x: x + '/',
           lambda x: x.split('//', 1)[1].upper(),
           lambda x: x + '?utm_source=phone'):
    e = fa._catalog.entry_for_url(fn(u))
    print('variant match:', bool(e), '<-', fn(u)[:60])

# 3. unknown URL -> entry None (callers must NOT scrape; main.py shows clean message)
e = fa._catalog.entry_for_url('https://fullraces.com/some/new/race/')
print('unknown -> None:', e is None)

# 4. known-good catalog race still resolves via scrape_race_page (no exception)
info = fa.scrape_race_page(url0)
print('race page ok_ru count:', len(info.get('ok_ru', [])), '| title:', info.get('title', '')[:40])