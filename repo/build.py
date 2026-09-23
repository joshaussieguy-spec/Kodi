#!/usr/bin/env python3
"""Build the Kodi repository zips: repository zip + per-addon zips + addons.xml.

Run from repo root:  python repo/build.py
Outputs into repo/zips/<addon-id>/ — the layout Kodi expects
(datadir/<addon-id>/<addon-id>-<version>.zip). Kodi installs
repository.thetallone zip, then auto-installs/updates
every addon listed in addons.xml.
"""
import hashlib
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.join(ROOT, "repo")
ZIPS_DIR = os.path.join(REPO_DIR, "zips")
REPO_ADDON_ID = "repository.thetallone"
REPO_ADDON_DIR = "repo/repository.thetallone"  # listed in addons.xml too, for updates

ADDON_DIRS = [
    "kodi-afl-addon/plugin.video.aflstreams",
    "kodi-arabic-addon/plugin.video.arabicshows",
    "kodi-f1-addon/plugin.video.f1streams",
    REPO_ADDON_DIR,
]

ADDON_XML_RE = re.compile(
    r'<addon\s+id="([^"]+)"\s+version="([^"]+)"', re.IGNORECASE | re.DOTALL
)


def version_of(addon_dir):
    with open(os.path.join(addon_dir, "addon.xml"), encoding="utf-8") as f:
        m = ADDON_XML_RE.search(f.read())
    return m.group(2) if m else "0.0.0"


def zipdir(src, addon_id, version):
    """Zip <src> into repo/zips/<addon_id>/<addon_id>-<version>.zip with
    the addon folder at the zip root (Kodi requirement)."""
    out_dir = os.path.join(ZIPS_DIR, addon_id)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{addon_id}-{version}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(src):
            for fn in files:
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, src)
                if "__pycache__" in rel:
                    continue
                z.write(full, os.path.join(addon_id, rel.replace(os.sep, "/")))
    return out


def main():
    entries = []
    built = []
    for d in ADDON_DIRS:
        addon_dir = os.path.join(ROOT, d)
        addon_id = os.path.basename(d)
        version = version_of(addon_dir)
        built.append(zipdir(addon_dir, addon_id, version))
        with open(os.path.join(addon_dir, "addon.xml"), encoding="utf-8") as f:
            entries.append(f.read())
    addons_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<addons>\n"
        + "\n".join(re.sub(r'^\s*<\?xml[^>]*\?>\s*', "", e, flags=re.DOTALL) for e in entries)
        + "\n</addons>\n"
    )
    with open(os.path.join(REPO_DIR, "addons.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(addons_xml)
    md5 = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    with open(os.path.join(REPO_DIR, "addons.xml.md5"), "w") as f:
        f.write(md5)

    # Clean stale zips (old versions) so repo/zips only offers current files
    keep = set(built)
    for base, _, files in os.walk(ZIPS_DIR):
        for fn in files:
            p = os.path.join(base, fn)
            if p not in keep:
                os.remove(p)

    print("Built:")
    print("  repo/addons.xml + addons.xml.md5")
    for p in built:
        print("  " + os.path.relpath(p, REPO_DIR))


if __name__ == "__main__":
    main()