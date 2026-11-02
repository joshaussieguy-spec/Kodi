import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref='https://dlive.sx/'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

for cid in ('38', '449', '554', '555'):
    try:
        w = fetch('https://dlive.sx/watch.php?id=' + cid)
        m = re.search(r'<iframe[^>]+src="(https?://[^"]*stream-\d+\.php[^"]*)"', w)
        if not m:
            print(cid, 'STEP1b: no stream iframe'); continue
        sp = m.group(1)
        p = fetch(sp, 'https://dlive.sx/')
        m2 = re.search(r'<iframe[^>]+src="([^"]+)"', p)
        if not m2:
            print(cid, 'STEP2b: no embed iframe'); continue
        emb = m2.group(1)
        if 'dembed.st' in emb:
            em = re.search(r'id=(\d+)', emb)
            ecid = em.group(1) if em else '?'
            try:
                e = fetch('https://dembed.st/premiumtv/daddy.php?id=' + ecid, 'https://dlive.sx/')
                src = re.search(r'const\s+SRC\s*=\s*["\']([^"\']+m3u8[^"\']*)["\']', e)
                print(cid, '->', emb.split("/")[2], 'SRC:', (src.group(1)[:80] if src else 'NONE'))
            except Exception as e2:
                print(cid, '->', emb.split("/")[2], 'embed FAIL', type(e2).__name__, str(e2)[:60])
        else:
            print(cid, '-> OTHER family:', emb[:90])
    except Exception as ex:
        print(cid, 'FAIL:', type(ex).__name__, str(ex)[:80])