import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref='https://dlive.sx/'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        redir = r.geturl()
        data = r.read().decode('utf-8', 'replace')
    return redir, data

# 1. dlive homepage: list external hosts it references
_, h = fetch('https://dlive.sx/')
hosts = sorted(set(re.findall(r'https?://([a-z0-9.-]+)', h)))
print('dlive hosts:', hosts[:20])

# 2. aggregator sweep — F1 landing pages
targets = [
    ('buffstreams', 'https://buffstreams24.org/'),
    ('sportsonline', 'https://sportsonline.sx/'),
    ('totalsportek', 'https://totalsportek.com/'),
    ('streameast', 'https://streameast.mx/'),
    ('footybite', 'https://footybite.co/'),
]
for name, url in targets:
    try:
        redir, d = fetch(url)
        f1_links = re.findall(r'href="([^"]*(?:f1|formula|motorsport|race)[^"]*)"', d, re.I)
        f1_links = sorted(set(f1_links))[:8]
        print('==', name, '| at', redir, '| f1 links:', f1_links)
    except Exception as e:
        print('==', name, 'FAIL:', type(e).__name__, str(e)[:70])