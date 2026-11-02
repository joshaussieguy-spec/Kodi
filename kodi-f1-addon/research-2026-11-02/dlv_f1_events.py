import re, os, urllib.request, ssl, datetime, urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

h = fetch('https://dlive.sx/index.php', 'https://dlive.sx/')
# find blocks (probably <tr> or div cards) mentioning F1/Formula/Grand Prix/Practice/Qualifying
blocks = re.split(r'<(?:tr|article|div class="match"[^>]*)', h)
f1blocks = [b for b in blocks if re.search(r'formula\s*1|f1|grand\s+prix|practice|qualifying', b, re.I)]
print('candidate blocks:', len(f1blocks))
seen = set()
for b in f1blocks[:14]:
    m = re.search(r'href="([^"]+)"[^>]*>\s*([^<]{4,90})', b)
    if m and m.group(1) not in seen:
        seen.add(m.group(1))
        print(' ', m.group(1), '|', ' '.join(m.group(2).split())[:70])