import os, json, time, urllib.request, urllib.parse, ssl, gzip, re

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

for cid in ('60', '537', '274', '577', '273', '38', '449', '554'):
    try:
        tok_url = 'https://edge.wedd48c.top/api/playlist-token?slug=premium%s' % cid
        body = fetch(tok_url, ORIG + '/premiumtv/daddy.php?id=' + cid)
        tok = json.loads(body.decode('utf-8', 'replace')).get('token', '')
        if not tok:
            print(cid, 'no token ->', body[:60]); continue
        man_url = 'https://edge.wedd48c.top/premium%s/index.m3u8?t=%s&_=%d' % (
            cid, tok, int(time.time() * 1000))
        man = fetch(man_url, ORIG + '/premiumtv/daddy.php?id=' + cid)
        ok = b'#EXTM3U' in man
        segs = [l.strip() for l in man.decode('utf-8', 'replace').splitlines()
                if l.strip() and not l.startswith('#')]
        seg_snif = ''
        if segs:
            s = segs[-1]
            surl = s if s.startswith('http') else 'https://edge.wedd48c.top/premium%s/%s' % (cid, s)
            sdata = fetch(surl, ORIG + '/premiumtv/daddy.php?id=' + cid)
            seg_snif = '%dB %s' % (len(sdata), 'TS0x47' if sdata[:1] == b'\x47'
                                   else ('PNG-TIKT' if b'TIKTIKPX' in sdata[:48] else sdata[:8]))
        print(cid, 'OK manifest=%d #EXTM3U=%s segs=%d | lastseg %s' % (len(man), ok, len(segs), seg_snif))
    except Exception as ex:
        print(cid, 'FAIL:', type(ex).__name__, str(ex)[:90])