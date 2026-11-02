import re, json, os
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')

h = open('embed_v.txt', encoding='utf-8', errors='replace').read()
m = re.search(r'window\.PP_CLAPPR_CONFIG\s*=\s*(\{.*?\})\s*;', h, re.S)
if m:
    try:
        cfg = json.loads(m.group(1))
        print('SRC:', cfg.get('src', '')[:170])
        print('watchAuth:', str(cfg.get('watchAuth', ''))[:60])
    except Exception as e:
        print('cfg parse fail:', e)
else:
    print('no PP_CLAPPR_CONFIG; literal .m3u8 count:', len(re.findall(r'\.m3u8', h)))

k = open('kora_frame.html', encoding='utf-8', errors='replace').read()
t = re.search(r'CONFIG\.token\s*=\s*["\']?([A-Za-z0-9_\-=]+)', k)
print('kora token found:', bool(t), (t.group(1)[:44] + '...') if t else '')
e = re.search(r'(https?://[a-z0-9]+\.kora-plus\.li)', k)
print('kora edge in frame:', e.group(1) if e else None)