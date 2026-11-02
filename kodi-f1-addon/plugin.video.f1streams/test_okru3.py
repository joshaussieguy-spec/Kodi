import sys, json, re, html as H, urllib.request
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

raw = fr.fetch_page('https://ok.ru/video/16714114796204')
m = re.search(r'data-options="([^"]+)"', raw)
data = json.loads(H.unescape(m.group(1)))
md = data.get('flashvars', {}).get('metadata', '')
md = json.loads(md) if isinstance(md, str) else md
full = [v for v in md.get('videos', []) if v.get('name') == 'full'][0]
u = full['url']

# 1. curl-impersonate.exe fetch (Chrome TLS) — this is what Kodi actually ships
code, out = fr._exe_fetch(u, 20)
print('EXE fetch:', code, len(out))
if code != 200:
    print('exe body:', out[:200])

# 2. curl_cffi chrome120 impersonation
if fr._cf_requests is not None:
    try:
        r = fr._cf_requests.get(u, impersonate='chrome120', timeout=20)
        print('CFI fetch:', r.status_code, len(r.content))
        print('head:', r.content[:60])
    except Exception as e:
        print('CFI FAIL:', e)