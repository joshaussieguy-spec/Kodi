import base64, re, os, urllib.request, ssl, gzip

os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')
k = open('kora_frame.html', encoding='utf-8', errors='replace').read()

m = re.search(r'token:\s*"([A-Za-z0-9_\-=]+)"', k)
tok = m.group(1)
tok += '=' * (-len(tok) % 4)          # tolerate missing padding
url = base64.b64decode(tok).decode()
print('DECODED URL:', url)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ua = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Referer': 'https://a11.kora-plus.li/frame.php?ch=f1',
      'Accept-Encoding': 'gzip'}
req = urllib.request.Request(url, headers=ua)
with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
    data = r.read()
if (r.headers.get('Content-Encoding') or '').lower() == 'gzip':
    data = gzip.decompress(data)
txt = data.decode('utf-8', 'replace')
open('kora_manifest.m3u8', 'w', encoding='utf-8').write(txt)
print('HTTP manifest bytes:', len(data))
print(txt[:500])