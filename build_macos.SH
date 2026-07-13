#!/bin/bash
# ============================================================
#  This script builds the Mac app. Run it on a Mac with:
#  ./build_macos.sh — you get a real .app you can drag into
#  the Applications folder!
# ============================================================
set -e   # If any step fails, stop right away (don't keep going blindly)

# Step 1: Go shopping — get our toys plus the app-builder (PyInstaller)
pip3 install -r requirements.txt pyinstaller

# Step 2: Squish everything into one .app bundle
#   --onefile  = pack it all together
#   --windowed = make a real Mac .app (no terminal window)
#   --add-data = pack our two logo pictures inside the .app
#   --collect-all customtkinter = pack ALL of customtkinter's art supplies
pyinstaller --onefile --windowed --name "SKZ Countdown" \
  --add-data "skz-logo.jpg:." \
  --add-data "t&t-logo.png:." \
  --collect-all customtkinter skz_countdown.py

echo 'Done! Your app is at "dist/SKZ Countdown.app" — drag it into /Applications.'
echo 'First launch: right-click the app -> Open (Macs are shy about new apps).'