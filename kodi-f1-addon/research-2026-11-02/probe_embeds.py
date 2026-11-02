import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

for cid in ('274', '577', '273', '537', '60'):
    try:
        e = fetch('https://dembed.st/premiumtv/daddy.php?id=' + cid,
                  'https://dlive.sx/stream/stream-%s.php' % cid)
        src = re.search(r'const\s+SRC\s*=\s*["\']([^"\']+m3u8[^"\']*)["\']', e)
        if src:
            print(cid, 'SRC:', src.group(1)[:110])
        else:
            m3 = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', e)
            print(cid, 'const-SRC no | literal m3u8:', len(m3), (m3[-1][:100] if m3 else 'none'), '| page bytes:', len(e))
    except Exception as ex:
        print(cid, 'FAIL:', type(ex).__name__, str(ex)[:90])