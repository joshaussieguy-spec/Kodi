import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

h = fetch('https://dlive.sx/index.php', 'https://dlive.sx/')
# dlive index is JS-built; look for embedded JSON data with F1
# pattern: ids in data blobs
ids = re.findall(r'"id"\s*:\s*(\d{2,5})[^}]{0,120}?[Ff]ormula|Formula[^}]{0,160}?"id"\s*:\s*(\d{2,5})', h)
print('json-embed F1 ids:', ids[:12])
# any ajax endpoint hints
eps = sorted(set(re.findall(r'(?:url|endpoint|api)[\'"\s:]+[\'"]([^\'"]+\.php[^\'"]*)[\'"]', h, re.I)))
print('ajax endpoints:', eps[:12])
# "cat=" values seen
cats = sorted(set(re.findall(r'cat=([^&"\']+)', h)))
print('cats:', [urllib.parse.unquote(c) for c in cats][:30])