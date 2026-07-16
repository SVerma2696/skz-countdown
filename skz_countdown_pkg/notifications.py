"""
Everything about popping up a little notification message in the corner of
the screen — one function per operating system's own way of doing it, plus
send_notification() which tries them in the order most likely to work.
"""

import subprocess    # lets us run other programs (like notifications)
import threading      # lets us do two things at once

from .config import APP_NAME, IS_WINDOWS, IS_MACOS, IS_LINUX, PLYER_AVAILABLE

if PLYER_AVAILABLE:
    from plyer import notification as plyer_notification


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
