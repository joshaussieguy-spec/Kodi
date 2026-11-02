import sys, json, re, html as H, urllib.request, gzip, io
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

# Get the full-quality URL and inspect what query params it carries
raw = fr.fetch_page('https://ok.ru/video/16714114796204')
m = re.search(r'data-options="([^"]+)"', raw)
data = json.loads(H.unescape(m.group(1)))
md = data.get('flashvars', {}).get('metadata', '')
md = json.loads(md) if isinstance(md, str) else md
full = [v for v in md.get('videos', []) if v.get('name') == 'full'][0]
u = full['url']
print('URL len:', len(u))
qs = u.split('?', 1)[1] if '?' in u else ''
pairs = [p.split('=')[0] for p in qs.split('&')]
print('params:', pairs)
# the urls= param holds the actual CDN endpoint, URL-encoded
um = re.search(r'urls=([^&]+)', qs)
if um:
    import urllib.parse as UP
    decoded = UP.unquote(um.group(1))
    print('urls param ->', decoded[:120])
# Try a HEAD-style range fetch on the FULL url with browser-ish headers incl cookie jar semantics
req = urllib.request.Request(u, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126',
    'Referer': 'https://ok.ru/',
    'Accept': '*/*',
    'Range': 'bytes=0-1023',
})
try:
    resp = urllib.request.urlopen(req, timeout=25)
    print('RANGE OK HTTP', resp.status, 'ct:', resp.headers.get('Content-Type'))
except Exception as e:
    print('RANGE FAIL:', e)
# maybe the URL needs to be hit WITHOUT the referer (vkuser CDN sometimes 400s foreign referers)
req2 = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126'})
try:
    resp2 = urllib.request.urlopen(req2, timeout=25)
    d = resp2.read(150000)
    print('NO-REF OK HTTP', resp2.status, 'bytes', len(d), d[:50])
except Exception as e:
    print('NO-REF FAIL:', e)