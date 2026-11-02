#!/usr/bin/env python3
"""gen_catalog.py — regenerate replay-catalog.json from fullraces.com.

Runs on PC only (fullraces.com 403s stdlib; uses the bundled curl-impersonate
exe via fullraces.py). Emits a flavor-neutral static catalog consumed by BOTH
flavors: PC scrapes live at runtime, Android relies on this static catalog.

Catalog v2 entry shape:
    {
      "title": "RACE - F1 2026 - Mexico City Grand Prix - Full Race Replay",
      "url":  "https://fullraces.com/race-f1-2026-mexico-city-grand-prix-...",
      "thumb": "https://...jpg",
      "cats": ["2026", "race-parts"],
      "ok_ru": ["16714114796204", ...]   # ok.ru video ids, tier-1 playback
    }

Android playback resolution: catalog ok_ru -> ok.ru JSON API (stdlib) ->
vkuser.net MP4. No fullraces.com, no Cloudflare, no impersonation needed.

Usage:  python gen_catalog.py           # regenerate (PC, from live site)
        python gen_catalog.py --verify  # just verify the saved catalog
"""
import sys, os, re, json, argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'plugin.video.f1streams'))
import fullraces as fr  # exe-backed fetch (PC)

OUT = os.path.join(_HERE, 'replay-catalog.json')
SEASON = '2026'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    if args.verify:
        data = json.load(open(OUT, encoding='utf-8'))
        n_ok = sum(1 for r in data['races'] if r.get('ok_ru'))
        print('catalog: %d races, %d with ok_ru' % (
            len(data['races']), n_ok))
        return 0

    races = fr.scrape_category(SEASON, 1)
    print('scraped %d listing entries' % len(races))
    out = []
    for i, r in enumerate(races):
        url = r.get('url', '')
        if not url:
            continue
        try:
            page = fr.scrape_race_page(url)
        except Exception as e:
            print('  %d/%d FAIL %s' % (i + 1, len(races), str(e)[:60]))
            continue
        entry = {
            'title': r.get('title') or page.get('title') or 'Race',
            'url': url,
            'thumb': r.get('thumb', ''),
            'cats': [SEASON],
        }
        ok_ids = [str(x) for x in page.get('ok_ru', [])]
        if ok_ids:
            entry['ok_ru'] = ok_ids
        # dailymotion fallback removed 2026-11-02 — ok_ru only
        out.append(entry)
        print('  %d/%d %s (ok:%s)' % (
            i + 1, len(races), entry['title'][:38],
            ','.join(ok_ids[:1]) or '-'))

    cat = {'gen': '2026-11-02', 'season': SEASON, 'races': out}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(cat, f, indent=1)
    print('wrote %s: %d entries (%d with ok_ru)' % (
        OUT, len(out), sum(1 for e in out if e.get('ok_ru'))))


if __name__ == '__main__':
    main()