import sys, importlib.util, os, types, re, json, urllib.request, gzip
sys.path.insert(0, os.path.abspath('.'))
for name in ('xbmc','xbmcgui','xbmcaddon','xbmcplugin'):
    m = types.ModuleType(name)
    class _A:
        def __init__(self,*a,**k): pass
        def __getattr__(self,n): return (lambda *a,**k: None)
    for attr in ('ListItem','Dialog','DialogProgress','DialogOK','TextInputDialog','Addon'):
        setattr(m, attr, _A)
    m.LOGDEBUG=m.LOGERROR=m.LOGINFO=m.LOGWARNING=0
    sys.modules[name] = m
spec = importlib.util.spec_from_file_location('fs', 'f1_servers.py')
fs = importlib.util.module_from_spec(spec); sys.modules['fs'] = fs
spec.loader.exec_module(fs)

ref = 'https://vertex.st/ch?id=7'
pjson = fs._http('https://vertex.st/api/player.php?id=7', referer=ref).decode('utf-8','replace')
emb = fs._de_esc(re.search(r'"url"\s*:\s*"([^"]+)"', pjson).group(1))
fp_raw = fs._http(emb, referer=ref).decode('utf-8','replace')
cfg = json.loads(re.search(r'window\.PP_CLAPPR_CONFIG\s*=\s*(\{.*?\})\s*;', fp_raw, re.S).group(1))
src, wa = cfg['src'], cfg['watchAuth']
open(r'C:\Users\Josh\embed-vertex.html','w',encoding='utf-8').write(fs._de_esc(fp_raw))
print('cfg src  :', src)
print('watchAuth:', wa)

def raw(url, headers):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', fs.UA)
    for k, v in headers.items(): req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20, context=fs._SSL_CTX) as r:
            d = r.read()
            if (r.headers.get('Content-Encoding') or '').lower() == 'gzip':
                d = gzip.decompress(d)
            sc = str(r.headers.get('Set-Cookie'))
            return 'OK ' + d[:40].decode('utf-8','replace').replace('\n','|') + ' | set-cookie: ' + sc[:90]
    except Exception as e:
        return 'ERR %r' % e

ml = 'https://matchli.st/'
tests = [
    ('verbatim+ref+wa-cookie', src, {'Referer': ml, 'Cookie': 'watchAuth=' + wa}),
    ('verbatim+ref only     ', src, {'Referer': ml}),
    ('verbatim+ref+origin   ', src, {'Referer': ml, 'Origin': ml.rstrip('/')}),
    ('url+%26wa param       ', src + '&wa=' + wa, {'Referer': ml}),
    ('srcBase+%26wa param   ', cfg['srcBase'] + '&wa=' + wa, {'Referer': ml}),
    ('verbatim+ref=vertex   ', src, {'Referer': 'https://vertex.st/'}),
    ('verbatim+no referer   ', src, {}),
]
for label, u, h in tests:
    print(label, '->', raw(u, h))