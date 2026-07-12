@echo off
REM ============================================================
REM  This script builds the Windows app. Double-click it and
REM  wait — when it's done, you get one .exe file that runs on
REM  ANY Windows computer, even without Python installed!
REM ============================================================

REM Step 1: Go shopping — get our toys plus the app-builder (PyInstaller)
pip install -r requirements.txt pyinstaller

REM Step 2: Squish everything into ONE file.
REM   --onefile  = one single .exe instead of a big messy folder
REM   --windowed = no scary black text window when the app opens
REM   --collect-all customtkinter = pack ALL of customtkinter's art supplies
pyinstaller --onefile --windowed --name "SKZ Countdown" ^
  --collect-all customtkinter skz_countdown.py

echo Done! Your app is at dist\"SKZ Countdown.exe"
pause