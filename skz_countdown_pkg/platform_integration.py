"""
Everything about talking to the OPERATING SYSTEM itself instead of just
drawing a window: "run me when the computer starts up" (a different trick
on every OS), and "make sure only one copy of me is running at once."
"""

import os
import shlex        # helps write safe commands for Linux
import socket        # lets us check "is the app already open?"
import subprocess    # lets us run other programs
import sys           # tells us which operating system we're on
import threading      # lets us do two things at once

from .config import APP_ID, APP_NAME, IS_WINDOWS, IS_MACOS, _cfg_dir
from .notifications import send_notification

# ---------------- "Start at login" (every OS does this differently) ----------


def get_launch_command():
    """Figure out the exact command the computer should run at login."""
    if getattr(sys, "frozen", False):
        # We are a packaged .exe/.app — just run ourselves.
        return [sys.executable]
    # We are a plain .py script — run "python our_script.py".
    script = os.path.abspath(sys.argv[0])
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


# ---------------- Making sure only ONE copy of the app runs ----------------
# A little made-up phone number on your own computer (never leaves it) that
# only one copy of the app can "answer." Whoever answers first is the ONE
# real copy; anyone else just leaves a quick message and steps aside.
_SINGLE_INSTANCE_PORT = 47623
# If something ELSE on the computer happens to be using that exact phone
# number (rare, but possible), we try one backup number instead of just
# giving up — so double-clicking the app always opens SOMETHING.
_SINGLE_INSTANCE_PORT_FALLBACK = 47624


def _try_bind(port):
    """Try to claim one port as our own. Returns the claimed socket, or
    None if something is already using it."""
    claim = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        claim.bind(("127.0.0.1", port))
    except OSError:
        claim.close()
        return None
    claim.listen(5)
    return claim


def _tap_existing_copy(port):
    """Knock on a port to see if OUR OWN app is the one listening there.
    Returns True if we successfully delivered the "come to the front"
    message, False if nobody who speaks our language answered (meaning
    some OTHER, unrelated program is just squatting on that port)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tap:
            tap.settimeout(1)
            tap.connect(("127.0.0.1", port))
            tap.sendall(b"SHOW\n")
        return True
    except OSError:
        return False


def _listen_forever(claim, on_relaunch_attempt):
    """Sit and wait for a LATER copy of the app to tap us on the
    shoulder, asking us to come back to the front."""
    while True:
        try:
            conn, _addr = claim.accept()
        except OSError:
            return  # our claim got closed — time to stop listening
        with conn:
            try:
                conn.recv(64)
            except OSError:
                pass
        on_relaunch_attempt()


def become_the_one_running_copy(on_relaunch_attempt):
    """Try to become the one and only copy of this app that's running.

    Returns one of three things:
      * a socket "claim" (keep it around for as long as the app runs!) —
        we're the one true copy, everything continues as normal.
      * None — a REAL other copy of this app is already running (we tapped
        it on the shoulder so it comes to the front); we should stop here
        so a second window never opens.
      * False — nobody we could actually reach is running on either the
        main port or the backup port (maybe some unrelated program is
        using both, which is rare) — we give up on the "only one copy"
        protection for this run, but we still open the app normally.
        Silently refusing to open at all would be far more confusing than
        skipping this one safety feature.
    """
    claim = _try_bind(_SINGLE_INSTANCE_PORT)
    if claim is not None:
        threading.Thread(
            target=_listen_forever, args=(claim, on_relaunch_attempt),
            daemon=True).start()
        return claim

    # Someone's already on our usual port. Is it really us?
    if _tap_existing_copy(_SINGLE_INSTANCE_PORT):
        return None   # yes — a real duplicate. Stop here, quietly.

    # Not us — something unrelated is squatting on the port. Try a backup
    # port instead of just giving up.
    fallback_claim = _try_bind(_SINGLE_INSTANCE_PORT_FALLBACK)
    if fallback_claim is not None:
        threading.Thread(
            target=_listen_forever,
            args=(fallback_claim, on_relaunch_attempt), daemon=True).start()
        return fallback_claim

    # Both ports are blocked by something else. Let the app open anyway —
    # just without the "only one copy" protection this time — and say so,
    # so a curious user isn't left wondering why nothing happened.
    send_notification(
        APP_NAME,
        "Couldn't check for another running copy (a port was busy) — "
        "opening anyway.")
    return False
