import json, os
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')
chans = json.load(open('iptv_channels.json', encoding='utf-8', errors='replace'))
streams = json.load(open('iptv_streams.json', encoding='utf-8', errors='replace'))
print('channels:', len(chans), '| streams:', len(streams))

hits = [c for c in chans
        if 'f1' in c.get('name', '').lower()
        or 'formula' in c.get('name', '').lower()
        or ('sky' in c.get('name', '').lower() and 'sports' in c.get('name', '').lower()
            and any(w in c.get('name', '').lower() for w in ('f1', 'formula')))]
print('F1-ish channels:', len(hits))
for c in hits[:25]:
    print('-', c.get('id'), '|', c.get('name'), '|', c.get('country'))

ids = {c.get('id') for c in hits}
sh = [s for s in streams if s.get('channel') in ids and not s.get('dead')]
print('live streams for those:', len(sh))
for s in sh[:20]:
    q = s.get('quality') or '?'
    print('-', s.get('channel'), '|', q, '|', s.get('url')[:110])