import http.client, ssl, json, re, html as H, urllib.request

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

def robust_get(u, maxbytes=2_200_000):
    """stdlib fetch tolerant of mid-stream resets (ok.ru truncates after ~1.18MB)."""
    p = u.split('/', 3)
    host, path = p[2], '/' + (p[3] if len(p) > 3 else '')
    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(host, timeout=30, context=ctx)
    conn.request('GET', path, headers={'User-Agent': UA, 'Accept': 'text/html,*/*',
                                       'Accept-Encoding': 'identity', 'Connection': 'close'})
    resp = conn.getresponse()
    chunks, total = [], 0
    while total < maxbytes:
        try:
            c = resp.read(65536)
        except Exception:
            break
        if not c:
            break
        chunks.append(c); total += len(c)
    conn.close()
    return resp.status, b''.join(chunks)

st, body = robust_get('https://ok.ru/video/16714114796204')
txt = body.decode('utf-8', errors='replace')
m = re.search(r'data-options="([^"]+)"', txt)
print('status:', st, 'len:', len(body), 'data-options:', bool(m))
data = json.loads(H.unescape(m.group(1)))
md = data.get('flashvars', {}).get('metadata', '')
md = json.loads(md) if isinstance(md, str) else md
full = [v for v in md.get('videos', []) if v.get('name') == 'full'][0]
print('full quality url head:', full['url'][:100])
# and the MP4 range via stdlib
r2 = urllib.request.Request(full['url'], headers={'User-Agent': UA, 'Range': 'bytes=0-31'})
with urllib.request.urlopen(r2, timeout=25) as r:
    print('MP4:', r.status, r.read(32))