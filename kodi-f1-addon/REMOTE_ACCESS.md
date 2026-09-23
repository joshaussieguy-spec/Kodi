# Remote Access to Kodi Laptop

Details kept out of the public repo (LAN addresses + hostnames). See local notes.

## Kodi Install (UWP / Windows Store)
```
%LOCALAPPDATA%\Packages\XBMCFoundation.Kodi_4n2hpmxwrvr6p\LocalCache\Roaming\Kodi\
```
- **Addons:** `addons/plugin.video.f1streams/`
- **Log:** `kodi.log`
- **Old log:** `kodi.old.log`

## Deploy addon update
```bash
scp -i <laptop-key> -o BatchMode=yes \
  main.py \
  <user>@<laptop-ip>:<kodi-roaming-path>/addons/plugin.video.f1streams/main.py
```

## Read Kodi log
```bash
ssh -i <laptop-key> -o BatchMode=yes <user>@<laptop-ip> \
  'powershell -Command "Select-String -Path <kodi-roaming-path>\kodi.log -Pattern f1stream,ERROR -SimpleMatch | Select-Object -Last 20"'
```