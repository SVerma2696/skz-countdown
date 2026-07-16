"""
The "facts and settings" part of the app.

This file holds things that never change while the app is running (like
which folder the logos live in) and things we load once at startup (like
your saved settings, and which album we're counting down to). Nothing in
here draws a window — that's ui.py's job. Keeping the "facts" separate from
the "drawing" is why the app can be pointed at a totally different album
release just by editing release.json, with no code changes needed.
"""

import json          # lets us save settings (and read release.json) as text
import os            # lets us talk to folders and files
import sys           # tells us which operating system we're on
from datetime import datetime, timezone   # tools for working with time
from zoneinfo import ZoneInfo              # tools for time zones

# Try to grab the notification toolbox. If it's not installed,
# we remember that so we don't crash later.
try:
    from plyer import notification as plyer_notification  # noqa: F401
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

# Try to grab the "drawing pictures" toolbox (Pillow). We use it to show
# the logos, the member photos, the tracklist, the tray icon, the seven-
# segment countdown digits, and the faint circuit-board background.
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk  # noqa: F401
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
        import pystray   # noqa: F401  (draws the tray icon)
        TRAY_AVAILABLE = True
    except ImportError:
        pass  # no tray toolbox? That's okay, the app still works.

# ---------------- The important facts about the app itself ----------------

APP_NAME = "SKZ Countdown"
APP_VERSION = "1.5.1"
APP_ID = "skz-countdown"

# The picture file that's ALWAYS the same, no matter which album is loaded
# from release.json — it's this app's own icon, not part of any release.
SKZ_LOGO_FILE = "skz-logo.png"   # the Stray Kids photo (window icon + header)

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

# The short nickname each member's real photos are named after, e.g.
# assets/members/bc1.jpg, bc2.webp, bc3.jpg, ... for Bang Chan. The app
# tries 1, 2, 3, ... of these until a number is missing, so you can add as
# many (or as few) photos per member as you like.
MEMBER_PHOTO_PREFIX = {
    "Bang Chan": "bc",
    "Lee Know": "lk",
    "Changbin": "cb",
    "Hyunjin": "hj",
    "Han": "h",
    "Felix": "f",
    "Seungmin": "s",
    "I.N": "in",
}

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
# Photos stay put for a while, then change at a random moment — not on a
# steady beat — so it feels more like someone occasionally flipping to a
# new picture than a metronome ticking.
MEMBER_CYCLE_MIN_MS = 7000     # wait at LEAST 7 seconds...
MEMBER_CYCLE_MAX_MS = 16000    # ...and at MOST 16 seconds before changing
GROUP_CYCLE_MIN_MS = 10000     # the group photo waits a little longer...
GROUP_CYCLE_MAX_MS = 22000     # ...somewhere between 10 and 22 seconds
BOOT_TYPE_MS = 18         # how fast the boot line "types" itself out
BOOT_BLINK_MS = 600       # how often the boot cursor blinks after that


def resource_path(filename):
    """Find a file we bundled with the app, like a logo picture.

    When PyInstaller packs us into one .exe/.app, it unzips extra files
    into a secret temporary folder named in sys._MEIPASS. When we're just
    plain .py files, this function lives two folders deep (inside the
    skz_countdown_pkg package folder), so we walk up TWO folders to get
    back to the project's home folder where the pictures actually live.
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        here = os.path.dirname(os.path.abspath(__file__))   # .../skz_countdown_pkg
        base = os.path.dirname(here)                        # the project's home folder
    return os.path.join(base, filename)


# The picture file types we know how to open, checked in this order.
_PHOTO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _find_numbered_photo(folder, prefix, number):
    """Look for one numbered photo (like "bc1" or plain "1"), trying every
    picture format we support, and return its full path — or None if it
    isn't there in any of them. This is how members and the group can mix
    and match .jpg, .png, and .webp photos without the app caring."""
    for ext in _PHOTO_EXTENSIONS:
        candidate = os.path.join(folder, f"{prefix}{number}{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


# ---------------- Saving and loading YOUR settings ----------------


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


# ---------------- Which album are we counting down to? ----------------
# This is the part that used to be hardcoded (a fixed date baked into the
# code). Now it lives in release.json instead, so the SAME app can count
# down to a totally different comeback just by editing that file — no
# code changes needed. If release.json is missing or broken, we fall back
# to these exact same "This & That" defaults, so the app never crashes.

DEFAULT_RELEASE = {
    "album_name": 'Stray Kids — "This & That"',
    "artist_display": "STRAY KIDS",
    "title_display": "This & That",
    "fandom_name": "STAY",
    "release_date": "2026-08-07",
    "release_time": "13:00:00",
    "release_timezone": "Asia/Seoul",
    "release_tz_label": "KST",
    "repo_url": "https://github.com/SVerma2696/skz-countdown",
    "artist_logo": "skz-logo.png",
    "title_logo": "t&t-logo.png",
    "tracklist_image": "tracklist.png",
    "links": [
        {"label": "Stray Kids Shop",
         "url": "https://straykidsshop.com/collections/this-that",
         "color": "#141416", "logo": "skzshoplogo.webp"},
        {"label": "Apple Music",
         "url": "https://music.apple.com/us/album/this-that/6781751949",
         "color": "#FA243C", "logo": "applemusic-logo.webp"},
        {"label": "Spotify",
         "url": "https://open.spotify.com/album/46TYlDjLrEsOLFgxfxNiUy",
         "color": "#1DB954", "logo": "spotify-logo.png"},
    ],
}


def load_release_config():
    """Read release.json. If it's missing or broken, use the defaults above
    — same "never crash the countdown" idea as load_settings()."""
    data = dict(DEFAULT_RELEASE)
    try:
        with open(resource_path("release.json"), "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except (OSError, json.JSONDecodeError, TypeError):
        pass  # no file, or it's broken — defaults are fine
    return data


def _release_datetime(data):
    """Turn release.json's date/time/timezone text into one real, timezone-
    aware moment in time. If the text is broken in any way (bad date, typo'd
    timezone name, ...), fall back to the built-in default moment instead of
    crashing the whole app over a typo in a config file."""
    try:
        year, month, day = (int(p) for p in data["release_date"].split("-"))
        hour, minute, second = (int(p) for p in data["release_time"].split(":"))
        zone = ZoneInfo(data["release_timezone"])
        return datetime(year, month, day, hour, minute, second, tzinfo=zone)
    except Exception:
        d = DEFAULT_RELEASE
        year, month, day = (int(p) for p in d["release_date"].split("-"))
        hour, minute, second = (int(p) for p in d["release_time"].split(":"))
        zone = ZoneInfo(d["release_timezone"])
        return datetime(year, month, day, hour, minute, second, tzinfo=zone)


# Load once, at startup — everything below is derived from release.json
# (or the built-in defaults) and used throughout the rest of the app.
RELEASE = load_release_config()

ALBUM_NAME = RELEASE["album_name"]
ARTIST_DISPLAY = RELEASE["artist_display"]
TITLE_DISPLAY = RELEASE["title_display"]
FANDOM_NAME = RELEASE["fandom_name"]
RELEASE_TZ_LABEL = RELEASE["release_tz_label"]
REPO_URL = RELEASE["repo_url"]
TT_LOGO_FILE = RELEASE["title_logo"]         # the title-art picture
TRACKLIST_FILE = RELEASE["tracklist_image"]  # the picture of the song list

# THE moment everything counts down to (a real, timezone-aware moment).
RELEASE_DT = _release_datetime(RELEASE)

# Ask the computer what time zone IT lives in,
# then figure out what the release moment is in LOCAL time.
LOCAL_TZ = datetime.now().astimezone().tzinfo
RELEASE_LOCAL = RELEASE_DT.astimezone(LOCAL_TZ)

# The buttons that jump to the album online.
# Each one is (label, web address, brand color, logo file name).
ALBUM_LINKS = [
    (link["label"], link["url"], link["color"], link["logo"])
    for link in RELEASE["links"]
]
