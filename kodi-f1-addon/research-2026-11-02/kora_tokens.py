import re, os
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')

k = open('kora_frame.html', encoding='utf-8', errors='replace').read()
# print every line mentioning token
for i, line in enumerate(k.splitlines(), 1):
    if 'token' in line.lower():
        print('%3d| %s' % (i, line.strip()[:200]))
print('=== atob line ===')
for i, line in enumerate(k.splitlines(), 1):
    if 'atob' in line:
        print('%3d| %s' % (i, line.strip()[:300]))