import sys, urllib.request, gzip, io, zlib
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

def get(u):
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        ce = (resp.headers.get('Content-Encoding') or '').lower()
        data = resp.read()
    if 'gzip' in ce:
        data = gzip.decompress(data)
    elif 'deflate' in ce:
        data = zlib.decompress(data, -zlib.MAX_WBITS)
    elif ce == 'br':
        import brotli  # unlikely on Android either — detect first
        data = brotli.decompress(data)
    return data

try:
    b = get('https://ok.ru/video/16714114796204')
    print('len', len(b), 'has data-options:', b'data-options' in b)
except Exception as e:
    print('FAIL:', type(e).__name__, str(e)[:200])