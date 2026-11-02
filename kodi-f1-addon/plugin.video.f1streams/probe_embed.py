import sys, importlib.util, os, types, re, json
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

base='https://vertex.st'; ref=base+'/ch?id=7'
pjson = fs._http(base+'/api/player.php?id=7', referer=ref).decode('utf-8','replace')
emb = fs._de_esc(re.search(r'"url"\s*:\s*"([^"]+)"', pjson).group(1))
fp_raw = fs._http(emb, referer=ref).decode('utf-8','replace')
fp = fs._de_esc(fp_raw)
out = []

def sec(title, pat, n=6, width=340):
    out.append('===== %s =====' % title)
    for hit in re.findall(pat, fp, re.S)[:n]:
        out.append(re.sub(r'\s+',' ', hit)[:width])
    out.append('')

sec('watchAuth', r'.{0,140}watchAuth.{0,260}')
sec('srcBase', r'.{0,100}srcBase.{0,240}')
sec('secure_hls', r'.{0,80}secure_hls.{0,200}')
sec('clappr Waves init', r'.{0,120}new WavesPlayer.{0,240}', 4)
sec('swarmId', r'.{0,80}swarmId.{0,160}', 3)
open(r'C:\Users\Josh\embed-dump.txt','w',encoding='utf-8').write('\n'.join(out))
print('written', len('\n'.join(out)))