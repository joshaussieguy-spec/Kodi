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
CHROME_ARGS = ['--ciphers', 'TLS_AES_128_GC...'.replace('...', 'M_SHA,TLS_AES_256_GCM_SHA384'),
               '--http2']
# Instead of guessing args, run the EXACT cmd the addon builds:
cmd = [exe] + fr._CHROME120_ARGS + ['-s', '--max-time', '30',
      '-w', fr._CURL_META + '%{http_code}', '-r', '0-159', u]
meta, out = fr._meta_split(subprocess.run(cmd, capture_output=True, timeout=60).stdout)
code = meta.split(':')[0]
print('meta:', meta[:80])
print('code:', code, 'bytes:', len(out))
print('magic:', out[:32])