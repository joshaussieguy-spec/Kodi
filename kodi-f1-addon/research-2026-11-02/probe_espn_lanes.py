import os, json, time, urllib.request, ssl, gzip

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ORIG = 'https://dembed.st'

def fetch(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                               'Origin': ORIG, 'Referer': ref,
                                               'Accept-Encoding': 'gzip',
                                               'Sec-Fetch-Dest': 'empty',
                                               'Sec-Fetch-Mode': 'cors',
                                               'Sec-Fetch-Site': 'cross-site'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        data = r.read()
    if (r.headers.get('Content-Encoding') or '').lower() == 'gzip':
        data = gzip.decompress(data)
    return data

def html(url, ref='https://dlive.sx/'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

import re
for cid in ('424', '44', '81', '925'):
    try:
        w = html('https://dlive.sx/watch.php?id=' + cid)
        m = re.search(r'<iframe[^>]+src="(https?://[^"]*stream-\d+\.php[^"]*)"', w)
        if not m:
            print(cid, 'no stream iframe'); continue
        p = html(m.group(1), 'https://dlive.sx/')
        m2 = re.search(r'<iframe[^>]+src="([^"]+)"', p)
        if not m2 or 'dembed.st' not in m2.group(1):
            print(cid, 'OTHER embed:', (m2.group(1) if m2 else 'none')[:80]); continue
        em = re.search(r'id=(\d+)', m2.group(1))
        ecid = em.group(1)
        e = fetch.__wrapped__ if False else html('https://dembed.st/premiumtv/daddy.php?id=' + ecid, 'https://dlive.sx/')
        src = re.search(r'const\s+SRC\s*=\s*["\']([^"\']+m3u8[^"\']*)["\']', e)
        if not src:
            print(cid, 'no SRC'); continue
        surl = src.group(1)
        slug = urllib.parse.urlparse(surl).path.strip('/').split('/')[0]
        body = fetch('https://edge.wedd48c.top/api/playlist-token?slug=%s' % slug, ORIG + '/premiumtv/daddy.php?id=' + ecid)
        tok = json.loads(body.decode()).get('token', '')
        man = fetch(surl + '?t=%s&_=%d' % (tok, int(time.time() * 1000)), ORIG + '/premiumtv/daddy.php?id=' + ecid) if tok else b''
        segs = [l.strip() for l in man.decode('utf-8', 'replace').splitlines() if l.strip() and not l.startswith('#')]
        seg_b = b''
        if segs:
            s = segs[-1]
            su = s if s.startswith('http') else 'https://edge.wedd48c.top/%s/%s' % (slug, s)
            seg_b = fetch(su, ORIG + '/premiumtv/daddy.php?id=' + ecid)
        print(cid, 'OK slug=%s manifest=%dB segs=%d segSNIF=%s' % (
            slug, len(man), len(segs),
            ('%dB %s' % (len(seg_b), seg_b[:1] == b'\x47' and 'TS0x47' or ('TIKT' if b'TIKTIKPX' in seg_b[:48] else repr(seg_b[:8])))) if seg_b else '-'))
    except Exception as ex:
        print(cid, 'FAIL:', type(ex).__name__, str(ex)[:80])