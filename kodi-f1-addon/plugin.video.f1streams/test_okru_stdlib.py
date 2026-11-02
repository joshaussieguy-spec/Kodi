import sys, urllib.request, gzip, io
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

def get(u):
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'text/html,*/*', 'Accept-Encoding': 'zstd,br'[:0] or 'identity'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, resp.read()

# 1. ok.ru video page via plain stdlib (Android path!)
try:
    st, b = get('https://ok.ru/video/16714114796204')
    import re, json, html as H
    txt = b.decode('utf-8', errors='replace')
    m = re.search(r'data-options="([^"]+)"', txt)
    print('OKRU STDLIB:', st, 'len', len(b), 'data-options:', bool(m))
    if m:
        data = json.loads(H.unescape(m.group(1)))
        md = data.get('flashvars', {}).get('metadata', '')
        md = json.loads(md) if isinstance(md, str) else md
        vids = md.get('videos', [])
        print('  qualities:', [(v.get('name')) for v in vids])
        full = [v for v in vids if v.get('name') == 'full'][0]
        print('  mp4 head 32B:', end=' ')
        r2 = urllib.request.Request(full['url'], headers={'User-Agent': UA, 'Range': 'bytes=0-31'})
        with urllib.request.urlopen(r2, timeout=25) as resp2:
            print(resp2.status, resp2.read(32))
except Exception as e:
    print('OKRU STDLIB FAIL:', e)