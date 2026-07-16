"""Starts the app: makes sure we're the only copy running, then opens the window."""

from .platform_integration import become_the_one_running_copy
from .ui import CountdownApp


def main():
    """Make the window and hand control over to it. The end!"""
    app = None

    def _on_relaunch_attempt():
        # Runs on a background thread, so hop over to the window's own
        # thread before touching it (the same trick the tray icon uses).
        if app is not None:
            app.after(0, app._show_window)

    result = become_the_one_running_copy(_on_relaunch_attempt)
    if result is None:
        return   # a REAL other copy is already running — we tapped it on
                 # the shoulder above, so we just quietly stop here

    # `result` is either our claimed socket (kept alive simply by staying
    # in scope for the rest of this function) or False, meaning we're
    # proceeding without single-instance protection this run — either way,
    # it's safe to open the window now.
    app = CountdownApp()
    app.mainloop()   # this line runs until the app quits
