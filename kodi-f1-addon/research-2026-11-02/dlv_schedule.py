import os, json, time, urllib.request, urllib.parse, ssl, gzip, re

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ORIG = 'https://dembed.st'

def txt(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        d = r.read()
    if (r.headers.get('Content-Encoding') or '').lower() == 'gzip':
        d = gzip.decompress(d)
    return d.decode('utf-8', 'replace')

def fetch(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                               'Origin': ORIG, 'Referer': ref,
                                               'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        d = r.read()
    if (r.headers.get('Content-Encoding') or '').lower() == 'gzip':
        d = gzip.decompress(d)
    return d

try:
    h = txt('https://dlive.sx/schedule.php?cat=f1', 'https://dlive.sx/')
    rows = re.findall(r'href="(/schedule\.php\?id=\d+[^"]*|/watch\.php\?id=\d+)"[^>]*>([^<]{3,80})<', h)
    print('schedule rows:', len(rows))
    for u, t in rows[:20]:
        print(' ', u, '|', t.strip())
except Exception as ex:
    print('schedule cat=f1 FAIL:', type(ex).__name__, str(ex)[:100])

# generic schedule fallback
try:
    h2 = txt('https://dlive.sx/schedule.php', 'https://dlive.sx/')
    f1s = [seg for seg in re.split(r'<tr', h2) if re.search(r'formula|f1\b|grand prix', seg, re.I)]
    print('generic schedule: f1-ish rows', len(f1s))
    for seg in f1s[:6]:
        m = re.search(r'href="([^"]+)[^>]*>([^<]+)<', seg)
        if m:
            print(' ', m.group(1), '|', m.group(2).strip()[:60])
except Exception as ex:
    print('schedule generic FAIL:', type(ex).__name__, str(ex)[:100])