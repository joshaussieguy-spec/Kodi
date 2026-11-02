import re, os, subprocess, sys
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')

k = open('kora_frame.html', encoding='utf-8', errors='replace').read()
print('=== kora frame: first 900 chars ===')
print(k[:900])
print('=== token/atob/iframe refs ===')
for pat in ('token', 'atob', '.m3u8', 'iframe', 'live/', '.php'):
    hits = re.findall(re.escape(pat), k)
    print(pat, len(hits))