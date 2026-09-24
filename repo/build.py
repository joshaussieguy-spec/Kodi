#!/usr/bin/env python3
"""Build the Kodi repository zips: repository zip + per-addon zips + addons.xml.

Run from repo root:  python repo/build.py
Outputs into repo/zips/<addon-id>/ — the layout Kodi expects
(datadir/<addon-id>/<addon-id>-<version>.zip). Kodi installs
repository.thetallone zip, then auto-installs/updates
every addon listed in addons.xml.

GOTCHAS (learned 2026-09-23):
- NEVER delete old-version zips: Kodi caches addons.xml and may request an
  old version for a while; a 404 = "invalid package"/failed install.
  COMPAT_VERSIONS regenerates old-version zips from current content.
- Kodi fetches repo-listing artwork from datadir too:
  zips/<id>/icon.png, zips/<id>/fanart.jpg, zips/<id>/resources/*.png|jpg
  → copy artwork out of the addon dirs into both layouts.
"""
import hashlib
import os
import re
import shutil
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
    "kodi-f1-addon/script.kodirestart",
    REPO_ADDON_DIR,
]

# Old versions Kodi's cached repo index may still request (regenerated as
# fixed zips from current content with the version string patched back).
COMPAT_VERSIONS = {
    "plugin.video.aflstreams": ["1.3.1"],
    "plugin.video.arabicshows": ["1.0.6"],
}

ARTWORK = ("icon.png", "fanart.jpg", "resources/icon.png", "resources/fanart.jpg")

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


def compat_zip(src_zip, addon_id, cur_ver, old_ver):
    """Copy a built zip, patching addon.xml's version back to old_ver so the
    stale repo index can still install it (with the FIXED zip structure)."""
    out = os.path.join(os.path.dirname(src_zip), f"{addon_id}-{old_ver}.zip")
    with zipfile.ZipFile(src_zip) as zin, zipfile.ZipFile(
        out, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith("addon.xml"):
                data = data.decode("utf-8").replace(
                    f'version="{cur_ver}"', f'version="{old_ver}"', 1
                ).encode("utf-8")
            zout.writestr(item, data)
    return out


def copy_artwork(addon_dir, addon_id):
    copied = []
    for rel in ARTWORK:
        src = os.path.join(addon_dir, rel.replace("/", os.sep))
        if not os.path.isfile(src):
            continue
        dst = os.path.join(ZIPS_DIR, addon_id, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return copied


def main():
    entries = []
    built = []
    artworks = []
    for d in ADDON_DIRS:
        addon_dir = os.path.join(ROOT, d)
        addon_id = os.path.basename(d)
        version = version_of(addon_dir)
        out = zipdir(addon_dir, addon_id, version)
        built.append(out)
        for old in COMPAT_VERSIONS.get(addon_id, []):
            built.append(compat_zip(out, addon_id, version, old))
        artworks += [f"{addon_id}/{r}" for r in copy_artwork(addon_dir, addon_id)]
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

    # Only remove stale-version ZIP files that no longer belong
    # (keep every zip we just built, incl. compat; never touch artwork).
    keep = set(built)
    for base, _, files in os.walk(ZIPS_DIR):
        for fn in files:
            if not fn.endswith(".zip"):
                continue
            p = os.path.join(base, fn)
            if p not in keep:
                os.remove(p)

    print("Built:")
    print("  repo/addons.xml + addons.xml.md5")
    for p in built:
        print("  " + os.path.relpath(p, REPO_DIR))
    for a in artworks:
        print("  art: " + a)


if __name__ == "__main__":
    main()