import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref='https://www.google.com/'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.geturl(), r.read().decode('utf-8', 'replace')

# 1. thedaddy.to / thedaddy.pk homepages
for d in ('https://thedaddy.to/', 'https://thedaddy.pk/'):
    try:
        redir, h = fetch(d)
        f1 = sorted(set(re.findall(r'href="([^"]*(?:f1|formula)[^"]*)"', h, re.I)))[:12]
        print('==', d, '->', redir, '| F1 links:', f1)
    except Exception as e:
        print('==', d, 'FAIL:', type(e).__name__, str(e)[:70])

# 2. buffstreams F1 page
try:
    redir, h = fetch('https://buffstreams24.org/f1-streams4')
    iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', h, re.I)
    links = sorted(set(re.findall(r'href="([^"]*(?:sky|f1|streaming|watch)[^"]*)"', h, re.I)))[:10]
    print('== buffstreams F1 ->', redir, '| iframes:', iframes[:5], '| links:', links)
except Exception as e:
    print('== buffstreams FAIL:', type(e).__name__, str(e)[:70])