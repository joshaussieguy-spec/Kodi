# Kodi Apps

Collection of Josh's Kodi addons and helpers.

## Addons

| Addon | What it does |
|---|---|
| `kodi-afl-addon/plugin.video.aflstreams` | AFL live streams (DaddyLive source, local time display) |
| `kodi-arabic-addon/plugin.video.arabicshows` | Arabic live channels + YouTube shows (with yt-resolver proxy) |
| `kodi-f1-addon/plugin.video.f1streams` | F1 live streams + full races (DaddyLive source) |

## Also in here

- `kodi-f1-addon/f1-proxy.py` — local HLS restreaming proxy (adds Referer header, port 8888) so VLC/phones can play
- `kodi-arabic-addon/yt-resolver-proxy.py` — YouTube stream resolver proxy
- `kodi-arabic-addon/restart-kodi.bat` — kill + relaunch Kodi over SSH (schtasks trick for the interactive session)
- `kodi-arabic-addon/working_channels.json` — channel list with tested status codes

## Deploy

Addons run on the HTPC laptop (Kodi from Windows Store). Deploy = scp file swap — see `kodi-f1-addon/REMOTE_ACCESS.md` for the layout; addresses/keys stay in local notes, not in the repo.

Never restart Kodi mid-watch — stop playback via JSON-RPC `Player.Stop` first.