import sys, subprocess, os, json, re, html as H
sys.path.insert(0, r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams')
import fullraces as fr

raw = fr.fetch_page('https://ok.ru/video/16714114796204')
m = re.search(r'data-options="([^"]+)"', raw)
data = json.loads(H.unescape(m.group(1)))
md = data.get('flashvars', {}).get('metadata', '')
md = json.loads(md) if isinstance(md, str) else md
full = [v for v in md.get('videos', []) if v.get('name') == 'full'][0]
u = full['url']

exe = os.path.join(r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams', 'bin', 'curl-impersonate.exe')
# Kodi player UAs: ffmpeg default "Lavf/<ver>", Kodi core "Kodi/<ver> ..."
for ua in ('Lavf/58.29.100',
           'Kodi/20.5 (Windows; Windows 10 2004) Kodi/20.5'):
    p = subprocess.run([exe] + fr._CHROME120_ARGS + ['-s', '--max-time', '25',
                       '-o', 'NUL', '-w', '%{http_code}', '-r', '0-127',
                       '-A', ua, u], capture_output=True, timeout=60)
    print(repr(ua), '->', p.stdout.decode(errors='replace'))