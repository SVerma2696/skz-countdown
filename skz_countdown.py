"""
Stray Kids — "This & That" Album Countdown

WHAT THIS PROGRAM DOES (the simple version):
  1. It knows the exact moment the album comes out.
  2. It looks at your computer's clock.
  3. It subtracts one from the other and shows you how long is left.
  4. It taps you on the shoulder (a notification) at big moments.

It also shows all 8 members lit up at once (click one to read about them),
the album tracklist, and buttons that jump straight to the album on Spotify,
Apple Music, and the Stray Kids shop. If you drop in more than one photo for
a member (or the group), the app shuffles between them over time — never
showing the same picture twice in a row. It runs on Windows, Mac, and Linux,
and keeps counting quietly in the background even when you close the window.

A note on the "engineering console" look: the section titles start with "//"
(that's how programmers write a note-to-self in code), the numbers use a
typewriter font like a digital readout, and thin red lines act like little
circuit traces. It's meant to look like a tidy control panel a computer
engineer would build.
"""

# ---- These are the "toolboxes" we borrow code from ----
import json          # lets us save settings as a little text file
import os            # lets us talk to folders and files
import random        # lets us shuffle photos so they don't repeat in a row
import shlex         # helps write safe commands for Linux
import subprocess    # lets us run other programs (like notifications)
import sys           # tells us which operating system we're on
import threading     # lets us do two things at once
import webbrowser    # lets us open a web page, like our GitHub repo
from datetime import datetime, timezone   # tools for working with time
from zoneinfo import ZoneInfo              # tools for time zones

import customtkinter as ctk   # the toolbox that draws our pretty window

# Try to grab the notification toolbox. If it's not installed,
# we remember that so we don't crash later.
try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

# Try to grab the "drawing pictures" toolbox (Pillow). We use it to show
# the logos, the member photos, the tracklist, the tray icon, the seven-
# segment countdown digits, and the faint circuit-board background.
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Which computer are we running on? Only one of these will be True.
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# The "tray" is the little row of icons by your clock.
# We use it on Windows and Linux. Macs use the Dock instead,
# because the tray toolbox and the window toolbox fight over
# who gets to be in charge on a Mac.
TRAY_AVAILABLE = False
if not IS_MACOS and PIL_AVAILABLE:
    try:
        import pystray   # draws the tray icon
        TRAY_AVAILABLE = True
    except ImportError:
        pass  # no tray toolbox? That's okay, the app still works.

# ---------------- The important facts about the album ----------------

APP_NAME = "SKZ Countdown"
APP_VERSION = "1.3.1"
APP_ID = "skz-countdown"
ALBUM_NAME = 'Stray Kids — "This & That"'
REPO_URL = "https://github.com/SVerma2696/skz-countdown"  # our home on GitHub

# The two picture files that live right next to this script.
SKZ_LOGO_FILE = "skz-logo.png"   # the Stray Kids photo (window icon + header)
TT_LOGO_FILE = "t&t-logo.png"    # the "This & That" title picture
TRACKLIST_FILE = "tracklist.png"  # the picture of the song list

# THE moment everything counts down to:
# August 7, 2026 at 1:00 PM in Korea (where the album releases).
RELEASE_DT = datetime(2026, 8, 7, 13, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))

# Ask the computer what time zone IT lives in,
# then figure out what the Korean release moment is in LOCAL time.
LOCAL_TZ = datetime.now().astimezone().tzinfo
RELEASE_LOCAL = RELEASE_DT.astimezone(LOCAL_TZ)

# The 8 members, in order. Each one is (display name, placeholder file name).
# The app looks for a real photo with that file name in assets/members/;
# if it can't find one, it draws a clean placeholder with the name instead.
MEMBERS = [
    ("Bang Chan", "1_bang_chan.png"),
    ("Lee Know", "2_lee_know.png"),
    ("Changbin", "3_changbin.png"),
    ("Hyunjin", "4_hyunjin.png"),
    ("Han", "5_han.png"),
    ("Felix", "6_felix.png"),
    ("Seungmin", "7_seungmin.png"),
    ("I.N", "8_in.png"),
]

# A short, friendly blurb for each member — shown in their pop-up window
# when you click their card.
MEMBER_DESCRIPTIONS = {
    "Bang Chan": (
        "The leader of Stray Kids. Born in Sydney, Australia, Chan is a "
        "main producer and vocalist who leads the group's in-house "
        "production team, 3RACHA."
    ),
    "Lee Know": (
        "Main dancer and vocalist, known by his real name Minho. Famous "
        "for his sharp, precise choreography and his beloved cats."
    ),
    "Changbin": (
        "A rapper and producer, and one third of 3RACHA alongside Bang "
        "Chan and Han. Known for his deep voice and powerful stage "
        "presence."
    ),
    "Hyunjin": (
        "A dancer and vocalist who also contributes to the group's "
        "choreography and fashion direction."
    ),
    "Han": (
        "Rapper, producer, and the third member of 3RACHA. Full name Han "
        "Jisung — he writes and composes many of Stray Kids' title tracks."
    ),
    "Felix": (
        "A rapper born in Sydney, Australia, known for his distinctively "
        "low voice and bright, high-energy personality."
    ),
    "Seungmin": (
        "A vocalist often praised for his stable, powerful live singing "
        "and dry sense of humor."
    ),
    "I.N": (
        "The youngest member (the group's 'maknae') and a vocalist, full "
        "name Yang Jeongin — known for a low, steady voice for his age."
    ),
}

# The buttons that jump to the album online.
# Each one is (label, web address, brand color, logo file name).
ALBUM_LINKS = [
    ("Stray Kids Shop",
     "https://straykidsshop.com/collections/this-that",
     "#141416", "store.png"),
    ("Apple Music",
     "https://music.apple.com/us/album/this-that/6781751949",
     "#FA243C", "apple_music.png"),
    ("Spotify",
     "https://open.spotify.com/album/46TYlDjLrEsOLFgxfxNiUy",
     "#1DB954", "spotify.png"),
]

# Where should we keep our little settings file?
# Every operating system has a "proper drawer" for app settings.
if IS_WINDOWS:
    _cfg_dir = os.getenv("APPDATA") or os.path.expanduser("~")
elif IS_MACOS:
    _cfg_dir = os.path.expanduser("~/Library/Application Support")
else:
    _cfg_dir = os.getenv("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
os.makedirs(_cfg_dir, exist_ok=True)   # make the drawer if it's missing
SETTINGS_FILE = os.path.join(_cfg_dir, "skz_countdown_settings.json")

# The big moments we send notifications for.
# Each one is: (its name in settings, what to say, seconds before release)
MILESTONES = [
    ("notify_1w", "1 week to go", 7 * 24 * 3600),   # 7 days early
    ("notify_1d", "1 day to go", 24 * 3600),        # 1 day early
    ("notify_1h", "1 hour to go", 3600),            # 1 hour early
    ("notify_release", "IT'S OUT!", 0),             # the moment itself!
]

# The colors we paint with (written as computer color codes).
# Black, white, and Stray Kids' red — clean and sleek, like a control panel.
# RED IS THE ONE ACCENT: we try hard to only use it for the thing that's
# actually active or important right now (the ticking seconds, a hovered
# member, the one primary button) — never just to decorate a box. Black
# and white do the rest of the work; that restraint is what makes it look
# "designed" instead of "colorful."
ACCENT = "#E4002B"        # Stray Kids red — the one accent color
ACCENT_HOVER = "#FF2E4F"  # a lighter red for when the mouse hovers
STATUS_BAR_BG = "#141416"  # the status bar is ALWAYS this near-black —
                            # it's a fixed "terminal strip", not part of
                            # the light/dark page theme below

# Two full "looks" for the rest of the app — the Settings window has a
# switch that flips between them. Everything else (ACCENT, fonts) stays
# the same in both; only the page's own black/white balance changes.
THEMES = {
    "light": dict(
        BG_MAIN="#FFFFFF",       # crisp white window background
        BG_CARD="#F7F7F9",       # faintest gray, so boxes stand out
        CARD_BORDER="#E2E2E7",   # neutral outline for ordinary boxes
        DIVIDER="#E7E7EB",       # the thin line next to "// SECTION" titles
        FG_DIM="#6b6b76",        # medium gray for small text
        FG_STRONG="#141416",     # near-black for text that should pop
        CHIP_DARK="#141416",     # dark "chip" buttons (GitHub / Quit)
        CHIP_TEXT="#FFFFFF",     # their text/outline
        # An "unlit" LED segment — a faint tint of the SAME red as the lit
        # segments (not a mismatched gray), just like a real LED display
        # shows the rest of the "8" shape as a dim version of its own color.
        SEG_OFF="#F7DEE1",
    ),
    "dark": dict(
        BG_MAIN="#0D0D0F",       # near-black window background
        BG_CARD="#18181B",       # slightly lighter, so boxes stand out
        CARD_BORDER="#2A2A30",   # neutral outline for ordinary boxes
        DIVIDER="#2A2A30",       # the thin line next to "// SECTION" titles
        FG_DIM="#9a9aa2",        # soft gray for small text
        FG_STRONG="#FFFFFF",     # bright white for text that should pop
        CHIP_DARK="#F2F2F2",     # light "chip" buttons (inverted, for contrast)
        CHIP_TEXT="#141416",     # their text/outline
        SEG_OFF="#3A171C",       # a dim red tint, this time on a dark card
    ),
}

# How often to look at the clock (in milliseconds).
# A typewriter-style font makes the numbers feel like a digital readout.
# If a computer doesn't have this exact font, it just falls back quietly.
MONO_FONT = "Consolas" if IS_WINDOWS else "Menlo" if IS_MACOS else "monospace"

TICK_VISIBLE_MS = 1000    # window open: every 1 second (so seconds tick)
TICK_HIDDEN_MS = 15000    # window hidden: every 15 seconds (saves work,
                          # because nobody can see the seconds anyway)
MEMBER_CYCLE_MS = 3500    # give a member a fresh photo every 3.5 seconds
GROUP_CYCLE_MS = 6000     # swap the group photo every 6 seconds
BOOT_TYPE_MS = 18         # how fast the boot line "types" itself out
BOOT_BLINK_MS = 600       # how often the boot cursor blinks after that


def resource_path(filename):
    """Find a file we bundled with the app, like a logo picture.

    When PyInstaller packs us into one .exe/.app, it unzips extra files
    into a secret temporary folder named in sys._MEIPASS. When we're just
    a plain .py script, the file is simply sitting right next to us.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


# ---------------- Saving and loading settings ----------------


def load_settings():
    """Read our settings file. If it doesn't exist, use friendly defaults."""
    # Start with everything turned ON.
    defaults = {k: True for k, _, _ in MILESTONES}
    defaults["notifications_enabled"] = True
    defaults["fired"] = []   # a list of alerts we already sent (no repeats!)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        defaults.update(data)  # replace defaults with what was saved
    except (OSError, json.JSONDecodeError):
        pass  # no file yet, or it's broken — defaults are fine
    return defaults


def save_settings(settings):
    """Write our settings to the file so they survive a restart."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass  # if the disk says no, don't crash over it


# ---------------- "Start at login" (every OS does this differently) ----------


def get_launch_command():
    """Figure out the exact command the computer should run at login."""
    if getattr(sys, "frozen", False):
        # We are a packaged .exe/.app — just run ourselves.
        return [sys.executable]
    # We are a plain .py script — run "python our_script.py".
    script = os.path.abspath(__file__)
    exe = sys.executable
    if IS_WINDOWS:
        # pythonw.exe = python without a black console window popping up
        exe = exe.replace("python.exe", "pythonw.exe")
    return [exe, script]


# Where each OS keeps its "run this at login" notes:
_MAC_PLIST = os.path.expanduser(f"~/Library/LaunchAgents/com.{APP_ID}.plist")
_LINUX_DESKTOP = os.path.join(
    os.getenv("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
    "autostart", f"{APP_ID}.desktop",
)


def is_startup_enabled():
    """Check: did we already ask the computer to start us at login?"""
    if IS_WINDOWS:
        import winreg  # Windows keeps startup notes in the "registry"
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ,
            )
            winreg.QueryValueEx(key, APP_NAME)  # is our note there?
            winreg.CloseKey(key)
            return True
        except OSError:
            return False  # no note found
    if IS_MACOS:
        return os.path.exists(_MAC_PLIST)      # Mac: is our note file there?
    return os.path.exists(_LINUX_DESKTOP)      # Linux: is our note file there?


def set_startup(enable):
    """Turn 'start at login' on or off, the way THIS computer likes."""
    cmd = get_launch_command()

    if IS_WINDOWS:
        # Windows: write (or erase) a note in the registry.
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        try:
            if enable:
                value = subprocess.list2cmdline(cmd)
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, value)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass  # nothing to erase
        finally:
            winreg.CloseKey(key)
        return

    if IS_MACOS:
        # Mac: write (or delete) a small "LaunchAgent" instruction file.
        if enable:
            os.makedirs(os.path.dirname(_MAC_PLIST), exist_ok=True)
            args = "\n".join(f"        <string>{c}</string>" for c in cmd)
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{APP_ID}</string>
    <key>ProgramArguments</key>
    <array>
{args}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            with open(_MAC_PLIST, "w", encoding="utf-8") as f:
                f.write(plist)
        else:
            try:
                os.remove(_MAC_PLIST)
            except FileNotFoundError:
                pass
        return

    # Linux: write (or delete) an "autostart" instruction file.
    if enable:
        os.makedirs(os.path.dirname(_LINUX_DESKTOP), exist_ok=True)
        entry = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            f"Exec={shlex.join(cmd)}\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        with open(_LINUX_DESKTOP, "w", encoding="utf-8") as f:
            f.write(entry)
    else:
        try:
            os.remove(_LINUX_DESKTOP)
        except FileNotFoundError:
            pass


# ---------------- Sending notifications ----------------


def _applescript_escape(s):
    """Make text safe to put inside Mac notification commands."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _powershell_escape(s):
    """Make text safe to put inside a PowerShell double-quoted string."""
    return s.replace("`", "``").replace('"', '`"').replace("$", "`$")


def _windows_toast(title, message):
    """Ask Windows 10/11 directly to show a real toast notification.

    Windows' older "balloon tip" trick (what the plyer toolbox uses) often
    shows nothing at all on modern Windows — and doesn't tell us it failed!
    So on Windows we ask the operating system for a real toast ourselves,
    the same way we ask macOS and Linux directly further down.
    """
    script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($template.CreateTextNode("{_powershell_escape(title)}")) | Out-Null
$textNodes.Item(1).AppendChild($template.CreateTextNode("{_powershell_escape(message)}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{_powershell_escape(APP_NAME)}").Show($toast)
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive",
         "-WindowStyle", "Hidden", "-Command", script],
        check=False, capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("PowerShell toast failed")


def send_notification(title, message):
    """Show a little pop-up message in the corner of the screen.

    We do it on a helper thread so the window never freezes while
    the notification is being delivered. Each operating system gets
    the plan most likely to actually work for IT:
      Windows: a real Windows toast first, plyer as backup.
      macOS / Linux: the plyer toolbox first, the OS's own tool as backup.
    """

    def _worker():
        if IS_WINDOWS:
            try:
                _windows_toast(title, message)
                return  # it worked, we're done
            except Exception:
                pass  # didn't work — fall through to plyer below

        if PLYER_AVAILABLE:
            try:
                plyer_notification.notify(
                    title=title, message=message,
                    app_name=APP_NAME, timeout=10,
                )
                return  # it worked, we're done
            except Exception:
                pass  # didn't work — try the OS's own way below

        # Last resort: ask the operating system directly.
        try:
            if IS_MACOS:
                script = (
                    f'display notification "{_applescript_escape(message)}" '
                    f'with title "{_applescript_escape(title)}"'
                )
                subprocess.run(["osascript", "-e", script], check=False,
                               capture_output=True)
            elif IS_LINUX:
                subprocess.run(["notify-send", title, message], check=False,
                               capture_output=True)
        except Exception:
            pass  # a failed pop-up should NEVER crash the countdown

    threading.Thread(target=_worker, daemon=True).start()


# ---------------- Drawing placeholder pictures ----------------
# When a real photo is missing, we draw a clean stand-in so the app always
# looks finished. These are made ONCE and remembered, so they don't eat RAM.


def _load_font(size):
    """Try to load a nice bold font for our placeholders; fall back if we
    can't find one (every computer is a little different)."""
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Arialbd.ttf",
                 "Helvetica.ttc", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()   # last-resort tiny built-in font


def _make_member_placeholder(name, size, border_color):
    """Draw a simple portrait stand-in (a soft face circle + a hint).

    We do NOT write the name here, because the app already shows the name on
    a label right under the card — writing it twice would look repeated."""
    w, h = size
    img = Image.new("RGB", (w, h), "#ECECEF")
    d = ImageDraw.Draw(img)
    # A big soft circle where the face would go.
    pad = int(w * 0.20)
    top = int(h * 0.16)
    d.ellipse([pad, top, w - pad, top + (w - 2 * pad)], fill="#D9D9DE")
    # A thin neutral frame — red is saved for the active/important thing,
    # so a placeholder box doesn't get it.
    d.rectangle([1, 1, w - 2, h - 2], outline=border_color, width=2)
    # A tiny "add photo here" hint near the bottom.
    small = _load_font(max(9, int(w * 0.085)))
    hint = "photo →"
    tw = d.textlength(hint, font=small)
    d.text(((w - tw) / 2, h - int(h * 0.20)), hint, fill="#9a9aa2", font=small)
    return img


def _make_group_placeholder(index, size, border_color):
    """Draw a simple wide 'group photo' stand-in."""
    w, h = size
    img = Image.new("RGB", (w, h), "#E4E4E8")
    d = ImageDraw.Draw(img)
    d.rectangle([1, 1, w - 2, h - 2], outline=border_color, width=2)
    font = _load_font(max(16, int(h * 0.14)))
    text = f"GROUP PHOTO {index}"
    tw = d.textlength(text, font=font)
    d.text(((w - tw) / 2, (h - font.size) / 2 - 8), text,
           fill="#141416", font=font)
    small = _load_font(max(11, int(h * 0.08)))
    hint = "drop 1.png, 2.png ... in assets/group/"
    tw2 = d.textlength(hint, font=small)
    d.text(((w - tw2) / 2, (h + font.size) / 2), hint,
           fill="#9a9aa2", font=small)
    return img


def _make_logo_placeholder(label, color, size):
    """Draw a simple lettered chip to stand in for a brand logo.

    This is NOT the real trademarked logo — just a neutral placeholder so
    the button looks finished. Drop the official logo into assets/logos/
    to replace it (see assets/logos/README.txt)."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, w - 1, h - 1], fill=color)   # a colored circle
    letter = label[0].upper()
    font = _load_font(int(h * 0.55))
    tw = d.textlength(letter, font=font)
    d.text(((w - tw) / 2, (h - font.size) / 2 - 2), letter,
           fill="#FFFFFF", font=font)
    return img


# ---------------- Drawing the seven-segment countdown digits ----------------
# Real digital clocks light up little bars to make each digit — this draws
# that same look ourselves, instead of just using a computer font.

# Which of the 7 bars (a=top, b=upper-right, c=lower-right, d=bottom,
# e=lower-left, f=upper-left, g=middle) are lit for each digit 0-9.
_SEVEN_SEG = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg",
}

# We draw each digit this many times bigger than it's shown on screen,
# then let CTkImage shrink it back down. Windows often displays windows a
# little bigger than "actual size" (DPI scaling) — starting from a much
# bigger, crisp picture means that stretch always shrinks a picture down
# (sharp) instead of blowing a small one up (blurry).
_SEG_SUPERSAMPLE = 4

# How big one digit is on screen. Bigger than a plain font would need,
# since a blocky LED digit needs some size to actually read clearly.
DIGIT_W = 78
DIGIT_H = 134


def _segment_bar(orientation, x0, y0, x1, y1, t):
    """One LED "bar": a hexagon with pointed ends, not a plain rectangle —
    this is the classic seven-segment-display shape (see any real digital
    clock), and it's what lets neighboring bars meet at a corner cleanly
    instead of their square corners visibly overlapping each other.

    orientation "h": the bar runs from (x0,y0) to (x1,y0) — y1 is unused.
    orientation "v": the bar runs from (x0,y0) to (x0,y1) — x1 is unused.
    t is the bar's full thickness.
    """
    ht = t / 2
    if orientation == "h":
        yc = y0
        return [
            (x0, yc), (x0 + ht, yc - ht), (x1 - ht, yc - ht),
            (x1, yc), (x1 - ht, yc + ht), (x0 + ht, yc + ht),
        ]
    xc = x0
    return [
        (xc, y0), (xc + ht, y0 + ht), (xc + ht, y1 - ht),
        (xc, y1), (xc - ht, y1 - ht), (xc - ht, y0 + ht),
    ]


def _seven_segment_bars(w, h):
    """Work out the 7 bar polygons for one digit cell of size w×h — the
    same layout every digit shares, just colored differently per digit."""
    # Separate margins for each axis — the cell is much taller than it is
    # wide, so a margin based on width alone would leave almost no gap
    # above/below the digit.
    margin_x = max(3, int(w * 0.12))
    margin_y = max(3, int(h * 0.10))
    left, right = margin_x, w - margin_x
    top, bottom = margin_y, h - margin_y
    mid = (top + bottom) / 2
    t = max(4, int((right - left) * 0.42))   # how thick (wide) each bar is
    notch = t * 0.22   # just enough gap that corners don't overlap
    return {
        "a": _segment_bar("h", left + notch, top, right - notch, 0, t),
        "g": _segment_bar("h", left + notch, mid, right - notch, 0, t),
        "d": _segment_bar("h", left + notch, bottom, right - notch, 0, t),
        "f": _segment_bar("v", left, top + notch, 0, mid - notch, t),
        "b": _segment_bar("v", right, top + notch, 0, mid - notch, t),
        "e": _segment_bar("v", left, mid + notch, 0, bottom - notch, t),
        "c": _segment_bar("v", right, mid + notch, 0, bottom - notch, t),
    }


def _seven_segment_digit(digit, w, h, lit_color, off_color):
    """Draw one digit as a classic seven-segment "LED" glyph — flat, crisp
    bars, no blur or shadow, the same way a real LED display looks.

    Segments that are OFF are still drawn — as a dim tint of the SAME red
    as the lit ones (see SEG_OFF), the way a real LED display shows the
    rest of the "8" shape dimly powered-down rather than gone, so a "1"
    reads cleanly next to that ghost instead of a mismatched gray block
    cutting into the lit strokes.
    """
    bars = _seven_segment_bars(w, h)
    lit_names = set(_SEVEN_SEG.get(digit, ""))

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for name, poly in bars.items():
        d.polygon(poly, fill=lit_color if name in lit_names else off_color)
    return img


# ---------------- The window itself ----------------


class CountdownApp(ctk.CTk):
    """The main window. Everything the user sees lives in here."""

    def __init__(self):
        super().__init__()  # build the basic empty window first
        self.settings = load_settings()
        self.tray_icon = None          # the tray icon (made later, maybe)
        self.settings_win = None       # the pop-up settings window (if open)
        self._bg_tip_shown = False     # did we explain the tray yet?
        self._startup_check_done = False  # lets us send "catch-up" alerts
        self._tick_job = None          # the "come back later" reminder ID
        self._member_job = None        # reminder ID for the member photo shuffle
        self._group_job = None         # reminder ID for the group photo swap
        self._last_shown = {}          # what each number label says right now
        self._celebrating = False      # did we already switch to party mode?
        self._img_cache = {}           # remember finished pictures (CTkImage)
        self._img_cache_raw = {}       # remember raw PIL pictures (digits, PCB)
        self._group_index = 0          # which group photo is showing
        self._boot_generation = 0      # lets us cancel an old boot animation
        # (which photo each member is showing lives in self._member_current,
        # set up in _build_members once we know how many photos each has)

        # Dark mode or light mode? Read the choice we saved last time.
        self.dark_mode = bool(self.settings.get("dark_mode", False))
        self._apply_theme()   # works out self.BG_MAIN, self.FG_STRONG, etc.

        self.title(f"{APP_NAME} — This & That")
        self.minsize(880, 600)

        # MEMORY SAVER: make our fonts ONCE and reuse them forever.
        # (Making a new font every second would slowly eat RAM.)
        self._font_status = ctk.CTkFont(size=14)
        self._font_celebrate = ctk.CTkFont(size=20, weight="bold")
        self._font_section = ctk.CTkFont(family=MONO_FONT, size=13,
                                         weight="bold")
        self._font_num = ctk.CTkFont(family=MONO_FONT, size=34, weight="bold")
        self._font_unit = ctk.CTkFont(size=11, weight="bold")
        self._font_mono_small = ctk.CTkFont(family=MONO_FONT, size=10)

        self._load_logos()   # open our logo + title pictures, if we can
        self._build_ui()     # draw everything

        # SIZE THE WINDOW TO FIT WHAT WE ACTUALLY DREW, instead of guessing
        # a fixed pixel size: Windows' own "make everything bigger" display
        # setting scales up every widget we asked for by some factor we
        # don't control, so a fixed guess can end up too small and clip the
        # right edge. Asking the content frame what width it actually
        # needs, AFTER drawing everything, always fits — on any screen, at
        # any DPI setting. (Height stays a fixed, reasonable size — the
        # page scrolls vertically on purpose, so extra height just means
        # less scrolling, never anything clipped.)
        self.update_idletasks()
        fit_w = min(self.content.winfo_reqwidth() + 50,
                   self.winfo_screenwidth() - 80)
        fit_h = min(820, self.winfo_screenheight() - 120)
        self.geometry(f"{fit_w}x{fit_h}")

        # When the user clicks the X, run OUR function instead of quitting.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if TRAY_AVAILABLE:
            self._start_tray()   # put our little icon by the clock
        if IS_MACOS:
            # On a Mac, clicking the Dock icon should re-open our window.
            try:
                self.createcommand("tk::mac::ReopenApplication",
                                   self._show_window)
            except Exception:
                pass

        self._tick()            # start the clock ticking!
        self._cycle_members()   # start swapping member photos
        self._cycle_group()     # start swapping the group photo

    # ---------- Light mode / dark mode ----------

    def _apply_theme(self):
        """Work out which colors to paint with, based on light/dark mode.

        Everything else in the app reads colors off of "self" (like
        self.BG_MAIN) instead of a fixed value, so flipping this and
        redrawing the window is all it takes to re-theme everything.
        """
        theme = THEMES["dark" if self.dark_mode else "light"]
        for key, value in theme.items():
            setattr(self, key, value)
        ctk.set_appearance_mode("dark" if self.dark_mode else "light")

    def _on_dark_mode_toggled(self):
        """The 'Dark mode' switch in Settings was flipped."""
        self.dark_mode = bool(self.dark_mode_switch.get())
        self.settings["dark_mode"] = self.dark_mode
        save_settings(self.settings)
        self._apply_theme()
        # Placeholder pictures have the OLD border color baked in — throw
        # away the picture cache so they get redrawn in the new theme.
        self._img_cache.clear()
        self._img_cache_raw.clear()
        # The settings window is about to be torn down along with
        # everything else, so close it first.
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.destroy()
        self.settings_win = None
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Tear down and redraw the whole window.

        Re-coloring every single widget by hand when the theme changes
        would be a mess to keep correct — instead we just throw the old
        page away and build a fresh one, the same way it looked the first
        time the app opened.
        """
        for job_name in ("_tick_job", "_member_job", "_group_job"):
            job_id = getattr(self, job_name)
            if job_id is not None:
                self.after_cancel(job_id)
                setattr(self, job_name, None)
        self.page.destroy()
        self.configure(fg_color=self.BG_MAIN)
        # The countdown boxes are BRAND NEW widgets that still just say
        # "--" — forget what we last painted, or _tick() will wrongly
        # think nothing changed and leave them showing "--" forever.
        self._last_shown = {}
        self._build_ui()
        self._tick()
        self._cycle_members()
        self._cycle_group()

    # ---------- Loading pictures (with a memory-saving cache) ----------

    def _get_image(self, path, size, kind, meta):
        """Return a ready-to-show picture, loading it only once.

        path : where the real photo would be (may not exist)
        size : how big to show it, as (width, height)
        kind : "member", "group", or "logo" — decides the placeholder style
        meta : extra info for the placeholder (a name, number, or (label,color))

        MEMORY SAVER: once we've made a picture, we keep it in self._img_cache
        and hand back the same one next time instead of rebuilding it.
        """
        cache_key = (path, size, kind)
        if cache_key in self._img_cache:
            return self._img_cache[cache_key]
        if not PIL_AVAILABLE:
            return None

        pic = None
        try:
            if path and os.path.exists(path):
                pic = Image.open(path)           # a real photo exists — use it!
                if pic.mode not in ("RGB", "RGBA"):
                    pic = pic.convert("RGBA")
                # SHARPNESS: shrink with a high-quality filter ourselves.
                # Image.LANCZOS keeps real photos crisp instead of blurry.
                pic = pic.resize(size, Image.LANCZOS)
        except Exception:
            pic = None
        if pic is None:                          # no photo? draw a placeholder
            if kind == "member":
                pic = _make_member_placeholder(meta, size, self.CARD_BORDER)
            elif kind == "group":
                pic = _make_group_placeholder(meta, size, self.CARD_BORDER)
            else:  # logo
                label, color = meta
                pic = _make_logo_placeholder(label, color, size)

        image = ctk.CTkImage(light_image=pic, dark_image=pic, size=size)
        self._img_cache[cache_key] = image
        return image

    # ---------- The seven-segment countdown digits ----------

    def _digit_glyphs(self, w, h):
        """Return the 10 digit pictures (0-9), drawing each one only once
        and reusing it forever after (just like our other picture caches)
        — recomposing a whole number is then just pasting a couple of
        these together, which is cheap enough to do every tick.

        SHARPNESS: CustomTkinter secretly re-scales every picture we hand
        it by whatever "make everything bigger" display-scaling factor
        Windows is using (often 125%-150%) — and it does that resize with
        a plain filter that looks noticeably soft. So instead of drawing
        at the plain on-screen size and letting CTkImage do that resize
        alone, we draw at the REAL final pixel size ourselves (on-screen
        size × that scaling factor) using a sharp filter — so whatever
        CTkImage does afterwards is a no-op, not a second blurry resize.
        We still draw _SEG_SUPERSAMPLE times bigger than even THAT and
        shrink down with Image.LANCZOS, for a crisp result either way.
        """
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        real_w, real_h = max(1, round(w * scale)), max(1, round(h * scale))
        cache_key = ("digitset", real_w, real_h, self.dark_mode)
        if cache_key not in self._img_cache_raw:
            big_w, big_h = real_w * _SEG_SUPERSAMPLE, real_h * _SEG_SUPERSAMPLE
            self._img_cache_raw[cache_key] = {
                ch: _seven_segment_digit(ch, big_w, big_h, ACCENT, self.SEG_OFF)
                    .resize((real_w, real_h), Image.LANCZOS)
                for ch in "0123456789"
            }
        return self._img_cache_raw[cache_key]

    def _number_image(self, text, w, h, gap=6):
        """Turn a short string of digits into one seven-segment picture."""
        glyphs = self._digit_glyphs(w, h)
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        real_w = max(1, round(w * scale))
        real_h = max(1, round(h * scale))
        real_gap = max(1, round(gap * scale))
        total_real_w = len(text) * real_w + (len(text) - 1) * real_gap
        canvas = Image.new("RGBA", (total_real_w, real_h), (0, 0, 0, 0))
        x = 0
        for ch in text:
            canvas.alpha_composite(glyphs.get(ch, glyphs["0"]), (x, 0))
            x += real_w + real_gap
        total_w = len(text) * w + (len(text) - 1) * gap   # logical size
        return ctk.CTkImage(light_image=canvas, dark_image=canvas,
                            size=(total_w, h))

    # ---------- The faint circuit-board background ----------

    def _pcb_pattern_image(self, w, h):
        """Draw a very faint dot-grid — a subtle 'circuit board' texture.

        Drawn once and cached (like our other pictures), so it costs
        nothing extra on every tick — it's just a picture sitting there.
        """
        cache_key = ("pcb", w, h, self.dark_mode)
        if cache_key not in self._img_cache_raw:
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            # A faint red dot at every grid intersection — barely there,
            # just enough to hint at a circuit board underneath.
            alpha = 22 if self.dark_mode else 14
            dot_color = (228, 0, 43, alpha)
            step = 22
            for y in range(0, h, step):
                for x in range(0, w, step):
                    d.ellipse([x, y, x + 2, y + 2], fill=dot_color)
            self._img_cache_raw[cache_key] = img
        return self._img_cache_raw[cache_key]

    def _paint_pcb_background(self, frame, w=900, h=170):
        """Put the faint dot-grid picture behind a frame's content, like a
        circuit board peeking through underneath — a cheap, one-time-drawn
        decoration, not redrawn per frame."""
        if not PIL_AVAILABLE:
            return
        pic = self._pcb_pattern_image(w, h)
        img = ctk.CTkImage(light_image=pic, dark_image=pic, size=(w, h))
        bg_label = ctk.CTkLabel(frame, text="", image=img)
        bg_label.place(relx=0.5, rely=0, anchor="n")
        bg_label.lower()   # keep it BEHIND the real content in the frame

    def _find_member_photos(self, file_name):
        """Find every real photo we have for one member.

        Looks for a FOLDER of numbered photos first (e.g.
        assets/members/1_bang_chan/1.png, 2.png, ...) so we can cycle
        through several; if there's no folder, falls back to the single
        flat file (e.g. assets/members/1_bang_chan.png); if neither
        exists, returns an empty list and the app draws a placeholder.
        """
        base = os.path.splitext(file_name)[0]
        folder = resource_path(os.path.join("assets", "members", base))
        paths = []
        if os.path.isdir(folder):
            i = 1
            while True:
                found = None
                for ext in (".png", ".jpg", ".jpeg"):
                    candidate = os.path.join(folder, f"{i}{ext}")
                    if os.path.exists(candidate):
                        found = candidate
                        break
                if not found:
                    break
                paths.append(found)
                i += 1
        if not paths:
            flat = resource_path(os.path.join("assets", "members", file_name))
            if os.path.exists(flat):
                paths.append(flat)
        return paths

    def _member_photo(self, index, photo_index, size):
        """Get one specific photo for one member, at a given size (or
        their placeholder, if that member has no real photo yet)."""
        name, file_name = MEMBERS[index]
        paths = self._member_photo_paths[index]
        # Even with no real photo, we pass a stable (non-existent) path so
        # every member still gets their OWN cached placeholder picture.
        path = paths[photo_index] if paths else resource_path(
            os.path.join("assets", "members", file_name))
        return self._get_image(path, size, "member", name)

    def _group_photo(self, index, size):
        """Get a group photo by number (or its placeholder)."""
        path = resource_path(os.path.join("assets", "group", f"{index}.png"))
        return self._get_image(path, size, "group", index)

    def _logo_image(self, file_name, label, color, size):
        """Get a brand/GitHub logo (or a simple lettered placeholder)."""
        path = resource_path(os.path.join("assets", "logos", file_name))
        return self._get_image(path, size, "logo", (label, color))

    def _count_group_photos(self):
        """How many real group photos did the user add? (At least 1, so the
        placeholder always shows.)"""
        folder = resource_path(os.path.join("assets", "group"))
        count = 0
        try:
            for i in range(1, 21):   # check 1.png ... 20.png
                if os.path.exists(os.path.join(folder, f"{i}.png")):
                    count += 1
                else:
                    break
        except Exception:
            pass
        return max(count, 1)

    def _load_logos(self):
        """Open the Stray Kids photo and the "This & That" title picture."""
        self.skz_logo_image = None   # the round Stray Kids photo (header)
        self.skz_logo_source = None  # the original picture (for the tray icon)
        self.tt_logo_image = None    # the "This & That" title picture
        self._icon_photos = []       # crisp small copies, for every window
        self._icon_ico_path = None   # a real .ico file (Windows only)
        if not PIL_AVAILABLE:
            return

        try:
            skz_pic = Image.open(resource_path(SKZ_LOGO_FILE)).convert("RGBA")
            self.skz_logo_source = skz_pic

            # MEMORY SAVER / SHARPNESS: shrink with a high-quality filter
            # OURSELVES before handing the picture to CTkImage. Letting the
            # widget toolkit stretch a big picture down to a small box uses
            # a blurrier filter and can look pixelated — doing it first
            # with Image.LANCZOS (a much crisper filter) fixes that.
            header_pic = skz_pic.resize((76, 76), Image.LANCZOS)
            self.skz_logo_image = ctk.CTkImage(
                light_image=header_pic, dark_image=header_pic, size=(76, 76))

            # Make a handful of ready-made small sizes for title bars and
            # taskbars. Giving Windows several crisp, exact-size copies
            # (instead of one huge picture it has to shrink itself) is what
            # keeps every window's icon looking sharp instead of blocky.
            self._icon_photos = [
                ImageTk.PhotoImage(skz_pic.resize((s, s), Image.LANCZOS))
                for s in (16, 20, 24, 32, 40, 48, 64)
            ]

            if IS_WINDOWS:
                # customtkinter secretly swaps the titlebar icon back to its
                # own logo unless we've set an .ico ourselves — so we do.
                # A generous list of sizes means Windows almost always finds
                # an exact match instead of stretching a mismatched one.
                self._icon_ico_path = os.path.join(
                    _cfg_dir, "skz_countdown_icon.ico")
                ico_sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
                skz_pic.save(
                    self._icon_ico_path, format="ICO",
                    sizes=[(s, s) for s in ico_sizes],
                )

            self._set_window_icon(self)
        except Exception:
            pass  # a missing picture should never crash the countdown

        try:
            tt_pic = Image.open(resource_path(TT_LOGO_FILE))
            width, height = tt_pic.size
            target_h = 66
            target_w = int(width * (target_h / height))
            tt_pic = tt_pic.resize((target_w, target_h), Image.LANCZOS)
            self.tt_logo_image = ctk.CTkImage(
                light_image=tt_pic, dark_image=tt_pic,
                size=(target_w, target_h))
        except Exception:
            pass

    def _set_window_icon(self, window):
        """Put the Stray Kids picture in one window's title bar/taskbar spot.

        Every separate window — the main one, Settings, a member's pop-up —
        has to be told about the icon on its own; Windows doesn't share it
        automatically between windows.
        """
        if not self._icon_photos:
            return
        try:
            window.iconphoto(True, *self._icon_photos)
            if IS_WINDOWS and self._icon_ico_path:
                window.iconbitmap(self._icon_ico_path)
        except Exception:
            pass  # a window without our icon should never crash the app

    # ---------- Opening web links ----------

    def _open_url(self, url):
        """Open any web address in the person's normal web browser."""
        webbrowser.open(url)

    # ---------- Small building-block helpers ----------

    def _section_header(self, parent, text):
        """A '// TITLE' row that looks like a code comment, with a line.

        The leading "//" is our one recurring slash motif, tying every
        section back to the same "circuit trace" divider style — that's
        why this text stays red even though most decoration doesn't.
        """
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text=text, font=self._font_section,
                     text_color=ACCENT).grid(row=0, column=0, sticky="w")
        ctk.CTkFrame(row, height=2, fg_color=self.DIVIDER,
                     corner_radius=0).grid(row=0, column=1, sticky="ew",
                                           padx=(12, 0), pady=(2, 0))
        return row

    # ---------- Drawing the whole window ----------

    def _build_ui(self):
        """Create everything you see, inside a scrollable centered column."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # A scrollable page, so even on a small screen you can scroll to see
        # everything — and on a huge full-screen monitor nothing gets cut off.
        self.page = ctk.CTkScrollableFrame(self, fg_color=self.BG_MAIN)
        self.page.grid(row=0, column=0, sticky="nsew")
        # Three columns: empty | content | empty. The empty sides grow on big
        # screens so the middle content stays centered and easy to read.
        self.page.grid_columnconfigure(0, weight=1)
        self.page.grid_columnconfigure(2, weight=1)

        # Everything lives inside this centered box. We let it size to its
        # content naturally (about 850px — the width of the 8-member row) and
        # the empty side columns keep it centered on big full-screen monitors.
        c = ctk.CTkFrame(self.page, fg_color="transparent")
        c.grid(row=0, column=1, sticky="n", pady=(6, 20))
        c.grid_columnconfigure(0, weight=1)
        self.content = c

        r = 0
        self._build_statusbar(c, r); r += 1
        self._build_header(c, r); r += 1
        self._build_countdown(c, r); r += 1
        self._build_album_links(c, r); r += 1
        self._build_members(c, r); r += 1
        self._build_group(c, r); r += 1
        self._build_tracklist(c, r); r += 1
        self._build_footer(c, r); r += 1

    def _build_statusbar(self, parent, row):
        """A thin monospace strip up top — the 'engineering console' touch.

        On launch it "boots up": one line of text types itself out, then a
        cursor block keeps softly blinking, like a real machine powering on.
        """
        bar = ctk.CTkFrame(parent, fg_color=STATUS_BAR_BG, corner_radius=6)
        bar.grid(row=row, column=0, sticky="ew", pady=(8, 14))
        bar.grid_columnconfigure(0, weight=1)
        self.boot_label = ctk.CTkLabel(
            bar, text="", anchor="w",
            font=ctk.CTkFont(family=MONO_FONT, size=11, weight="bold"),
            text_color="#FFFFFF",
        )
        self.boot_label.grid(row=0, column=0, sticky="ew", padx=(10, 10),
                             pady=6)
        self._start_boot_sequence()

    def _start_boot_sequence(self):
        """Kick off the typed 'booting up' line in the status bar."""
        self._boot_generation += 1   # cancels any earlier boot animation
        target = RELEASE_DT.strftime("%Y-%m-%dT%H:%M") + "+09:00"
        self._boot_full_text = (
            f"> booting {APP_NAME.lower().replace(' ', '-')} "
            f"v{APP_VERSION}... tz-sync OK... target: {target} [LOCKED]"
        )
        self._boot_progress = 0
        self._type_boot_line(self._boot_generation)

    def _type_boot_line(self, generation):
        """Reveal one more character of the boot line, then schedule the
        next one a moment later — cheap to do, and it looks like a machine
        booting up instead of text just appearing all at once."""
        if generation != self._boot_generation:
            return   # a newer boot sequence started (e.g. the theme changed)
        self._boot_progress += 1
        shown = self._boot_full_text[:self._boot_progress]
        cursor = "█" if self._boot_progress % 2 == 0 else " "
        self.boot_label.configure(text=shown + cursor)
        if self._boot_progress < len(self._boot_full_text):
            self.after(BOOT_TYPE_MS, lambda: self._type_boot_line(generation))
        else:
            self._blink_boot_cursor(generation, True)

    def _blink_boot_cursor(self, generation, on):
        """Once the line has finished typing, blink a soft cursor block
        forever — a tiny, cheap 'still alive' touch."""
        if generation != self._boot_generation:
            return
        self.boot_label.configure(text=self._boot_full_text + ("█" if on else " "))
        self.after(BOOT_BLINK_MS, lambda: self._blink_boot_cursor(generation, not on))

    def _build_header(self, parent, row):
        """The logo, title art, and the exact local release time."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=row, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        if self.skz_logo_image is not None:
            ctk.CTkLabel(header, text="", image=self.skz_logo_image).pack(
                pady=(0, 6))
        ctk.CTkLabel(
            header, text="STRAY KIDS", font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.FG_DIM,
        ).pack()

        if self.tt_logo_image is not None:
            ctk.CTkLabel(header, text="", image=self.tt_logo_image).pack(
                pady=(6, 0))
        else:
            ctk.CTkLabel(
                header, text='"This & That"',
                font=ctk.CTkFont(size=34, weight="bold"), text_color=ACCENT,
            ).pack(pady=(6, 0))

        ctk.CTkLabel(
            header, text="Drops August 7, 2026 · 1:00 PM KST — for STAY",
            font=ctk.CTkFont(size=13), text_color=self.FG_DIM,
        ).pack(pady=(6, 0))

        tz_name = RELEASE_LOCAL.strftime("%Z") or str(LOCAL_TZ)
        local_str = RELEASE_LOCAL.strftime(
            "%A, %B %d, %Y · %I:%M %p").replace(" 0", " ")
        ctk.CTkLabel(
            header, text=f"Your local time: {local_str} ({tz_name})",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=self.FG_STRONG,
        ).pack(pady=(2, 0))

        # A thin red circuit-trace line under the header.
        ctk.CTkFrame(header, height=2, fg_color=ACCENT, corner_radius=0).pack(
            fill="x", padx=60, pady=(14, 0))

    def _build_countdown(self, parent, row):
        """The five big number boxes: weeks, days, hours, minutes, seconds.

        The numbers themselves are drawn as flat, crisp seven-segment "LED"
        digits — see _seven_segment_digit(). Only the SECONDS box gets a
        red outline: it's the one thing that's always actively ticking, so
        it's the one box red is allowed to decorate.
        """
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", pady=(16, 6))
        wrap.grid_columnconfigure(0, weight=1)
        self._paint_pcb_background(wrap)   # a faint circuit-board texture

        units = ctk.CTkFrame(wrap, fg_color="transparent")
        units.grid(row=0, column=0)
        self.unit_labels = {}
        for i, name in enumerate(["WEEKS", "DAYS", "HOURS", "MINUTES",
                                  "SECONDS"]):
            is_seconds = name == "SECONDS"
            border = ACCENT if is_seconds else self.CARD_BORDER
            card = ctk.CTkFrame(units, corner_radius=14, fg_color=self.BG_CARD,
                                border_width=1, border_color=border, width=260)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            card.grid_propagate(False)
            card.configure(height=270)
            value = ctk.CTkLabel(card, text="--", font=self._font_num,
                                 text_color=self.FG_STRONG)
            value.pack(pady=(46, 0))
            ctk.CTkLabel(card, text=name, font=self._font_unit,
                         text_color=self.FG_DIM).pack(pady=(12, 20))
            self.unit_labels[name] = value

        self.status_label = ctk.CTkLabel(
            wrap, text="", font=self._font_status, text_color=self.FG_DIM)
        self.status_label.grid(row=1, column=0, pady=(12, 0))

    def _build_album_links(self, parent, row):
        """Buttons that jump straight to the album online.

        Each label ends with a small "↗" arrow — a quiet, consistent hint
        that the button leaves the app and opens a web page.
        """
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(20, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// GET THE ALBUM").grid(
            row=0, column=0, sticky="ew")

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.grid(row=1, column=0, pady=(12, 0))
        for i, (label, url, color, logo_file) in enumerate(ALBUM_LINKS):
            logo = self._logo_image(logo_file, label, color, (22, 22))
            btn = ctk.CTkButton(
                btns, text=f"  {label} ↗", image=logo, compound="left",
                fg_color=color, hover_color=color, text_color="#FFFFFF",
                font=ctk.CTkFont(family=MONO_FONT, size=13, weight="bold"),
                height=42, corner_radius=8,
                command=lambda u=url: self._open_url(u),
            )
            btn.grid(row=0, column=i, padx=6)

    def _build_members(self, parent, row):
        """8 columns — one per member — click one to learn more.

        Cards keep a plain neutral outline until you hover one: THEN it
        lights up red and its little mono tag flips to a "status readout" —
        red still means "the thing that's active right now," it's just the
        mouse deciding what's active instead of an automatic timer.
        """
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(24, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// MEMBERS · OT8  (click one to learn more)").grid(
            row=0, column=0, sticky="ew")

        strip = ctk.CTkFrame(box, fg_color="transparent")
        strip.grid(row=1, column=0, pady=(14, 0))

        # Work out (once) which real photos each member has, so we know
        # what to shuffle through later.
        self._member_photo_paths = [
            self._find_member_photos(file_name) for _name, file_name in MEMBERS
        ]
        self._member_current = [0] * len(MEMBERS)   # which photo is showing now
        self._member_thumb_size = (94, 126)

        self.member_cards = []          # (card, name_label) per member
        self.member_photo_labels = []   # the photo CTkLabel per member
        self.member_meta_labels = []    # the small mono "#01" tag per member
        for i, (name, file_name) in enumerate(MEMBERS):
            card = ctk.CTkFrame(strip, corner_radius=10, fg_color=self.BG_CARD,
                                border_width=2, border_color=self.CARD_BORDER)
            card.grid(row=0, column=i, padx=3, sticky="n")
            photo = self._member_photo(i, 0, self._member_thumb_size)
            img_label = ctk.CTkLabel(card, text="", image=photo)
            img_label.pack(padx=6, pady=6)
            name_label = ctk.CTkLabel(
                card, text=name, font=ctk.CTkFont(size=11, weight="bold"),
                text_color=self.FG_STRONG)
            name_label.pack()
            meta_label = ctk.CTkLabel(
                card, text=f"#{i + 1:02d}", font=self._font_mono_small,
                text_color=self.FG_DIM)
            meta_label.pack(pady=(0, 8))

            # Clicking anywhere on the card opens that member's info pop-up;
            # hovering it is the one moment red is allowed to show up here.
            for widget in (card, img_label, name_label, meta_label):
                widget.bind("<Button-1>",
                            lambda _e, idx=i: self._open_member_popup(idx))
                widget.bind("<Enter>",
                            lambda _e, idx=i: self._on_member_hover(idx, True))
                widget.bind("<Leave>",
                            lambda _e, idx=i: self._on_member_hover(idx, False))
                try:
                    widget.configure(cursor="hand2")   # hint it's clickable
                except Exception:
                    pass

            self.member_cards.append((card, name_label))
            self.member_photo_labels.append(img_label)
            self.member_meta_labels.append(meta_label)

    def _on_member_hover(self, index, entering):
        """The mouse entered or left one member's card."""
        card, _name_label = self.member_cards[index]
        meta_label = self.member_meta_labels[index]
        if entering:
            card.configure(border_color=ACCENT)
            meta_label.configure(text="STATUS: OT8 ✓", text_color=ACCENT)
        else:
            card.configure(border_color=self.CARD_BORDER)
            meta_label.configure(text=f"#{index + 1:02d}", text_color=self.FG_DIM)

    def _build_group(self, parent, row):
        """A wider area that cycles through group photos."""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(24, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// GROUP").grid(
            row=0, column=0, sticky="ew")

        frame = ctk.CTkFrame(box, corner_radius=10, fg_color=self.BG_CARD,
                             border_width=2, border_color=self.CARD_BORDER)
        frame.grid(row=1, column=0, pady=(14, 0))
        self._group_size = (560, 300)
        self._group_index = 1   # matches the photo we show first, below
        first = self._group_photo(1, self._group_size)
        self.group_label = ctk.CTkLabel(frame, text="", image=first)
        self.group_label.pack(padx=10, pady=10)

    def _build_tracklist(self, parent, row):
        """Show the picture of the song list."""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(24, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// TRACKLIST").grid(
            row=0, column=0, sticky="ew")

        # Load and size the tracklist picture to a comfy width, keeping shape.
        img = None
        try:
            path = resource_path(TRACKLIST_FILE)
            if PIL_AVAILABLE and os.path.exists(path):
                pic = Image.open(path)
                w, h = pic.size
                target_w = 420
                target_h = int(h * (target_w / w))
                pic = pic.resize((target_w, target_h), Image.LANCZOS)
                img = ctk.CTkImage(light_image=pic, dark_image=pic,
                                   size=(target_w, target_h))
        except Exception:
            img = None

        frame = ctk.CTkFrame(box, corner_radius=10, fg_color=self.BG_CARD,
                             border_width=1, border_color=self.CARD_BORDER)
        frame.grid(row=1, column=0, pady=(14, 0))
        if img is not None:
            ctk.CTkLabel(frame, text="", image=img).pack(padx=12, pady=12)
        else:
            ctk.CTkLabel(
                frame, text="tracklist.png not found",
                font=self._font_status, text_color=self.FG_DIM,
            ).pack(padx=40, pady=40)

    def _build_footer(self, parent, row):
        """Buttons (Settings, GitHub, Quit), a hint line, and credits."""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(26, 6))
        box.grid_columnconfigure(0, weight=1)

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.grid(row=0, column=0)

        # The gear button opens the pop-up settings window.
        ctk.CTkButton(
            btns, text="⚙  Settings", fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"), height=40,
            command=self._open_settings,
        ).grid(row=0, column=0, padx=6)

        # The GitHub button — with a logo (or a lettered placeholder).
        gh_logo = self._logo_image("github.png", "GitHub", self.CHIP_DARK, (20, 20))
        ctk.CTkButton(
            btns, text="  GitHub ↗", image=gh_logo, compound="left",
            fg_color=self.CHIP_DARK, hover_color=ACCENT_HOVER, border_width=1,
            border_color=self.CHIP_TEXT, text_color=self.CHIP_TEXT, height=40,
            font=ctk.CTkFont(family=MONO_FONT, size=13),
            command=lambda: self._open_url(REPO_URL),
        ).grid(row=0, column=1, padx=6)

        ctk.CTkButton(
            btns, text="Quit app", fg_color=self.CHIP_DARK, hover_color=ACCENT_HOVER,
            border_width=1, border_color=self.FG_DIM, text_color=self.CHIP_TEXT,
            height=40, command=self._quit_app,
        ).grid(row=0, column=2, padx=6)

        # A hint about what the X button does on this computer.
        if IS_MACOS:
            hint = ("Closing the window keeps the countdown running — click "
                    "the Dock icon to reopen, or use Quit app to exit.")
        elif TRAY_AVAILABLE:
            hint = ("Closing the window keeps the countdown running in the "
                    "system tray. Right-click the tray icon to quit.")
        else:
            hint = ("Install pystray + Pillow to keep the app running when "
                    "the window is closed.")
        ctk.CTkLabel(box, text=hint, font=ctk.CTkFont(size=12),
                     text_color=self.FG_DIM).grid(row=1, column=0, pady=(14, 2))

        ctk.CTkLabel(
            box, text=("Made for STAY. Member & group images are placeholders "
                       "— add your own in assets/. Stray Kids icon via Icons8 "
                       "· Album art via Spotify."),
            font=ctk.CTkFont(size=10), text_color=self.FG_DIM, wraplength=560,
        ).grid(row=2, column=0, pady=(0, 6))

    # ---------- The pop-up Settings window ----------

    def _open_settings(self):
        """Open (or re-focus) the settings window with all the toggles."""
        # If it's already open, just bring it to the front.
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.deiconify()
            self.settings_win.lift()
            self.settings_win.focus_force()
            return

        win = ctk.CTkToplevel(self)
        win.title(f"{APP_NAME} — Settings")
        win.geometry("420x520")
        win.configure(fg_color=self.BG_MAIN)
        win.transient(self)          # keep it attached to the main window
        self._set_window_icon(win)   # give this window our icon too
        self.settings_win = win

        ctk.CTkLabel(
            win, text="// APPEARANCE", font=self._font_section,
            text_color=ACCENT).pack(anchor="w", padx=20, pady=(18, 0))
        appearance_row = ctk.CTkFrame(win, fg_color="transparent")
        appearance_row.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(appearance_row, text="Dark mode",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.dark_mode_switch = ctk.CTkSwitch(
            appearance_row, text="", progress_color=ACCENT,
            command=self._on_dark_mode_toggled)
        self.dark_mode_switch.pack(side="right")
        if self.dark_mode:
            self.dark_mode_switch.select()

        ctk.CTkLabel(
            win, text="// STAY ALERTS", font=self._font_section,
            text_color=ACCENT).pack(anchor="w", padx=20, pady=(14, 0))

        # The big ON/OFF switch for all notifications.
        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(top, text="All STAY alerts",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.master_switch = ctk.CTkSwitch(
            top, text="", progress_color=ACCENT,
            command=self._on_setting_changed)
        self.master_switch.pack(side="right")
        if self.settings.get("notifications_enabled", True):
            self.master_switch.select()

        # One checkbox per big moment.
        self.milestone_vars = {}
        for key, label, _secs in MILESTONES:
            var = ctk.BooleanVar(value=self.settings.get(key, True))
            ctk.CTkCheckBox(
                win, text=f"Notify me: {label}", variable=var, fg_color=ACCENT,
                hover_color=ACCENT_HOVER, command=self._on_setting_changed,
            ).pack(anchor="w", padx=24, pady=4)
            self.milestone_vars[key] = var

        ctk.CTkLabel(win, text="// STARTUP", font=self._font_section,
                     text_color=ACCENT).pack(anchor="w", padx=20, pady=(14, 0))
        self.startup_var = ctk.BooleanVar(value=is_startup_enabled())
        ctk.CTkCheckBox(
            win, text="Start at login (recommended for alerts)",
            variable=self.startup_var, fg_color=ACCENT,
            hover_color=ACCENT_HOVER, command=self._on_startup_toggled,
        ).pack(anchor="w", padx=24, pady=(8, 4))

        ctk.CTkButton(
            win, text="Send test notification", fg_color=ACCENT,
            hover_color=ACCENT_HOVER, command=self._test_notification,
        ).pack(padx=20, pady=(18, 12))

    # ---------- The pop-up "about this member" window ----------

    def _open_member_popup(self, index):
        """Show one member's photo, name, and a short description."""
        name, _file_name = MEMBERS[index]
        description = MEMBER_DESCRIPTIONS.get(name, "")

        win = ctk.CTkToplevel(self)
        win.title(f"{APP_NAME} — {name}")
        win.geometry("360x480")
        win.configure(fg_color=self.BG_MAIN)
        win.transient(self)
        self._set_window_icon(win)   # this pop-up gets our icon too

        # A bigger version of whichever photo that member is showing
        # right now (loaded fresh at a bigger size — our picture cache
        # remembers it, so re-opening the same member is instant).
        big_size = (200, 268)
        photo = self._member_photo(index, self._member_current[index], big_size)
        ctk.CTkLabel(win, text="", image=photo).pack(pady=(26, 12))
        ctk.CTkLabel(
            win, text=name, font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.FG_STRONG,
        ).pack()
        ctk.CTkLabel(
            win, text=f"#{index + 1:02d}  ·  OT8", font=self._font_mono_small,
            text_color=self.FG_DIM,
        ).pack(pady=(2, 0))
        ctk.CTkLabel(
            win, text=description, font=ctk.CTkFont(size=13),
            text_color=self.FG_DIM, wraplength=300, justify="center",
        ).pack(padx=24, pady=(12, 20))

    # ---------- The tray icon (Windows / Linux only) ----------

    def _make_tray_image(self):
        """Draw our tray icon: the real Stray Kids picture if we have it,
        otherwise a simple red circle so the app still looks finished."""
        if self.skz_logo_source is not None:
            return self.skz_logo_source.resize((64, 64), Image.LANCZOS)
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))  # see-through square
        d = ImageDraw.Draw(img)
        d.ellipse([4, 4, 60, 60], fill=ACCENT)       # big red circle
        d.ellipse([22, 22, 42, 42], fill="#111114")  # dark hole in the middle
        return img

    def _start_tray(self):
        """Put our icon next to the clock, with a right-click menu."""
        try:
            # A thin separator line before "Quit" is a small, modern touch —
            # it visually sets the one-way, exit-the-app action apart from
            # the safe "just open the window" one above it.
            menu = pystray.Menu(
                pystray.MenuItem("Open SKZ Countdown", self._tray_show,
                                 default=True),   # double-click = open
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit SKZ Countdown", self._tray_quit),
            )
            self.tray_icon = pystray.Icon(
                APP_NAME, self._make_tray_image(), APP_NAME, menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception:
            self.tray_icon = None   # some Linux desktops have no tray — fine

    def _tray_show(self, *_):
        """User clicked 'Open' in the tray menu."""
        self.after(0, self._show_window)   # hop back to the window's thread

    def _tray_quit(self, *_):
        """User clicked 'Quit' in the tray menu."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.destroy)

    # ---------- Opening, hiding, and quitting the window ----------

    def _show_window(self):
        """Bring the window back and put it in front."""
        self.deiconify()
        self.lift()
        self.focus_force()
        # Wake everything up RIGHT NOW so it's fresh instantly.
        for job in ("_tick_job", "_member_job", "_group_job"):
            jid = getattr(self, job)
            if jid is not None:
                self.after_cancel(jid)
                setattr(self, job, None)
        self._tick()
        self._cycle_members()
        self._cycle_group()

    def _quit_app(self):
        """Really, truly close the whole app."""
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    def _on_close(self):
        """The user clicked the X. Hide instead of quitting (if we can)."""
        can_run_in_background = IS_MACOS or self.tray_icon is not None
        if can_run_in_background:
            self.withdraw()   # hide the window; the countdown keeps going
            if not self._bg_tip_shown:
                self._bg_tip_shown = True   # only explain this once
                if IS_MACOS:
                    tip = ("Still counting down in the background. "
                           "Click the Dock icon to reopen.")
                else:
                    tip = ("Still counting down in the system tray. "
                           "Right-click the tray icon to quit.")
                send_notification(APP_NAME, tip)
        else:
            self.destroy()    # no background option — just quit

    # ---------- Reacting to checkboxes and buttons ----------

    def _on_setting_changed(self):
        """A checkbox or switch was clicked — save the new choices."""
        self.settings["notifications_enabled"] = bool(self.master_switch.get())
        for key, var in self.milestone_vars.items():
            self.settings[key] = bool(var.get())
        save_settings(self.settings)

    def _on_startup_toggled(self):
        """The 'start at login' checkbox was clicked."""
        try:
            set_startup(bool(self.startup_var.get()))
        except OSError:
            self.startup_var.set(is_startup_enabled())  # snap back to truth

    def _test_notification(self):
        """The test button — send a practice pop-up."""
        send_notification(APP_NAME, f"Test toast! Counting down to {ALBUM_NAME} 🎧")

    # ---------- The member photo shuffle (every card stays lit up) ----------

    def _cycle_members(self):
        """Give any member with more than one photo a fresh random one —
        shuffled so the same picture never shows twice in a row. Members
        with only one photo (or none yet) just stay put. Borders always
        stay lit; only the picture inside ever changes."""
        if not self.member_cards:
            return
        if self.state() != "withdrawn":   # don't bother while hidden
            for i in range(len(MEMBERS)):
                paths = self._member_photo_paths[i]
                if len(paths) < 2:
                    continue   # nothing to shuffle for this member yet
                choices = [j for j in range(len(paths))
                           if j != self._member_current[i]]
                self._member_current[i] = random.choice(choices)
                photo = self._member_photo(
                    i, self._member_current[i], self._member_thumb_size)
                self.member_photo_labels[i].configure(image=photo)
        self._member_job = self.after(MEMBER_CYCLE_MS, self._cycle_members)

    def _cycle_group(self):
        """Swap to a fresh random group photo every few seconds — shuffled
        so the same picture never shows twice in a row. Only bothers if
        there's more than one, and only while the window is visible. The
        frame around it always stays lit up."""
        total = self._count_group_photos()
        if total > 1 and self.state() != "withdrawn":
            choices = [i for i in range(1, total + 1) if i != self._group_index]
            self._group_index = random.choice(choices)
            self.group_label.configure(
                image=self._group_photo(self._group_index, self._group_size))
        self._group_job = self.after(GROUP_CYCLE_MS, self._cycle_group)

    # ---------- The heartbeat: the tick ----------

    def _tick(self):
        """Look at the clock, update the numbers, check for big moments.

        MEMORY SAVERS in here:
          * We only repaint a number if it actually changed.
          * While the window is hidden, we slow down to one check every
            15 seconds (nobody can see the seconds anyway).
        """
        now = datetime.now(timezone.utc)              # what time is it NOW?
        remaining = (RELEASE_DT - now).total_seconds()  # how long is left?
        hidden = self.state() == "withdrawn"          # is the window hidden?

        if remaining <= 0:
            # THE ALBUM IS OUT! Switch to party mode (but only once).
            if not self._celebrating:
                self._celebrating = True
                for name in self.unit_labels:
                    self.unit_labels[name].configure(text="0")
                self.status_label.configure(
                    text='🎉 "This & That" IS OUT — STAY, go stream! 🎉',
                    text_color=ACCENT, font=self._font_celebrate)
        elif not hidden:
            # Split the leftover seconds into weeks/days/hours/min/sec.
            total_seconds = int(remaining)
            weeks, rem = divmod(total_seconds, 7 * 24 * 3600)
            days, rem = divmod(rem, 24 * 3600)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)

            # Only touch labels whose number actually changed.
            for name, val in (("WEEKS", weeks), ("DAYS", days),
                              ("HOURS", hours), ("MINUTES", minutes),
                              ("SECONDS", seconds)):
                if self._last_shown.get(name) != val:
                    self._last_shown[name] = val
                    text = str(val) if name == "WEEKS" else f"{val:02d}"
                    if PIL_AVAILABLE:
                        # Draw it as a flat, crisp seven-segment "LED" picture.
                        img = self._number_image(text, DIGIT_W, DIGIT_H)
                        self.unit_labels[name].configure(image=img, text="")
                    else:
                        self.unit_labels[name].configure(text=text)

            day_count = total_seconds // 86400
            if self._last_shown.get("day_count") != day_count:
                self._last_shown["day_count"] = day_count
                self.status_label.configure(
                    text=f"{day_count} total days remaining",
                    text_color=self.FG_DIM, font=self._font_status)

        # Even when hidden, we still check whether it's time for an alert.
        self._check_milestones(remaining)

        delay = TICK_HIDDEN_MS if hidden else TICK_VISIBLE_MS
        self._tick_job = self.after(delay, self._tick)

    # ---------- Deciding when to send the big alerts ----------

    def _check_milestones(self, remaining):
        """Send alerts at the right moments — and never send one twice."""
        if not self.settings.get("notifications_enabled", True):
            self._startup_check_done = True
            return  # the big switch is off — stay quiet
        fired = set(self.settings.get("fired", []))  # alerts already sent

        # Which big moments have we passed that we haven't announced yet?
        crossed = [
            (key, label, secs)
            for key, label, secs in MILESTONES
            if key not in fired
            and self.settings.get(key, True)
            and remaining <= secs
        ]
        if not crossed:
            self._startup_check_done = True
            return

        changed = False
        for key, label, secs_before in crossed:
            in_live_window = remaining > secs_before - 3600
            is_most_recent = key == crossed[-1][0]

            if in_live_window:
                if secs_before == 0:
                    send_notification(
                        "🎉 IT'S HERE!",
                        f"{ALBUM_NAME} is officially OUT. Go stream!")
                else:
                    send_notification(
                        APP_NAME, f"{label} until {ALBUM_NAME} drops!")
            elif not self._startup_check_done and is_most_recent:
                # Crossed while the app was CLOSED — one catch-up alert.
                if secs_before == 0:
                    send_notification(
                        "🎉 IT'S OUT!",
                        f"{ALBUM_NAME} dropped while the app was closed. "
                        "Go stream!")
                else:
                    send_notification(
                        APP_NAME,
                        f"While the app was closed: {label} until "
                        f"{ALBUM_NAME} drops!")

            fired.add(key)
            changed = True

        self._startup_check_done = True
        if changed:
            self.settings["fired"] = sorted(fired)
            save_settings(self.settings)


def main():
    """Make the window and hand control over to it. The end!"""
    app = CountdownApp()
    app.mainloop()   # this line runs until the app quits


if __name__ == "__main__":
    main()   # only auto-start if this file is run directly