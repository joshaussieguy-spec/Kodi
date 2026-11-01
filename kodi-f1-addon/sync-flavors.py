#!/usr/bin/env python3
"""Sync live-lane code from the PC addon to the Android flavor.

Run from repo root:  python kodi-f1-addon/sync-flavors.py

The two tracks share ONLY the live-lane code (main.py minus the PC-only
replays gate, f1_servers.py). The Android dir is the copied target.
When you fix an upstream/solver bug once, run this so both tracks ship it:
  1. edit kodi-f1-addon/plugin.video.f1streams (PC track) as usual
  2. python kodi-f1-addon/sync-flavors.py
  3. bump BOTH addon.xml versions (PC: 2.8.x, Android: 2.7.y — independent)
  4. python repo/build.py   (publishes both zips + addons.xml + md5)
  5. commit + push (jsDelivr CDN serves it)

PC-only files NEVER cross over — enforced both by this script's excludes and
by a git-ignored marker (Android dir has no bin/, _lib/, fullraces.py).
"""
import re
import shutil
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PC_DIR = os.path.join(HERE, "plugin.video.f1streams")
ANDROID_DIR = os.path.join(HERE, "plugin.video.f1streams.android")

# Live-lane files that must be byte-identical, after the PC gate block gets
# force-hazard-stripped: Android needs PC_REPLAYS permanently False even if the
# PC gate block changes shape later.
LIVE_FILES = ["f1_servers.py"]

# main.py: copied, then the Android gate surgically replaced (keeps menu +
# router edits flowing over from PC while replays stay structurally absent).
MAIN_PATCH = (
    ("_IS_WINDOWS = _os.name == 'nt'", ""),
    ("PC_REPLAYS = _IS_WINDOWS and _os.path.isfile(_CUR_EXE)",
     "PC_REPLAYS = False  # Android track: replays structurally PC-only"),
)

VERSIONS = {}  # addon id -> version, filled from each addon.xml


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def main():
    if not os.path.isdir(ANDROID_DIR):
        print("Android flavor missing:", ANDROID_DIR)
        sys.exit(1)

    # 1. byte-identical live files
    for rel in LIVE_FILES:
        shutil.copy2(os.path.join(PC_DIR, rel), os.path.join(ANDROID_DIR, rel))
        print("synced", rel)

    # 2. main.py with the gate swap
    src = read(os.path.join(PC_DIR, "main.py"))
    for old, new in MAIN_PATCH:
        if old not in src:
            print(f"WARN: pattern not found in main.py: {old!r} — check the gate block")
            sys.exit(2)
        src = src.replace(old, new)
    with open(os.path.join(ANDROID_DIR, "main.py"), "w",
              encoding="utf-8", newline="") as f:
        f.write(src)
    print("synced main.py (gate -> PC_REPLAYS=False)")

    # 3. report versions from both manifests
    for d, label in ((PC_DIR, "PC"), (ANDROID_DIR, "Android")):
        ax = read(os.path.join(d, "addon.xml"))
        m = re.search(r'id="([^"]+)"\s+version="([^"]+)"', ax)
        if m:
            VERSIONS[m.group(1)] = m.group(2)
            print(f"{label}: {m.group(1)} @ {m.group(2)}")


if __name__ == "__main__":
    main()