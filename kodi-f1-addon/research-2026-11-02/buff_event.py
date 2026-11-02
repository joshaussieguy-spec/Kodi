import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref='https://buffstreams24.org/'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.geturl(), r.read().decode('utf-8', 'replace')

# the per-event page: watch-f1-abu-dhabi... — check what it embeds
redir, h = fetch('https://buffstreams24.org/stream/watch-f1-abu-dhabi-grand-prix-vs-live-stream-online-free-today')
print('event page bytes:', len(h), '| url:', redir)
iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', h, re.I)
print('iframes:', iframes[:6])
# any JS var with stream source
for pat in (r'source\s*[:=]\s*["\']([^"\']+)["\']', r'data-src="([^"]+)"', r'(https?://[^"\' ]*embed[^"\' ]*)'):
    hits = re.findall(pat, h, re.I)[:6]
    print(pat[:24], '->', hits)
ext = sorted(set(re.findall(r'https?://([a-z0-9.-]{4,40})/', h)))[:25]
print('external hosts:', ext)