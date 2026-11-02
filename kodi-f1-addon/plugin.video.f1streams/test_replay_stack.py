import sys, subprocess, os, json, re, html as H
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

# 1. MP4 signature check on the exe-fetched bytes (range just header bytes)
raw = fr.fetch_page('https://ok.ru/video/16714114796204')
m = re.search(r'data-options="([^"]+)"', raw)
data = json.loads(H.unescape(m.group(1)))
md = data.get('flashvars', {}).get('metadata', '')
md = json.loads(md) if isinstance(md, str) else md
full = [v for v in md.get('videos', []) if v.get('name') == 'full'][0]

exe = os.path.join(r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams', 'bin', 'curl-impersonate.exe')
args = ['-s', '--max-time', '30', '-r', '0-63', full.get('url')]
p = subprocess.run([exe] + args, capture_output=True, timeout=60)
print('MP4 head bytes:', p.stdout[:24])

# 2. Is fullraces.com itself reachable via plain urllib (Android stdlib path)?
import urllib.request
def _uget(u):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126', 'Accept': 'text/html'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, resp.read(4000)
try:
    st, b = _uget('https://fullraces.com/')
    txt = b.decode('utf-8', errors='replace')
    print('URIB fullraces:', st, 'len', len(b), 'cf?', 'Just a moment' in txt)
except Exception as e:
    print('URIB fullraces FAIL:', e)

# 3. Category scrape via pure urllib path?
try:
    st, b = _uget('https://fullraces.com/category/2026/')
    txt = b.decode('utf-8', errors='replace')
    print('URIB cat 2026:', st, 'race links:', txt.count('/race-f1-2026'))
except Exception as e:
    print('URIB cat FAIL:', e)