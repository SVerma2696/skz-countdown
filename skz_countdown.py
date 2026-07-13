"""
Stray Kids — "This & That" Album Countdown

WHAT THIS PROGRAM DOES (the simple version):
  1. It knows the exact moment the album comes out.
  2. It looks at your computer's clock.
  3. It subtracts one from the other and shows you how long is left.
  4. It taps you on the shoulder (a notification) at big moments.

It also shows the 8 members one at a time, the album tracklist, and buttons
that jump straight to the album on Spotify, Apple Music, and the Stray Kids
shop. It runs on Windows, Mac, and Linux, and keeps counting quietly in the
background even when you close the window.

A note on the "engineering console" look: the section titles start with "//"
(that's how programmers write a note-to-self in code), the numbers use a
typewriter font like a digital readout, and thin red lines act like little
circuit traces. It's meant to look like a tidy control panel a computer
engineer would build.
"""

# ---- These are the "toolboxes" we borrow code from ----
import json          # lets us save settings as a little text file
import os            # lets us talk to folders and files
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
# the logos, the member photos, the tracklist, and the tray icon.
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
APP_VERSION = "1.2.0"
APP_ID = "skz-countdown"
ALBUM_NAME = 'Stray Kids — "This & That"'
REPO_URL = "https://github.com/SVerma2696/skz-countdown"  # our home on GitHub

# The two picture files that live right next to this script.
SKZ_LOGO_FILE = "skz-logo.jpg"   # the Stray Kids photo (window icon + header)
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
ACCENT = "#E4002B"        # Stray Kids red
ACCENT_HOVER = "#FF2E4F"  # a lighter red for when the mouse hovers
BG_MAIN = "#FFFFFF"       # crisp white window background
BG_CARD = "#F7F7F9"       # the faintest gray, so boxes stand out on white
BG_CARD_2 = "#EFEFF2"     # a slightly deeper gray for placeholders
FG_DIM = "#6b6b76"        # medium gray for small text (readable on white)
FG_STRONG = "#141416"     # near-black for text that should pop off the page
CHIP_DARK = "#141416"     # near-black for our outlined "chip" buttons
CHIP_TEXT = "#FFFFFF"     # their always-white text/outline

# How often to look at the clock (in milliseconds).
# A typewriter-style font makes the numbers feel like a digital readout.
# If a computer doesn't have this exact font, it just falls back quietly.
MONO_FONT = "Consolas" if IS_WINDOWS else "Menlo" if IS_MACOS else "monospace"

TICK_VISIBLE_MS = 1000    # window open: every 1 second (so seconds tick)
TICK_HIDDEN_MS = 15000    # window hidden: every 15 seconds (saves work,
                          # because nobody can see the seconds anyway)
MEMBER_CYCLE_MS = 3500    # spotlight a new member every 3.5 seconds
GROUP_CYCLE_MS = 6000     # swap the group photo every 6 seconds


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


def _make_member_placeholder(name, size):
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
    # A thin red frame — matches our circuit-trace theme.
    d.rectangle([1, 1, w - 2, h - 2], outline=ACCENT, width=2)
    # A tiny "add photo here" hint near the bottom.
    small = _load_font(max(9, int(w * 0.085)))
    hint = "photo →"
    tw = d.textlength(hint, font=small)
    d.text(((w - tw) / 2, h - int(h * 0.20)), hint, fill="#9a9aa2", font=small)
    return img


def _make_group_placeholder(index, size):
    """Draw a simple wide 'group photo' stand-in."""
    w, h = size
    img = Image.new("RGB", (w, h), "#E4E4E8")
    d = ImageDraw.Draw(img)
    d.rectangle([1, 1, w - 2, h - 2], outline=ACCENT, width=2)
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
        self._member_job = None        # reminder ID for the member spotlight
        self._group_job = None         # reminder ID for the group photo swap
        self._last_shown = {}          # what each number label says right now
        self._celebrating = False      # did we already switch to party mode?
        self._img_cache = {}           # remember pictures so we load them once
        self._member_index = 0         # which member is in the spotlight
        self._group_index = 0          # which group photo is showing

        self.title(f"{APP_NAME} — This & That")
        self.geometry("960x780")       # starting window size
        self.minsize(880, 600)         # wide enough to fit all 8 members
        ctk.set_appearance_mode("light")
        self.configure(fg_color=BG_MAIN)   # paint the window white

        # MEMORY SAVER: make our fonts ONCE and reuse them forever.
        # (Making a new font every second would slowly eat RAM.)
        self._font_status = ctk.CTkFont(size=14)
        self._font_celebrate = ctk.CTkFont(size=20, weight="bold")
        self._font_section = ctk.CTkFont(family=MONO_FONT, size=13,
                                         weight="bold")
        self._font_num = ctk.CTkFont(family=MONO_FONT, size=34, weight="bold")
        self._font_unit = ctk.CTkFont(size=11, weight="bold")

        self._load_logos()   # open our logo + title pictures, if we can
        self._build_ui()     # draw everything

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
        self._cycle_members()   # start spotlighting members
        self._cycle_group()     # start swapping the group photo

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
        except Exception:
            pic = None
        if pic is None:                          # no photo? draw a placeholder
            if kind == "member":
                pic = _make_member_placeholder(meta, size)
            elif kind == "group":
                pic = _make_group_placeholder(meta, size)
            else:  # logo
                label, color = meta
                pic = _make_logo_placeholder(label, color, size)

        image = ctk.CTkImage(light_image=pic, dark_image=pic, size=size)
        self._img_cache[cache_key] = image
        return image

    def _member_photo(self, file_name, name, size):
        """Get a member's photo (or their placeholder)."""
        path = resource_path(os.path.join("assets", "members", file_name))
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
        self.tt_logo_image = None    # the "This & That" title picture
        if not PIL_AVAILABLE:
            return

        try:
            skz_pic = Image.open(resource_path(SKZ_LOGO_FILE))
            self.skz_logo_image = ctk.CTkImage(
                light_image=skz_pic, dark_image=skz_pic, size=(76, 76))
            # The taskbar/title-bar icon needs a plain Tk picture.
            self._icon_photo = ImageTk.PhotoImage(skz_pic)
            self.iconphoto(True, self._icon_photo)

            if IS_WINDOWS:
                # customtkinter secretly swaps the titlebar icon back to its
                # own logo unless we've set an .ico ourselves — so we do.
                ico_path = os.path.join(_cfg_dir, "skz_countdown_icon.ico")
                skz_pic.save(
                    ico_path, format="ICO",
                    sizes=[(256, 256), (64, 64), (32, 32), (16, 16)],
                )
                self.iconbitmap(ico_path)
        except Exception:
            pass  # a missing picture should never crash the countdown

        try:
            tt_pic = Image.open(resource_path(TT_LOGO_FILE))
            width, height = tt_pic.size
            target_h = 66
            target_w = int(width * (target_h / height))
            self.tt_logo_image = ctk.CTkImage(
                light_image=tt_pic, dark_image=tt_pic,
                size=(target_w, target_h))
        except Exception:
            pass

    # ---------- Opening web links ----------

    def _open_url(self, url):
        """Open any web address in the person's normal web browser."""
        webbrowser.open(url)

    # ---------- Small building-block helpers ----------

    def _section_header(self, parent, text):
        """A '// TITLE' row that looks like a code comment, with a red line."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text=text, font=self._font_section,
                     text_color=ACCENT).grid(row=0, column=0, sticky="w")
        ctk.CTkFrame(row, height=2, fg_color="#E7E7EB",
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
        self.page = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
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
        """A thin monospace strip up top — the 'engineering console' touch."""
        tz_name = RELEASE_LOCAL.strftime("%Z") or str(LOCAL_TZ)
        bar = ctk.CTkFrame(parent, fg_color=FG_STRONG, corner_radius=6)
        bar.grid(row=row, column=0, sticky="ew", pady=(8, 14))
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            bar, text=f"  ● {APP_NAME.lower().replace(' ', '-')} v{APP_VERSION}",
            font=ctk.CTkFont(family=MONO_FONT, size=11, weight="bold"),
            text_color="#FFFFFF",
        ).grid(row=0, column=0, sticky="w", pady=4)
        ctk.CTkLabel(
            bar, text=f"tz-sync: Asia/Seoul → {tz_name}  ",
            font=ctk.CTkFont(family=MONO_FONT, size=11),
            text_color="#B9B9C2",
        ).grid(row=0, column=2, sticky="e", pady=4, padx=(0, 4))

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
            text_color=FG_DIM,
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
            header, text="Drops August 7, 2026 · 1:00 PM KST",
            font=ctk.CTkFont(size=13), text_color=FG_DIM,
        ).pack(pady=(6, 0))

        tz_name = RELEASE_LOCAL.strftime("%Z") or str(LOCAL_TZ)
        local_str = RELEASE_LOCAL.strftime(
            "%A, %B %d, %Y · %I:%M %p").replace(" 0", " ")
        ctk.CTkLabel(
            header, text=f"Your local time: {local_str} ({tz_name})",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=FG_STRONG,
        ).pack(pady=(2, 0))

        # A thin red circuit-trace line under the header.
        ctk.CTkFrame(header, height=2, fg_color=ACCENT, corner_radius=0).pack(
            fill="x", padx=60, pady=(14, 0))

    def _build_countdown(self, parent, row):
        """The five big number boxes: weeks, days, hours, minutes, seconds."""
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", pady=(16, 6))
        wrap.grid_columnconfigure(0, weight=1)

        units = ctk.CTkFrame(wrap, fg_color="transparent")
        units.grid(row=0, column=0)
        self.unit_labels = {}
        for i, name in enumerate(["WEEKS", "DAYS", "HOURS", "MINUTES",
                                  "SECONDS"]):
            # Each box has a thin red outline, like a little circuit chip.
            card = ctk.CTkFrame(units, corner_radius=10, fg_color=BG_CARD,
                                border_width=1, border_color=ACCENT, width=150)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            card.grid_propagate(False)
            card.configure(height=120)
            value = ctk.CTkLabel(card, text="--", font=self._font_num,
                                 text_color=FG_STRONG)
            value.pack(pady=(24, 0))
            ctk.CTkLabel(card, text=name, font=self._font_unit,
                         text_color=FG_DIM).pack(pady=(2, 14))
            self.unit_labels[name] = value

        self.status_label = ctk.CTkLabel(
            wrap, text="", font=self._font_status, text_color=FG_DIM)
        self.status_label.grid(row=1, column=0, pady=(12, 0))

    def _build_album_links(self, parent, row):
        """Buttons that jump straight to the album online."""
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
                btns, text=f"  {label}", image=logo, compound="left",
                fg_color=color, hover_color=color, text_color="#FFFFFF",
                font=ctk.CTkFont(size=13, weight="bold"), height=42,
                corner_radius=8,
                command=lambda u=url: self._open_url(u),
            )
            btn.grid(row=0, column=i, padx=6)

    def _build_members(self, parent, row):
        """8 columns — one per member — that light up one at a time."""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(24, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// MEMBERS  (spotlight cycles)").grid(
            row=0, column=0, sticky="ew")

        strip = ctk.CTkFrame(box, fg_color="transparent")
        strip.grid(row=1, column=0, pady=(14, 0))

        self.member_cards = []   # remember each card so we can highlight it
        thumb_size = (94, 126)
        for i, (name, file_name) in enumerate(MEMBERS):
            # Each member gets a column: a photo card + their name below.
            card = ctk.CTkFrame(strip, corner_radius=10, fg_color=BG_CARD,
                                border_width=2, border_color="#E2E2E7")
            card.grid(row=0, column=i, padx=3, sticky="n")
            photo = self._member_photo(file_name, name, thumb_size)
            img_label = ctk.CTkLabel(card, text="", image=photo)
            img_label.pack(padx=6, pady=6)
            name_label = ctk.CTkLabel(
                card, text=name, font=ctk.CTkFont(size=11, weight="bold"),
                text_color=FG_DIM)
            name_label.pack(pady=(0, 8))
            self.member_cards.append((card, name_label))

    def _build_group(self, parent, row):
        """A wider area that cycles through group photos."""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(24, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// GROUP").grid(
            row=0, column=0, sticky="ew")

        frame = ctk.CTkFrame(box, corner_radius=10, fg_color=BG_CARD,
                             border_width=1, border_color="#E2E2E7")
        frame.grid(row=1, column=0, pady=(14, 0))
        self._group_size = (560, 300)
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
                img = ctk.CTkImage(light_image=pic, dark_image=pic,
                                   size=(target_w, target_h))
        except Exception:
            img = None

        frame = ctk.CTkFrame(box, corner_radius=10, fg_color=BG_CARD,
                             border_width=1, border_color=ACCENT)
        frame.grid(row=1, column=0, pady=(14, 0))
        if img is not None:
            ctk.CTkLabel(frame, text="", image=img).pack(padx=12, pady=12)
        else:
            ctk.CTkLabel(
                frame, text="tracklist.png not found",
                font=self._font_status, text_color=FG_DIM,
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
        gh_logo = self._logo_image("github.png", "GitHub", CHIP_DARK, (20, 20))
        ctk.CTkButton(
            btns, text="  View on GitHub", image=gh_logo, compound="left",
            fg_color=CHIP_DARK, hover_color="#232326", border_width=1,
            border_color=CHIP_TEXT, text_color=CHIP_TEXT, height=40,
            command=lambda: self._open_url(REPO_URL),
        ).grid(row=0, column=1, padx=6)

        ctk.CTkButton(
            btns, text="Quit app", fg_color=CHIP_DARK, hover_color="#232326",
            border_width=1, border_color=FG_DIM, text_color=CHIP_TEXT,
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
                     text_color=FG_DIM).grid(row=1, column=0, pady=(14, 2))

        ctk.CTkLabel(
            box, text=("Member & group images are placeholders — add your own "
                       "in assets/. Stray Kids icon via Icons8 · Album art via "
                       "Spotify."),
            font=ctk.CTkFont(size=10), text_color=FG_DIM, wraplength=560,
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
        win.geometry("420x430")
        win.configure(fg_color=BG_MAIN)
        win.transient(self)          # keep it attached to the main window
        self.settings_win = win

        ctk.CTkLabel(
            win, text="// NOTIFICATIONS", font=self._font_section,
            text_color=ACCENT).pack(anchor="w", padx=20, pady=(18, 0))

        # The big ON/OFF switch for all notifications.
        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(top, text="All notifications",
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

    # ---------- The tray icon (Windows / Linux only) ----------

    def _make_tray_image(self):
        """Draw a tiny red circle to be our tray icon picture."""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))  # see-through square
        d = ImageDraw.Draw(img)
        d.ellipse([4, 4, 60, 60], fill=ACCENT)       # big red circle
        d.ellipse([22, 22, 42, 42], fill="#111114")  # dark hole in the middle
        return img

    def _start_tray(self):
        """Put our icon next to the clock, with a right-click menu."""
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Open SKZ Countdown", self._tray_show,
                                 default=True),   # double-click = open
                pystray.MenuItem("Quit", self._tray_quit),
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

    # ---------- The member spotlight (cycles one at a time) ----------

    def _cycle_members(self):
        """Light up the next member's card, dim the rest. Very cheap — it
        only changes border colors, so it's easy on memory and battery."""
        if not self.member_cards:
            return
        if self.state() != "withdrawn":   # don't bother while hidden
            for i, (card, name_label) in enumerate(self.member_cards):
                if i == self._member_index:
                    card.configure(border_color=ACCENT)          # the star!
                    name_label.configure(text_color=FG_STRONG)
                else:
                    card.configure(border_color="#E2E2E7")       # resting
                    name_label.configure(text_color=FG_DIM)
            self._member_index = (self._member_index + 1) % len(self.member_cards)
        self._member_job = self.after(MEMBER_CYCLE_MS, self._cycle_members)

    def _cycle_group(self):
        """Swap to the next group photo every few seconds (only if there is
        more than one, and only while the window is visible)."""
        total = self._count_group_photos()
        if total > 1 and self.state() != "withdrawn":
            self._group_index = (self._group_index % total) + 1
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
                    self.unit_labels[name].configure(text=str(val))

            day_count = total_seconds // 86400
            if self._last_shown.get("day_count") != day_count:
                self._last_shown["day_count"] = day_count
                self.status_label.configure(
                    text=f"{day_count} total days remaining",
                    text_color=FG_DIM, font=self._font_status)

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