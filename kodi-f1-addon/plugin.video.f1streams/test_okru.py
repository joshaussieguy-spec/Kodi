import sys, re, json, html as H
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

# 1. Which resolver does main.py prefer for this page? We know ok_ru -> 16714114796204
raw = fr.fetch_page('https://ok.ru/video/16714114796204')
print('ok page len:', len(raw) if raw else 0)
m = re.search(r'data-options="([^"]+)"', raw or '')
print('data-options found:', bool(m))
res = None
if m:
    try:
        data = json.loads(H.unescape(m.group(1)))
        fv = data.get('flashvars', {})
        md = fv.get('metadata', '')
        md = json.loads(md) if isinstance(md, str) else md
        vids = md.get('videos', [])
        print('qualities:', [(v.get('name'), len(v.get('url',''))) for v in vids][:6])
        res = fr.resolve_okru('16714114796204')
        if res:
            u = res['url']
            print('resolved quality:', res.get('quality'), 'type:', res.get('type'))
            print('url head:', u[:110])
            # Fetch first chunk of the actual media
            import urllib.request, gzip
            req = urllib.request.Request(u, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126',
                'Referer': 'https://ok.ru/',
                'Accept': '*/*',
                'Accept-Encoding': 'identity',
            })
            resp = urllib.request.urlopen(req, timeout=25)
            first = resp.read(200000)
            print('HTTP', resp.status, 'bytes', len(first), 'head:', first[:60])
    except Exception as e:
        print('ERR:', type(e).__name__, e)
else:
    print('no data-options — page is a CF challenge or layout changed. head:', (raw or '')[:200])