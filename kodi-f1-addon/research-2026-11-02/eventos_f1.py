import json, os
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')
j = json.load(open('eventos.json', encoding='utf-8', errors='replace'))
print('top keys:', list(j.keys())[:8] if isinstance(j, dict) else 'LIST len=%d' % len(j))
txt = json.dumps(j)
print('f1 mentions:', txt.lower().count('formula 1'), '| gp mentions:', txt.lower().count('grand prix'))
# find motorsport-ish entries
def walk(o, path=''):
    if isinstance(o, dict):
        s = json.dumps(o, ensure_ascii=False).lower()
        if ('formula' in s or 'f1' in s) and len(json.dumps(o)) < 800:
            print('---', path, '::', json.dumps(o, ensure_ascii=False)[:260])
            return
        for k, v in o.items():
            walk(v, path + '/' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o[:400]):
            walk(v, path + '[%d]' % i)
walk(j)