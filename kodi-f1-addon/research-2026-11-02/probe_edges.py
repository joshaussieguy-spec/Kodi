import os, urllib.request, ssl, gzip

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': '*/*', 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        data = r.read()
    if (r.headers.get('Content-Encoding') or '').lower() == 'gzip':
        data = gzip.decompress(data)
    return data

for cid in ('274', '577', '273', '537', '60'):
    try:
        data = fetch('https://edge.wedd48c.top/premium%s/index.m3u8' % cid,
                     'https://dembed.st/premiumtv/daddy.php?id=' + cid)
        first = data[:20]
        is_m3u8 = b'#EXTM3U' in data
        segs = data.count(b'#EXTINF')
        print(cid, 'manifest:', len(data), 'B | #EXTM3U:', is_m3u8, '| segments:', segs)
        if is_m3u8 and segs:
            # try a real segment pull
            seg = None
            for line in data.decode('utf-8', 'replace').splitlines():
                if line and not line.startswith('#'):
                    seg = line.strip()
                    break
            if seg and seg.startswith('http'):
                surl = seg
            elif seg:
                surl = 'https://edge.wedd48c.top/premium%s/%s' % (cid, seg)
            sdata = fetch(surl, 'https://dembed.st/premiumtv/daddy.php?id=' + cid)
            ok = len(sdata) > 40000 and sdata[:1] == b'\x47'
            print('   seg:', len(sdata), 'B | TS sync 0x47:', sdata[:1] == b'\x47', '| >=40KB:', ok)
    except Exception as ex:
        print(cid, 'FAIL:', type(ex).__name__, str(ex)[:90])