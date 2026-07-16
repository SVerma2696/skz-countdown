"""
Stray Kids — "This & That" Album Countdown

WHAT THIS PROGRAM DOES (the simple version):
  1. It knows the exact moment the album comes out (from release.json).
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

THIS FILE ITSELF is intentionally tiny — it's just the "front door." All the
actual code lives next door in the skz_countdown_pkg/ folder, split into
small files that each do one job (drawing the window, sending notifications,
talking to the operating system, and so on). This file just walks through
that front door and says "go!"
"""

from skz_countdown_pkg.main import main

if __name__ == "__main__":
    main()   # only auto-start if this file is run directly
