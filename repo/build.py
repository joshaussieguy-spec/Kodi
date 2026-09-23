#!/usr/bin/env python3
"""Build the Kodi repository zips: repository zip + per-addon zips + addons.xml.

Run from repo root:  python repo/build.py
Outputs into repo/ — ready to commit & push. Kodi installs
repository.joshs.kodi.apps-1.0.0.zip, then auto-installs/updates
every addon listed in addons.xml.
"""
import hashlib
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.join(ROOT, "repo")
ADDON_DIRS = [
    "kodi-afl-addon/plugin.video.aflstreams",
    "kodi-arabic-addon/plugin.video.arabicshows",
    "kodi-f1-addon/plugin.video.f1streams",
]
REPO_ADDON_ID = "repository.joshs.kodi.apps"

ADDON_XML_RE = re.compile(
    r'<addon\s+id="([^"]+)"\s+version="([^"]+)"', re.IGNORECASE | re.DOTALL
)


def version_of(addon_dir):
    with open(os.path.join(addon_dir, "addon.xml"), encoding="utf-8") as f:
        m = ADDON_XML_RE.search(f.read())
    return m.group(2) if m else "0.0.0"


def zipdir(src, dest, addon_id, version):
    out = os.path.join(REPO_DIR, f"{addon_id}-{version}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(src):
            for fn in files:
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, os.path.dirname(src))
                if "__pycache__" in rel:
                    continue
                z.write(full, os.path.join(os.path.basename(src), rel))
    return out


def zip_repository():
    src = os.path.join(REPO_DIR, REPO_ADDON_ID.replace(".", "_").replace("joshs_kodi", "joshs-kodi")) \
        if False else os.path.join(REPO_DIR, "repository.joshs.kodi.apps")
    out = os.path.join(REPO_DIR, f"{REPO_ADDON_ID}-1.0.0.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(src):
            for fn in files:
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, REPO_DIR)
                z.write(full, rel)
    return out


def main():
    entries = []
    for d in ADDON_DIRS:
        addon_dir = os.path.join(ROOT, d)
        addon_id = os.path.basename(d)
        version = version_of(addon_dir)
        zipdir(addon_dir, REPO_DIR, addon_id, version)
        with open(os.path.join(addon_dir, "addon.xml"), encoding="utf-8") as f:
            entries.append(f.read())
    addons_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<addons>\n" + "\n".join(entries) + "\n</addons>\n"
    )
    with open(os.path.join(REPO_DIR, "addons.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(addons_xml)
    md5 = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    with open(os.path.join(REPO_DIR, "addons.xml.md5"), "w") as f:
        f.write(md5)
    zr = zip_repository()
    for p in [os.path.join(REPO_DIR, f"{a.rsplit('/', 1)[0]}") for a in ADDON_DIRS]:
        pass
    print("Built:")
    print("  repo/addons.xml + addons.xml.md5")
    for d in ADDON_DIRS:
        aid = os.path.basename(d)
        v = version_of(os.path.join(ROOT, d))
        print(f"  repo/{aid}-{v}.zip")
    print(f"  repo/{REPO_ADDON_ID}-1.0.0.zip")


if __name__ == "__main__":
    main()