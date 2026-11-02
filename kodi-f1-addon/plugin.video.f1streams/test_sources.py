"""Throwaway: inspect fullraces.com race-page button layout (order/labels of hosts)."""
import sys, re
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

races = fr.scrape_category('2026')
print('races:', len(races))

for race in races[:3]:
    url = race['url']
    print('\n=== RACE:', race['title'], url)
    html = None
    for fn in ('fetch_page', '_exe_fetch'):
        try:
            html = getattr(fr, fn)(url)
        except Exception as e:
            print(fn, 'failed:', e)
        if html:
            break
    if not html:
        print('no html'); continue
    text = html.decode('utf-8', 'replace') if isinstance(html, bytes) else html
    print('html bytes:', len(text))
    btns = re.findall(r'<a[^>]*class="[^"]*su-button[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                      text, re.DOTALL)
    for i, (href, label) in enumerate(btns[:40]):
        label = re.sub(r'<[^>]+>', '', label).strip()[:48]
        h = ('dm' if 'dailymotion' in href else
             'ok' if 'ok.ru' in href else
             'fm' if 'filemoon' in href else '?')
        print('%2d %-2s %-48s | %s' % (i, h, label, href[:80]))
    for m in re.finditer(r'[Oo]ption\s*\d', text):
        ctx = text[max(0, m.start()-80):m.end()+60].replace('\n', ' ')
        ctx = re.sub(r'\s+', ' ', ctx)
        print('OPT-CTX:', ctx[:150])