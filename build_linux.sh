#!/bin/bash
# ============================================================
#  This script builds the Linux app. Run it on Linux with:
#  ./build_linux.sh — you get one file that just runs!
# ============================================================
set -e   # If any step fails, stop right away (don't keep going blindly)

# Step 1: Go shopping — get our toys plus the app-builder (PyInstaller)
pip3 install -r requirements.txt pyinstaller

# Step 2: Squish everything into one runnable file
#   --add-data = pack our two logo pictures inside the finished binary
pyinstaller --onefile --windowed --name "skz-countdown" \
  --add-data "skz-logo.jpg:." \
  --add-data "t&t-logo.png:." \
  --collect-all customtkinter skz_countdown.py

echo 'Done! Your app is at dist/skz-countdown'
echo 'Tip: pop-ups need libnotify (notify-send); the tray icon needs an'
echo 'AppIndicator-capable desktop (GNOME users: install the extension).'