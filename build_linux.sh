#!/bin/bash
# ============================================================
#  This script builds the Linux app. Run it on Linux with:
#  ./build_linux.sh — you get one file that just runs!
# ============================================================
set -e   # If any step fails, stop right away (don't keep going blindly)

# Step 1: Go shopping — get our toys plus the app-builder (PyInstaller)
pip3 install -r requirements.txt pyinstaller

# Step 2: Squish everything into one runnable file.
#   --add-data = pack the logos, tracklist, release.json (which comeback to
#                count down to), and assets folder inside the binary
#                (on Mac/Linux the two sides of --add-data are split by ":")
pyinstaller --onefile --windowed --name "skz-countdown" \
  --add-data "skz-logo.png:." \
  --add-data "t&t-logo.png:." \
  --add-data "tracklist.png:." \
  --add-data "release.json:." \
  --add-data "assets:assets" \
  --collect-all customtkinter skz_countdown.py

echo 'Done! Your app is at dist/skz-countdown'
echo 'Tip: pop-ups need libnotify (notify-send); the tray icon needs an'
echo 'AppIndicator-capable desktop (GNOME users: install the extension).'