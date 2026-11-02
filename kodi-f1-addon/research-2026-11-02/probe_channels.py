import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref='https://dlive.sx/'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

for cid in ('274', '577', '273', '537', '60'):
    try:
        w = fetch('https://dlive.sx/watch.php?id=' + cid)
        m = re.search(r'<iframe[^>]+src="(https?://[^"]*stream-\d+\.php[^"]*)"', w)
        if not m:
            print(cid, 'STEP1b: no stream iframe ->', w[:80] if not w else len(w), 'bytes'); continue
        sp = m.group(1)
        p = fetch(sp, 'https://dlive.sx/')
        m2 = re.search(r'<iframe[^>]+src="([^"]+)"', p)
        if not m2:
            print(cid, 'STEP2b: no iframe in', sp[:60]); continue
        print(cid, 'OK ->', m2.group(1)[:90])
    except Exception as e:
        print(cid, 'FAIL:', type(e).__name__, str(e)[:80])