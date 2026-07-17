#!/bin/bash
# ============================================================
#  This script builds the Mac app. Run it on a Mac with:
#  ./build_macos.sh — you get a real .app you can drag into
#  the Applications folder!
# ============================================================
set -e   # If any step fails, stop right away (don't keep going blindly)

# Step 1: Go shopping — get our toys plus the app-builder (PyInstaller)
pip3 install -r requirements.txt pyinstaller

# Step 2: Make a proper Mac ".icns" icon from our logo photo, so the app's
#   Dock icon is the Stray Kids picture instead of a plain default one.
#   (sips and iconutil are built into every Mac.)
rm -rf skz.iconset && mkdir skz.iconset
for SIZE in 16 32 64 128 256 512; do
  sips -z $SIZE $SIZE skz-logo.png --out "skz.iconset/icon_${SIZE}x${SIZE}.png" >/dev/null
  DBL=$((SIZE*2))
  sips -z $DBL $DBL skz-logo.png --out "skz.iconset/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns skz.iconset -o skz-logo.icns
rm -rf skz.iconset

# Step 3: Squish everything into one .app bundle.
#   --icon     = the Dock/Finder icon we just made
#   --add-data = pack the logos, tracklist, release.json (which comeback to
#                count down to), and assets folder inside the .app
#                (on Mac/Linux the two sides of --add-data are split by ":")
pyinstaller --onefile --windowed --name "SKZ-Countdown" \
  --icon "skz-logo.icns" \
  --add-data "skz-logo.png:." \
  --add-data "t&t-logo.png:." \
  --add-data "tracklist.png:." \
  --add-data "release.json:." \
  --add-data "assets:assets" \
  --collect-all customtkinter skz_countdown.py

echo 'Done! Your app is at "dist/SKZ-Countdown.app" — drag it into /Applications.'
echo 'First launch: right-click the app -> Open (Macs are shy about new apps).'