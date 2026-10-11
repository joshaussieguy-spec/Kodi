"""Probe: what does /formula-1 actually return, and what markup holds race links?"""
import sys, re
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

html = fr.fetch_page(fr.BASE_URL + '/formula-1')
print('bytes:', len(html or ''))
if not html:
    sys.exit('FETCH FAILED')

# h3>a pattern?
h3 = re.findall(r'<h3[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>', html)
print('h3>a matches:', len(h3))
for u, t in h3[:5]:
    print('  ', u, '|', t[:60])

# inf_raited blocks?
inf = re.findall(r'class="inf_raited"', html)
print('inf_raited blocks:', len(inf))

# any fullraces.com race-ish hrefs at all
generic = re.findall(r'href="(https?://fullraces\.com/[^"]+)"', html)
uniq = []
for g in generic:
    if g not in uniq:
        uniq.append(g)
print('all uniq fullraces hrefs:', len(uniq))
for u in uniq[:15]:
    print('  ', u)

# dump a chunk around the first race-ish link to see structure
for u in uniq:
    if '/race-' in u or '/watch-' in u:
        i = html.find(u)
        print('--- CONTEXT around first race link ---')
        print(html[max(0, i-400):i+200])
        break