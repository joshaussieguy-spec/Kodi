import json, os
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')
j = json.load(open('eventos.json', encoding='utf-8', errors='replace'))
sp = j.get('sports', [])
print('sports type:', type(sp).__name__, 'len:', len(sp))
sample = sp[0] if sp else None
print('sample keys:', json.dumps(sample, ensure_ascii=False)[:400] if sample else None)
names = []
for s in sp:
    n = (s.get('sport') or s.get('name') or s.get('title') or '') if isinstance(s, dict) else str(s)
    names.append(n)
    if any(w in n.lower() for w in ('motor', 'formula', 'f1', 'race', 'carrer')):
        print('HIT:', json.dumps(s, ensure_ascii=False)[:300])
print('all names:', names)