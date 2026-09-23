#!/bin/bash
# F1 Stream Player for Android/Termux
# Automatically fetches fresh stream tokens and plays with correct headers

STREAM_KEY="q3zz9ru56f"  # Austrian GP

# Get fresh token
SUB_$(curl -s "https://obstreamx.click/live/${STREAM_KEY}.m3u8" | grep -v '^#' | head -1)

echo "Found sub-playlist: $SUB"

# Play with mpv (has proper header support)
if command -v mpv &>/dev/null; then
    mpv --http-header-fields="Referer: https://getembed.live/" "https://obstreamx.click/$SUB"
elif command -v vlc &>/dev/null; then
    # VLC might work with referer
    vlc --http-referrer=https://getembed.live/ "https://obstreamx.click/$SUB"
else
    echo "Error: Install mpv or vlc"
    exit 1
fi