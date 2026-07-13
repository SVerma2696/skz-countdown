@echo off
REM ============================================================
REM  This script builds the Windows app. Double-click it and
REM  wait — when it's done, you get one .exe file that runs on
REM  ANY Windows computer, even without Python installed!
REM ============================================================

REM Step 1: Go shopping — get our toys plus the app-builder (PyInstaller)
pip install -r requirements.txt pyinstaller

REM Step 2: Turn our logo photo into a proper .ico icon file, so the .exe
REM   shows the Stray Kids picture in File Explorer and the taskbar.
python -c "from PIL import Image; Image.open('skz-logo.png').save('skz-logo.ico', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"

REM Step 3: Squish everything into ONE file.
REM   --onefile   = one single .exe instead of a big messy folder
REM   --windowed  = no scary black text window when the app opens
REM   --icon      = use our Stray Kids picture as the .exe's own icon
REM   --add-data  = pack the logos, the tracklist, AND the whole assets
REM                 folder (member/group/logo pictures) inside the .exe.
REM                 On Windows the two sides of --add-data are split by ";"
REM   --collect-all customtkinter = pack ALL of customtkinter's art supplies
pyinstaller --onefile --windowed --name "SKZ-Countdown" ^
  --icon "skz-logo.ico" ^
  --add-data "skz-logo.png;." ^
  --add-data "t&t-logo.png;." ^
  --add-data "tracklist.png;." ^
  --add-data "assets;assets" ^
  --collect-all customtkinter skz_countdown.py

echo Done! Your app is at dist\"SKZ-Countdown.exe"
pause