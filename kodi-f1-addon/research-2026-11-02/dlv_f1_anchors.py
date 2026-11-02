import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

h = fetch('https://dlive.sx/index.php?cat=Upcoming+Events', 'https://dlive.sx/')
# Find F1-related anchors and their hrefs
anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*(?:F1|Formula|Grand Prix|Practice|Quali)[^<]*)</a>', h, re.I)
print('F1 anchors:')
for u, t in sorted(set(anchors)):
    print(' ', u[:90], '|', ' '.join(t.split())[:70])
# data-stream / data-ch pairs near F1
m = re.findall(r'data-ch="([^"]+)"[^>]*data-id="(\d+)"|data-id="(\d+)"[^>]*data-ch="([^"]+)"', h)
print('data-ch/id pairs:', m[:12])