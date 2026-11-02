import json, os, time
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')
j = json.load(open('tvsport.json', encoding='utf-8', errors='replace'))
now = time.time() * 1000
print('total matches:', len(j.get('matches', [])))
f1 = [m for m in j.get('matches', [])
      if 'formula' in (m.get('league') or '').lower()
      or 'formula' in (m.get('matchstr') or m.get('team1') or '').lower()
      or 'grand prix' in (m.get('matchstr') or m.get('team1') or '').lower()]
print('F1-ish:', len(f1))
for m in f1[:12]:
    ts = m.get('startTimestamp', 0)
    lbl = time.strftime('%d %H:%M', time.gmtime(ts / 1000)) + 'Z' if ts else '?'
    print('-', lbl, '|', (m.get('matchstr') or m.get('team1') or '')[:60],
          '| ch:', len(m.get('channels') or []),
          '|', json.dumps(m.get('channels') or [])[:180])