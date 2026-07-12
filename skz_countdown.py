"""
Stray Kids — "This & That" Album Countdown

WHAT THIS PROGRAM DOES (the simple version):
  1. It knows the exact moment the album comes out.
  2. It looks at your computer's clock.
  3. It subtracts one from the other and shows you how long is left.
  4. It taps you on the shoulder (a notification) at big moments.

It works on Windows, Mac, and Linux, and it keeps working quietly in the
background even when you close the window.
"""

# ---- These are the "toolboxes" we borrow code from ----
import json          # lets us save settings as a little text file
import os            # lets us talk to folders and files
import shlex         # helps write safe commands for Linux
import subprocess    # lets us run other programs (like notifications)
import sys           # tells us which operating system we're on
import threading     # lets us do two things at once
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

# Which computer are we running on? Only one of these will be True.
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# The "tray" is the little row of icons by your clock.
# We use it on Windows and Linux. Macs use the Dock instead,
# because the tray toolbox and the window toolbox fight over
# who gets to be in charge on a Mac.
TRAY_AVAILABLE = False
if not IS_MACOS:
    try:
        import pystray                    # draws the tray icon
        from PIL import Image, ImageDraw  # draws the picture FOR the icon
        TRAY_AVAILABLE = True
    except ImportError:
        pass  # no tray toolbox? That's okay, the app still works.

# ---------------- The important facts about the album ----------------

APP_NAME = "SKZ Countdown"
APP_ID = "skz-countdown"
ALBUM_NAME = 'Stray Kids — "This & That"'

# THE moment everything counts down to:
# August 7, 2026 at 1:00 PM in Korea (where the album releases).
RELEASE_DT = datetime(2026, 8, 7, 13, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))

# Ask the computer what time zone IT lives in,
# then figure out what the Korean release moment is in LOCAL time.
LOCAL_TZ = datetime.now().astimezone().tzinfo
RELEASE_LOCAL = RELEASE_DT.astimezone(LOCAL_TZ)

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
ACCENT = "#E4002B"        # Stray Kids red
ACCENT_HOVER = "#FF2E4F"  # a lighter red for when the mouse hovers
BG_CARD = "#1b1b1f"       # dark gray for boxes
FG_DIM = "#9a9aa2"        # soft gray for small text

# How often to look at the clock (in milliseconds).
TICK_VISIBLE_MS = 1000    # window open: every 1 second (so seconds tick)
TICK_HIDDEN_MS = 15000    # window hidden: every 15 seconds (saves work,
                          # because nobody can see the seconds anyway)

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


def send_notification(title, message):
    """Show a little pop-up message in the corner of the screen.

    We do it on a helper thread so the window never freezes while
    the notification is being delivered.
    Plan A: the plyer toolbox. Plan B: the OS's own built-in way.
    """

    def _worker():
        # Plan A: plyer (works on all three systems, usually)
        if PLYER_AVAILABLE:
            try:
                plyer_notification.notify(
                    title=title, message=message,
                    app_name=APP_NAME, timeout=10,
                )
                return  # it worked, we're done
            except Exception:
                pass  # didn't work — try Plan B below
        # Plan B: ask the operating system directly
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


# ---------------- The window itself ----------------


class CountdownApp(ctk.CTk):
    """The main window. Everything the user sees lives in here."""

    def __init__(self):
        super().__init__()  # build the basic empty window first
        self.settings = load_settings()
        self.tray_icon = None          # the tray icon (made later, maybe)
        self._bg_tip_shown = False     # did we explain the tray yet?
        self._startup_check_done = False  # lets us send "catch-up" alerts
        self._tick_job = None          # the "come back later" reminder ID
        self._last_shown = {}          # what each number label says right now
        self._celebrating = False      # did we already switch to party mode?

        self.title(APP_NAME)
        self.geometry("660x640")       # starting window size
        self.minsize(580, 580)         # don't let it shrink smaller than this
        ctk.set_appearance_mode("dark")

        # MEMORY SAVER: make our fonts ONCE and reuse them forever.
        # (Making a new font every second would slowly eat RAM.)
        self._font_status = ctk.CTkFont(size=14)
        self._font_celebrate = ctk.CTkFont(size=18, weight="bold")

        self._build_ui()   # draw all the labels, boxes, and buttons

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

        self._tick()   # start the clock ticking!

    # ---------- Drawing the window ----------

    def _build_ui(self):
        """Create everything you see: titles, number boxes, checkboxes."""
        self.grid_columnconfigure(0, weight=1)  # let things stretch sideways

        # --- The title area at the top ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, pady=(26, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="STRAY KIDS", font=ctk.CTkFont(size=15, weight="bold"),
            text_color=FG_DIM,
        ).grid(row=0, column=0)
        ctk.CTkLabel(
            header, text='"This & That"',
            font=ctk.CTkFont(size=34, weight="bold"), text_color=ACCENT,
        ).grid(row=1, column=0)
        ctk.CTkLabel(
            header,
            text="Drops August 7, 2026 · 1:00 PM KST",
            font=ctk.CTkFont(size=13), text_color=FG_DIM,
        ).grid(row=2, column=0, pady=(4, 0))

        # Show the release moment in THIS computer's own time zone.
        tz_name = RELEASE_LOCAL.strftime("%Z") or str(LOCAL_TZ)
        local_str = RELEASE_LOCAL.strftime(
            "%A, %B %d, %Y · %I:%M %p").replace(" 0", " ")
        ctk.CTkLabel(
            header,
            text=f"Your local time: {local_str} ({tz_name})",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#e8e8ee",
        ).grid(row=3, column=0, pady=(2, 0))

        # --- The five number boxes (weeks, days, hours, minutes, seconds) ---
        self.units_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.units_frame.grid(row=1, column=0, pady=18, padx=24, sticky="ew")

        self.unit_labels = {}   # so we can find each number label later
        unit_names = ["WEEKS", "DAYS", "HOURS", "MINUTES", "SECONDS"]
        big_font = ctk.CTkFont(size=32, weight="bold")     # made once,
        small_font = ctk.CTkFont(size=11, weight="bold")   # shared by all 5
        for i, name in enumerate(unit_names):
            self.units_frame.grid_columnconfigure(i, weight=1, uniform="u")
            card = ctk.CTkFrame(self.units_frame, corner_radius=14,
                                fg_color=BG_CARD)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            value = ctk.CTkLabel(card, text="--", font=big_font)
            value.pack(pady=(16, 0), padx=12)
            ctk.CTkLabel(
                card, text=name, font=small_font, text_color=FG_DIM,
            ).pack(pady=(0, 14))
            self.unit_labels[name] = value

        # --- One line of status text under the numbers ---
        self.status_label = ctk.CTkLabel(
            self, text="", font=self._font_status, text_color=FG_DIM
        )
        self.status_label.grid(row=2, column=0, pady=(0, 6))

        # --- The notifications box ---
        notif_frame = ctk.CTkFrame(self, corner_radius=14, fg_color=BG_CARD)
        notif_frame.grid(row=3, column=0, padx=24, pady=(6, 12), sticky="ew")
        notif_frame.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(notif_frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row, text="Notifications",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        # The big ON/OFF switch for all notifications.
        self.master_switch = ctk.CTkSwitch(
            title_row, text="Enabled", progress_color=ACCENT,
            command=self._on_setting_changed,
        )
        self.master_switch.grid(row=0, column=1, sticky="e")
        if self.settings.get("notifications_enabled", True):
            self.master_switch.select()   # start switched on if saved as on

        # One checkbox for each big moment.
        self.milestone_vars = {}
        for i, (key, label, _secs) in enumerate(MILESTONES):
            var = ctk.BooleanVar(value=self.settings.get(key, True))
            cb = ctk.CTkCheckBox(
                notif_frame, text=f"Notify me: {label}", variable=var,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                command=self._on_setting_changed,
            )
            cb.grid(row=i + 1, column=0, sticky="w", padx=16, pady=4)
            self.milestone_vars[key] = var

        # The "start at login" checkbox (works on every OS).
        row_base = len(MILESTONES) + 1
        self.startup_var = ctk.BooleanVar(value=is_startup_enabled())
        ctk.CTkCheckBox(
            notif_frame, text="Start at login (recommended for alerts)",
            variable=self.startup_var, fg_color=ACCENT,
            hover_color=ACCENT_HOVER, command=self._on_startup_toggled,
        ).grid(row=row_base, column=0, sticky="w", padx=16, pady=(10, 4))
        row_base += 1

        # The two buttons at the bottom of the box.
        btn_row = ctk.CTkFrame(notif_frame, fg_color="transparent")
        btn_row.grid(row=row_base, column=0, sticky="w", padx=16, pady=(8, 14))

        ctk.CTkButton(
            btn_row, text="Send test notification", fg_color=ACCENT,
            hover_color=ACCENT_HOVER, command=self._test_notification,
        ).grid(row=0, column=0)

        ctk.CTkButton(
            btn_row, text="Quit app", fg_color="#3a3a42",
            hover_color="#4a4a52", command=self._quit_app,
        ).grid(row=0, column=1, padx=(10, 0))

        # A helpful hint about what the X button does on this computer.
        if IS_MACOS:
            hint = ("Closing the window keeps the countdown running — "
                    "click the Dock icon to reopen, or use Quit app to exit.")
        elif TRAY_AVAILABLE:
            hint = ("Closing the window keeps the countdown running in the "
                    "system tray. Right-click the tray icon to quit.")
        else:
            hint = ("Install pystray + Pillow to keep the app running when "
                    "the window is closed.")
        ctk.CTkLabel(
            self, text=hint, font=ctk.CTkFont(size=12), text_color=FG_DIM,
        ).grid(row=4, column=0, pady=(0, 12))

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
                APP_NAME, self._make_tray_image(), APP_NAME, menu
            )
            # The tray runs on its own helper thread so it never
            # blocks our window.
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception:
            # Some Linux desktops have no tray. Fine — app still works.
            self.tray_icon = None

    def _tray_show(self, *_):
        """User clicked 'Open' in the tray menu."""
        # The tray lives on another thread, and the window toolbox only
        # listens to its OWN thread — so we pass a note with after().
        self.after(0, self._show_window)

    def _tray_quit(self, *_):
        """User clicked 'Quit' in the tray menu."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.destroy)

    # ---------- Opening, hiding, and quitting the window ----------

    def _show_window(self):
        """Bring the window back and put it in front."""
        self.deiconify()     # un-hide
        self.lift()          # move on top of other windows
        self.focus_force()   # make it the active window
        # Wake the clock up RIGHT NOW so numbers are fresh instantly
        # (while hidden, we only check every 15 seconds to save power).
        if self._tick_job is not None:
            self.after_cancel(self._tick_job)  # cancel the lazy reminder
            self._tick_job = None
        self._tick()

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
            # If the computer said no, flip the checkbox back to the truth.
            self.startup_var.set(is_startup_enabled())

    def _test_notification(self):
        """The test button — send a practice pop-up."""
        send_notification(APP_NAME, f"Test toast! Counting down to {ALBUM_NAME} 🎧")

    # ---------- The heartbeat: the tick ----------

    def _tick(self):
        """Look at the clock, update the numbers, check for big moments.

        MEMORY SAVERS in here:
          * We only repaint a number if it actually changed.
          * While the window is hidden, we slow down to one check
            every 15 seconds (nobody can see the seconds anyway).
        """
        now = datetime.now(timezone.utc)              # what time is it NOW?
        remaining = (RELEASE_DT - now).total_seconds()  # how long is left?

        hidden = self.state() == "withdrawn"   # is the window hidden?

        if remaining <= 0:
            # THE ALBUM IS OUT! Switch to party mode (but only once).
            if not self._celebrating:
                self._celebrating = True
                for name in self.unit_labels:
                    self.unit_labels[name].configure(text="0")
                self.status_label.configure(
                    text='🎉 "This & That" IS OUT — STAY, go stream! 🎉',
                    text_color=ACCENT, font=self._font_celebrate,
                )
        elif not hidden:
            # Split the leftover seconds into weeks, days, hours, min, sec.
            total_seconds = int(remaining)
            weeks, rem = divmod(total_seconds, 7 * 24 * 3600)
            days, rem = divmod(rem, 24 * 3600)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)

            # Only touch labels whose number actually changed.
            # (Repainting all five every second wastes work — usually
            # only SECONDS changes.)
            for name, val in (("WEEKS", weeks), ("DAYS", days),
                              ("HOURS", hours), ("MINUTES", minutes),
                              ("SECONDS", seconds)):
                if self._last_shown.get(name) != val:
                    self._last_shown[name] = val
                    self.unit_labels[name].configure(text=str(val))

            # Update the "total days" line only when the day count changes.
            day_count = total_seconds // 86400
            if self._last_shown.get("day_count") != day_count:
                self._last_shown["day_count"] = day_count
                self.status_label.configure(
                    text=f"{day_count} total days remaining",
                    text_color=FG_DIM, font=self._font_status,
                )

        # Even when hidden, we still check whether it's time for an alert.
        self._check_milestones(remaining)

        # Ask to be woken up again: soon if visible, lazily if hidden.
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
        # (Ordered oldest to newest: 1 week ... release.)
        crossed = [
            (key, label, secs)
            for key, label, secs in MILESTONES
            if key not in fired
            and self.settings.get(key, True)
            and remaining <= secs
        ]
        if not crossed:
            self._startup_check_done = True
            return  # nothing new to announce

        changed = False
        for key, label, secs_before in crossed:
            # "Live" = we crossed this moment within the last hour,
            # meaning the app was awake when it happened.
            in_live_window = remaining > secs_before - 3600
            is_most_recent = key == crossed[-1][0]

            if in_live_window:
                # It just happened — announce it normally!
                if secs_before == 0:
                    send_notification(
                        "🎉 IT'S HERE!",
                        f"{ALBUM_NAME} is officially OUT. Go stream!",
                    )
                else:
                    send_notification(
                        APP_NAME, f"{label} until {ALBUM_NAME} drops!"
                    )
            elif not self._startup_check_done and is_most_recent:
                # It happened while the app was CLOSED. Now that we're
                # awake again, send ONE catch-up alert (only the newest
                # missed moment — no notification spam).
                if secs_before == 0:
                    send_notification(
                        "🎉 IT'S OUT!",
                        f"{ALBUM_NAME} dropped while the app was closed. "
                        "Go stream!",
                    )
                else:
                    send_notification(
                        APP_NAME,
                        f"While the app was closed: {label} until "
                        f"{ALBUM_NAME} drops!",
                    )
            # Older missed moments get quietly marked as done.

            fired.add(key)   # remember we handled this one
            changed = True

        self._startup_check_done = True
        if changed:
            self.settings["fired"] = sorted(fired)
            save_settings(self.settings)   # write it down so we remember
                                           # even after a restart


def main():
    """Make the window and hand control over to it. The end!"""
    app = CountdownApp()
    app.mainloop()   # this line runs until the app quits


if __name__ == "__main__":
    main()   # only auto-start if this file is run directly