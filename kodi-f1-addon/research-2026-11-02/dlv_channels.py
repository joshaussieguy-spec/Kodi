import re, os
os.chdir(r'C:\Users\Josh\Kodi\kodi-f1-addon\research-2026-11-02')
h = open('dlv_247.html', encoding='utf-8', errors='replace').read()
# channel cards: find id + title pairs
cards = re.findall(r'watch\.php\?id=(\d+)["\'][^>]*>.{0,400}?(?:alt="([^"]*)"|title="([^"]*)"|>([^<]{3,60}))', h, re.S)
seen = {}
for cid, a, t, txt in cards:
    label = (a or t or txt or '').strip()
    if label and cid not in seen:
        seen[cid] = label
print('channel ids found:', len(seen))
f1_like = {cid: lab for cid, lab in seen.items()
           if re.search(r'f1|formula|sky sport|dazn|espn|motorsport|racing', lab, re.I)}
for cid, lab in sorted(f1_like.items()):
    print(cid, '=', lab[:70])