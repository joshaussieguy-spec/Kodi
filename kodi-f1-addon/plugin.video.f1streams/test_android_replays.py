import sys, subprocess, os, json, re, html as H
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

# Android-side path: can curl-impersonate Linux/Android exist? Check main.py's
# Android live lanes work standalone; for replays the REAL question is whether
# ok.ru serves the mp4 to plain stdlib TLS. Test stdlib against the direct CDN URL.
raw = fr.fetch_page('https://ok.ru/video/16714114796204')
m = re.search(r'data-options="([^"]+)"', raw)
data = json.loads(H.unescape(m.group(1)))
md = data.get('flashvars', {}).get('metadata', '')
md = json.loads(md) if isinstance(md, str) else md
full = [v for v in md.get('videos', []) if v.get('name') == 'full'][0]
u = full['url']
import urllib.request
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept': '*/*',
    'Range': 'bytes=0-159',
}
for extra in ({}, {'Referer': 'https://ok.ru/'}):
    h = dict(headers); h.update(extra)
    try:
        req = urllib.request.Request(u, headers=h)
        resp = urllib.request.urlopen(req, timeout=25)
        print('STDLIB', extra or 'no-ref', '->', resp.status, resp.read(32))
    except Exception as e:
        print('STDLIB', extra or 'no-ref', 'FAIL:', e)

# ok.ru path via catalog (Dailymotion stripped 2026-11-02)
cats = ['f2-full-races']
for c in cats:
    races = fr.scrape_category(c, 1)
    print(c, 'races:', len(races))
    if races:
        info = fr.scrape_race_page(races[0]['url'])
        print('  keys:', {k: len(v) for k, v in info.items() if isinstance(v, list)})
        if info.get('ok_ru'):
            res = fr.resolve_okru(info['ok_ru'][0])
            print('  okru resolve:', (res or {}).get('type', 'NONE'), (res or {}).get('url', '')[:60])