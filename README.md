# SKZ Countdown — Stray Kids "This & That"

A desktop countdown app for the Stray Kids *"This & That"* album release:
**August 7, 2026 at 1:00 PM KST**. The app reads your computer's local
timezone and converts the release moment automatically — a STAY in Seoul,
New York, or London all see the correct countdown for *their* clock.

That release date lives in a small [`release.json`](#-pointing-this-at-a-different-comeback)
file, not hardcoded in the code — so the same app can count down to a
*different* comeback just by editing one file, and once release day passes
it doesn't dead-end: it quietly switches to a running "Day N since release"
counter instead of freezing on a one-time "it's out!" screen.

## 🆕 What's new in v1.6.1

- **Fixed a CI-breaking bug in v1.6.0's own test gate:** on Linux, just
  *importing* `pystray` (not even using it) tries to connect to a graphical
  (X11) display immediately — on a headless machine with no display at all
  (like a GitHub Actions runner, or a Linux box over plain SSH), that raises
  an `Xlib.error.DisplayNameError` instead of the plain `ImportError` the
  code was expecting, which crashed the entire app before a window could
  ever open. Broadened that one `except ImportError` to `except Exception`
  — no tray icon is a normal, harmless fallback; a surprise crash on import
  never should have been possible in the first place.

## 🆕 What's new in v1.6.0

- **Fixed a real timezone bug:** the "Your local time" line used to work
  out your computer's UTC offset once, using *today's* daylight-saving
  state, then reuse that same offset for every future date — wrong for any
  release date in a different daylight-saving season than today (e.g.
  viewing a December release from July). It's now resolved correctly for
  the release's *own* date every time, and recomputed on every tick so it
  stays correct even if the app has been running for weeks and a
  daylight-saving change happens while it's open.
- **`release.json` is now genuinely editable by anyone who downloads the
  app**, not just the person who built it: previously it was only ever read
  from inside the packaged .exe/.app, a temp folder that's deleted the
  moment the app closes — so nobody who just downloaded it could point it
  at a different comeback. It's now looked up in order (first match wins):
  next to the app itself → your saved-settings folder → the bundled
  default. See [Pointing this at a different comeback](#-pointing-this-at-a-different-comeback).
- **The tray icon is actually useful now without opening the window:**
  hovering it shows a live "12d 4h · This & That" tooltip, and its corner
  gets a tiny red LED-style number counting the days down — redrawn once a
  day, free the rest of the time.
- **The release moment is now one click, not a scroll:** the instant the
  countdown hits zero, a big "▶ Stream now" button appears right under it
  (there's also an opt-in "open it automatically" checkbox in Settings),
  instead of leaving the stream link several sections down the page.
- Packaging fix: the build scripts and CI workflow now actually bundle
  `release.json` into the built app (`--add-data`) — it was missing before,
  so a built .exe/.app was silently falling back to the "This & That"
  defaults no matter what release.json said.
- **Tests now gate every release build.** A new `test` job in
  `.github/workflows/build.yml` runs the full `pytest` suite first; the
  Windows, macOS, and Linux build jobs all wait on it passing. A broken
  release can no longer be published.
- The test suite grew from 12 to 28 tests: boundary cases for milestone
  alerts, a round-trip property test proving the countdown split always
  adds back up to the original total, `release.json` fallback behavior
  (a typo'd timezone, a nonexistent date like Feb 30th, missing keys), and
  the daylight-saving fix above.

## 🆕 What's new in v1.5.1

- The seven-segment countdown digits got a shape pass to look closer to a
  real physical LED display (like the reference photo they're modeled on):
  each bar's corners are now gently rounded instead of perfectly sharp
  points, the way real molded-plastic LED segments actually look up close.
- Fixed a long-standing bug in `.gitignore`: almost every rule in it had a
  trailing comment on the same line (`__pycache__/   # ...`), which isn't
  valid `.gitignore` syntax — git only treats a line as a comment if it
  *starts* with `#`. In practice this meant `__pycache__/`, `*.pyc`,
  `build/`, `dist/`, `*.spec`, `.venv/`, and `venv/` were never actually
  being ignored. Rewritten so every comment is on its own line.

## 🆕 What's new in v1.5.0

- **Fixed:** the countdown used to freeze at the last numbers (with a tiny
  stray "0" drawn on top) the moment the album dropped, instead of
  celebrating properly.
- **Fixed:** toggling dark mode *after* release used to permanently blank
  the countdown boxes to `--`.
- The release date/time/links/tracklist are now read from `release.json` at
  startup instead of being hardcoded, with a **post-release "Day N since
  release" mode** so the app stays useful long after the countdown ends.
- Dark mode now keeps the Settings window open when you toggle it, and the
  whole-page theme swap no longer flashes the old theme's background color
  for an instant or jumps your scroll position back to the top.
- The group photo's frame now hugs whatever photo is actually showing
  instead of always padding it into one fixed box.
- If the app's single-instance check ever finds its usual port blocked by
  something unrelated, it now falls back to a second port (and tells you)
  instead of silently refusing to open.
- The countdown math and milestone-alert logic were pulled out into small,
  pure, directly-testable functions (`skz_countdown_pkg/logic.py`, covered
  by `pytest` in `tests/`), and the whole app was split from one 1,925-line
  file into a handful of focused ones under `skz_countdown_pkg/` — see
  [Project layout](#-project-layout).

A black/white/red "engineering console" look, built around seven-segment
LED-style countdown digits (with a soft glow on the ticking seconds), a
typed boot-up line in the status bar, and a switchable **light/dark mode**.
All 8 members get their own card — click one to read a short bio — and the
album tracklist and one-click buttons to Spotify, Apple Music, and the Stray
Kids shop are all here too, plus a "View on GitHub" button back to this page.

Runs on **Windows, macOS, and Linux** (Python + CustomTkinter).

---

# 📥 How to Download

### ⭐ Just want the app? (no coding needed)

**[⬇ Click here to download the latest version](https://github.com/SVerma2696/skz-countdown/releases/latest)**

1. Scroll down to the **Assets** section
2. Click the file for your computer:

| Your computer | Download this | Then do this |
|---|---|---|
| 🪟 **Windows** | `SKZ-Countdown.exe` | Double-click it. That's it — no install needed. |
| 🍎 **Mac** | `SKZ-Countdown-macOS.zip` | Unzip it → drag the app into **Applications** → the **first time only**, right-click the app and choose **Open** |
| 🐧 **Linux** | `skz-countdown` | Open a terminal where you saved it and run: `chmod +x skz-countdown && ./skz-countdown` |

> 🪟 **Windows will warn you the first time** ("Windows protected your PC").
> This just means the app isn't signed with a paid certificate — normal for
> free indie apps. Click **More info → Run anyway**. See
> [Getting your computer to trust the app](#-getting-your-computer-to-trust-the-app)
> below for Windows, macOS, and Linux details.

### 💻 Want the source code instead? (for developers)

1. Click the green **`<> Code`** button at the top of this page
2. Choose **Download ZIP** (or run `git clone https://github.com/SVerma2696/skz-countdown.git`)
3. Unzip, open a terminal in the folder, and run:

```bash
pip install -r requirements.txt
python skz_countdown.py
```

---

## 🛠️ Built With

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| GUI | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — modern themed widgets on top of Tkinter |
| Timezone handling | `zoneinfo` (standard library) + `tzdata` — release anchored to whatever `release.json` says, converted to the user's local timezone *for that specific date* (correct across daylight saving, not just "today's" offset) |
| Notifications | A real Windows 10/11 toast (via PowerShell + the WinRT notification API) on Windows; [plyer](https://github.com/kivy/plyer) with native fallbacks (`osascript` on macOS, `notify-send` on Linux) everywhere else |
| Images | [Pillow](https://python-pillow.org/) — loads the logos, member/group photos and tracklist, draws placeholder art + the tray icon (including a live seven-segment day-count badge), and generates the memory-cached `CTkImage`s |
| Layout | `CTkScrollableFrame` with a centered max-width column, so it looks right from a small window up to full-screen |
| Links | `webbrowser` (standard library) — opens the album on Spotify / Apple Music / the store, and the repo on GitHub |
| System tray | [pystray](https://github.com/moses-palmer/pystray) + Pillow (Windows/Linux); Dock + `tk::mac::ReopenApplication` on macOS. The tooltip and a tiny red LED-style day-count badge stay live even while the window is hidden |
| Persistence | JSON settings in the OS-appropriate config directory (AppData / Application Support / `~/.config`) |
| Start at login | `winreg` Run key (Windows) · LaunchAgent plist (macOS) · XDG autostart entry (Linux) |
| Packaging | PyInstaller — standalone .exe / .app / binary, no Python required; icons (`.ico` / `.icns`) auto-generated at build time |
| CI/CD | GitHub Actions matrix build across `windows-latest`, `macos-latest`, `ubuntu-latest`, auto-attaching binaries to Releases — gated behind a `pytest` job, so a failing test blocks the build |
| Tests | `pytest`, 28 tests — the pure countdown/milestone math and the `release.json` config parsing both live in files with no GUI dependency, so they're directly unit-tested |

## 🗂️ Project layout

`skz_countdown.py` at the project root is just a thin "front door" — it
imports and runs the real app, which lives in `skz_countdown_pkg/`, split
into small files that each do one job:

| File | What it's responsible for |
|---|---|
| `config.py` | Constants, member data, themes, loading/saving your settings, and loading `release.json` |
| `logic.py` | The pure countdown math (no window, no widgets) — covered by `tests/test_logic.py` |
| `notifications.py` | Sending a pop-up notification, the right way for each OS |
| `platform_integration.py` | "Start at login" and the single-instance lock |
| `imaging.py` | Drawing placeholder photos and the seven-segment LED digits |
| `ui.py` | `CountdownApp` — the actual window |
| `main.py` | Ties the above together and starts the app |

This same split is why `python skz_countdown.py` and the build scripts still
work exactly as before — PyInstaller bundles the whole package automatically,
no build script changes needed.

## 📚 What I Learned

Building this taught me more about *cross-platform* development than any
single-OS project could:

- **Timezones are a data-modeling problem, not a math problem.** Storing one
  absolute moment (1:00 PM KST as a timezone-aware datetime) and converting
  at display time is robust; storing per-region offsets is a bug factory.
  `zoneinfo` handles DST transitions for free.
- **"Cross-platform" means three different operating systems' rules, not one
  codebase that ignores them.** Autostart alone required three separate
  mechanisms: a registry Run key on Windows, a LaunchAgent plist on macOS,
  and an XDG `.desktop` entry on Linux.
- **A toolkit's "it works everywhere" promise still has exceptions.** The
  plyer library's Windows notifications use an old "balloon tip" trick that
  Windows 10/11 frequently ignores — silently, with no error raised. The fix
  was to ask Windows directly for a real toast on that one platform instead
  of trusting the cross-platform abstraction blindly.
- **GUI toolkits and threads don't mix.** pystray runs in a background
  thread, but Tkinter is not thread-safe — tray callbacks have to marshal
  back onto the Tk main loop with `after()`. On macOS, pystray needs the
  main thread entirely, so the app uses the Dock + Tk's reopen hook instead.
- **Design for the app being closed.** The countdown is computed live from
  the release timestamp vs. the system clock (never a stored timer), and
  fired milestones persist to disk — so on relaunch the app knows which
  alerts were missed and sends a catch-up notification instead of spamming
  or silently skipping.
- **Graceful degradation beats hard dependencies.** Missing tray support or
  a flaky notification backend shouldn't crash a countdown app — every
  optional integration has a fallback path and the UI tells the user what's
  available.
- **Keeping memory flat over a long-running app.** This app can sit in the
  tray for weeks, so nothing is allowed to slowly leak. Fonts and images are
  built once and cached (a `CTkImage` per member/logo, reused forever), the
  countdown only repaints a digit when it actually changes, and while the
  window is hidden the loop slows from every 1s to every 15s. The member
  spotlight animates by only recoloring a border, not rebuilding widgets.
- **Missing assets should degrade, not crash.** Member and group photos are
  optional — if a file isn't there, the app draws a clean placeholder in its
  place, so it always looks finished and never errors over a missing picture.
- **"Pixels" aren't always pixels.** Windows' display scaling (125%/150%
  "make everything bigger") silently stretches every size you ask a widget
  for, so a crisp small picture can come out blurry, and a window sized to a
  fixed pixel guess can end up too narrow and clip content. The fix for both:
  draw pictures bigger than needed and shrink them down ourselves with a
  sharp filter, and size the window from what the content actually asks for
  *after* drawing it, instead of guessing a constant.
- **CI/CD removes the "works on my machine" packaging problem.** PyInstaller
  can only build for the OS it runs on; a GitHub Actions matrix builds all
  three targets on every version tag and publishes them to Releases
  automatically — even generating each platform's icon (`.ico` / `.icns`)
  on the fly.

## Features

- Live countdown (weeks, days, hours, minutes, seconds), updates every second,
  drawn as blocky **seven-segment "LED" digits** with a soft red glow behind
  the ticking seconds — the one digit that's always actively counting.
- **Timezone-aware:** anchored to the release moment in `release.json` and
  converted to your system's local timezone — correctly resolved for
  *that specific date's* daylight-saving state (not just today's), and
  re-checked every tick so it stays right even across a long-running
  session. Your local release time is shown in the header.
- **Light or dark mode:** a switch in Settings flips the whole app between a
  crisp white console and a near-black one — red stays the one accent color
  either way. Your choice is remembered between launches.
- **A typed "boot sequence"** in the status bar on launch (`> booting
  skz-countdown v1.6.1... tz-sync OK... target: 2026-08-07T13:00+09:00
  [LOCKED]`), finishing with a softly blinking cursor.
- **8 members, click one to learn more:** every member's card is always lit
  up; hovering one highlights it in red and flips its tag to a little status
  readout, and clicking opens a pop-up with their photo and a short bio. Drop
  in more than one photo for a member (or the group) and the app shuffles
  between them at a random moment, waiting a good while between changes —
  never the same picture twice in a row, and never on a predictable beat. The
  album **tracklist** is shown too. See
  [Adding your own images](#-adding-your-own-images) to swap in your own.
- **Whole photos, never cropped or stretched:** every picture (member, group,
  or logo) is shrunk to fit its box while keeping its own shape — if its
  proportions don't match the box exactly, you see a little breathing room on
  the sides instead of a cut-off or distorted photo.
- **One-click album links** to the [Stray Kids Shop](https://straykidsshop.com/collections/this-that),
  [Apple Music](https://music.apple.com/us/album/this-that/6781751949), and
  [Spotify](https://open.spotify.com/album/46TYlDjLrEsOLFgxfxNiUy), plus a
  **"View on GitHub"** button back to this repo.
- **Only one copy runs at a time:** opening the app again while it's already
  running (even minimized to the tray) just brings the existing window back
  to the front instead of launching a confusing second copy.
- **Clean "engineering console" look:** `// SECTION` headers, thin red
  circuit-trace dividers, a faint circuit-board texture behind the countdown,
  and a strict rule that red only ever marks the one active/important thing
  (the ticking seconds, a hovered member, the primary button) — never just
  decoration.
- **Full-screen friendly:** the whole page scrolls and stays centered in a
  comfy column whether the window is small or maximized, and the window sizes
  itself to whatever your display's scaling actually needs so nothing clips.
- **Settings live in a pop-up window** (the ⚙ button), so the main view stays
  clean: dark mode switch, master STAY-alert switch, per-milestone checkboxes,
  an opt-in "open the stream link automatically at release" checkbox,
  start-at-login, and a test-notification button.
- **The moment it drops, a big "▶ Stream now" button appears** right under
  the countdown — no scrolling down to find the link at the one moment you
  actually need it.
- **Keeps running when you close it:**
  - Windows / Linux → minimizes to the system tray; right-click to reopen/quit.
    The tray icon's tooltip shows a live "12d 4h · This & That" countdown, and
    a tiny red LED-style number in its corner counts the days down — so you
    can tell how long is left without opening the window at all.
  - macOS → keeps running in the Dock; click the Dock icon to reopen
  - A "Quit app" button fully exits on any platform
- **Never loses time:** the countdown is always computed live from the release
  timestamp vs. your system clock — even a full quit and relaunch is exact.
- Desktop notifications at milestones (1 week, 1 day, 1 hour, release). On
  Windows this uses a real Windows toast; macOS and Linux use plyer with
  native fallbacks (`osascript` / `notify-send`). If a milestone passes while
  the app is closed, you get one catch-up alert next launch.
- **Start at login** on all platforms (registry / LaunchAgent / XDG autostart)
- **Low, flat memory use:** images and fonts are cached and reused, digits
  repaint only on change, and the app idles slowly while hidden in the tray.
- Settings persist between launches. Once release day passes, the app
  celebrates once, then settles into a running "Day N since release"
  counter instead of a dead-end screen.

## 🖼️ Adding your own images

Drop picture files into the `assets/` folder and the app picks them up
automatically — PNG, JPG, and WEBP all work, and you can mix formats freely.
Anything missing just falls back to a clean placeholder (it never crashes
over a missing file):

- `assets/members/` — name each photo with the member's short nickname, then
  a number: `bc1.jpg`, `bc2.webp`, `bc3.jpg`, ... The app tries 1, 2, 3, ...
  until a number is missing, so add as many (or as few) photos per member as
  you like — with 2+, it shuffles between them at a random moment, never the
  same one twice in a row.

  | ID | Member | ID | Member |
  |---|---|---|---|
  | `bc` | Bang Chan | `h` | Han |
  | `lk` | Lee Know | `f` | Felix |
  | `cb` | Changbin | `s` | Seungmin |
  | `hj` | Hyunjin | `in` | I.N |

- `assets/group/` — group photos named `1.jpg`, `2.png`, `3.webp`, … (shuffled
  randomly, no immediate repeats — same idea as the members above)
- `assets/logos/` — *optional* official brand logos: `spotify-logo.png`,
  `applemusic-logo.webp`, `skzshoplogo.webp`, `github-logo.webp` (replaces the
  simple lettered placeholders). These are third-party trademarks, so they're
  **not** bundled by default.

Every photo is shown in full — shrunk to fit its box if needed, but never
stretched or cropped. Each folder has a `README.txt` repeating these names.
See [License & credits](#license) for the rules on what you can redistribute.

## 🎛️ Pointing this at a different comeback

[`release.json`](release.json) at the project root holds everything about
*which* release the app counts down to — edit it and the whole app updates,
no code changes needed:

```json
{
  "album_name": "Stray Kids — \"This & That\"",
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
    { "label": "...", "url": "...", "color": "#141416", "logo": "....webp" }
  ]
}
```

`release_timezone` is any [IANA timezone name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
(e.g. `"America/New_York"`); `release_tz_label` is just the short text shown
next to the release time (e.g. `"KST"`, `"EST"`). If `release.json` goes
missing or has a typo in it somewhere, the app quietly falls back to the
built-in "This & That" defaults instead of crashing — same idea as the
settings file.

**This works even on a downloaded, already-built app — no rebuild needed.**
The app looks for `release.json` in three places, in order, and uses the
first one it finds:

1. **Right next to the app itself** (the `.exe`/`.app`, or this script if
   you're running from source) — drop your own `release.json` beside it to
   point that exact copy at a different comeback.
2. **Your saved-settings folder** (the same place `skz_countdown_settings.json`
   lives) — works even if the app is installed somewhere you can't write new
   files, like `Program Files`.
3. **The copy bundled inside the app** — the built-in "This & That" default,
   always there as a safety net.

So a STAY could point a downloaded copy at the *next* comeback the day it's
announced, without anyone needing to cut a new release.

Once the release date passes, the app doesn't dead-end on a static "it's
out!" screen — it switches to a running **"Day N since release"** counter
underneath the album links, so it stays useful for as long as you keep it
running. And the exact moment it *does* drop, a big **"▶ Stream now"**
button appears right under the countdown (there's also an opt-in "open it
automatically" checkbox in Settings) — so the payoff is one click, not a
scroll down the page.

The tray icon also stays useful without opening the window at all: hover it
for a "12d 4h · This & That" tooltip, and its corner shows a tiny red
LED-style number counting the days down.

## 🧪 Running the tests

The countdown math, milestone-alert logic, timezone handling, and
`release.json` fallback behavior (`skz_countdown_pkg/logic.py` and
`skz_countdown_pkg/config.py`) have no GUI dependency, so they're covered by
plain `pytest` tests — 28 of them, covering boundary cases (a milestone
firing exactly at its mark, disabled/already-fired milestones being
skipped), the config fallbacks (a typo'd timezone, a nonexistent date like
Feb 30th, missing keys), and that daylight-saving time is resolved correctly
for the specific release date, not just "today":

```bash
pip install pytest
pytest
```

These same tests **gate every release build** — see
[Automated builds](#automated-builds-github-actions) below.

## 🖼️ Image credits

The pictures in the app header aren't drawn by the app — they're:

- **Stray Kids icon** — [Icons8](https://icons8.com/icons/set/stray-kids)
  ([image source](https://img.icons8.com/plasticine/1200/stray-kids.jpg))
- **"This & That" title art** — from the album's page on
  [Spotify](https://open.spotify.com/album/46TYlDjLrEsOLFgxfxNiUy)
  ([image source](https://i.scdn.co/image/ab67616d00001e02cad184e653ea5dea71bc7365))
- **Tracklist image** — the official *"This & That"* tracklist reveal.

The **member photos, group photos, and app-link logos** bundled in this
repo's `assets/` folder were added by the project's author. They're photos
and brand marks of their respective owners (JYP Entertainment, the
photographers, Spotify, Apple, the Stray Kids Shop, GitHub) — used here for
a non-commercial fan project, not covered by this project's own MIT license.
If you fork this project, swap in your own images or confirm you have the
right to use these before distributing them further.

The header credit line also appears in small text at the bottom of the app
window itself.

## Build a downloadable app for each OS

PyInstaller builds for the OS you run it on — so build the Windows .exe on
Windows, the .app on a Mac, and the Linux binary on Linux. Build scripts are
included, and each one bundles the logos, the tracklist, and the whole
`assets/` folder inside the finished app (via `--add-data`) so every picture
still shows once it's installed elsewhere. The Windows and macOS scripts also
**auto-generate the app icon** (`.ico` / `.icns`) from `skz-logo.png` at build
time — so the Stray Kids picture shows in Explorer/taskbar and in the Mac Dock,
and there's no icon file to commit.

| OS      | Run                | Output                          |
|---------|--------------------|---------------------------------|
| Windows | `build_windows.bat`| `dist\SKZ-Countdown.exe`        |
| macOS   | `./build_macos.sh` | `dist/SKZ-Countdown.app`        |
| Linux   | `./build_linux.sh` | `dist/skz-countdown` (binary)   |

Each output is fully standalone — no Python needed on the target machine.

### Automated builds (GitHub Actions)

You don't need a Mac or Linux machine — the included workflow at
`.github/workflows/build.yml` builds all three automatically. After pushing
the repo to GitHub, cut a release like this:

```bash
git tag v1.6.1
git push origin v1.6.1
```

**Tests gate every release.** Before any of the three platform builds start,
a `test` job runs the full `pytest` suite — the Windows, macOS, and Linux
build jobs all `needs: [test]`, so if the countdown math or milestone logic
is broken, GitHub simply won't build (let alone publish) any binary. A
broken release can't ship.

GitHub spins up Windows, macOS, and Linux runners, builds each binary with
PyInstaller, and publishes a Release with all three attached
(`SKZ-Countdown.exe`, `SKZ-Countdown-macOS.zip`, `skz-countdown`). You can also
trigger a build manually from the repo's **Actions** tab. Anyone can then
download the app for their OS straight from your Releases page.

### Platform notes

- **Windows:** Focus Assist / Do Not Disturb can suppress toasts.
- **macOS:** the .app is unsigned, so the first launch needs right-click →
  Open. Notifications via osascript appear under "Script Editor" unless the
  app is bundled/signed.
- **Linux:** notifications need `libnotify` (`notify-send`), preinstalled on
  most distros. The tray icon needs an AppIndicator-capable desktop — on
  GNOME, install the AppIndicator extension. If no tray is available, the app
  quits on close instead (the UI tells you).

## 🛡️ Getting your computer to trust the app

Every OS is cautious about apps downloaded from the internet that aren't
signed with a paid certificate. That warning is about *reputation*, not
safety — it's completely normal for a small free project. Here's how to get
past it on each system.

### 🪟 Windows (SmartScreen)

Windows SmartScreen warns on *any* app it hasn't "seen" from enough other
people yet. From quickest to most involved:

1. **"More info → Run anyway"** — click **More info** on the SmartScreen
   warning, then **Run anyway**. This is the standard, free way past it and
   is all most people need to do, once.
2. **Unblock the file before running it** — right-click the downloaded
   `.exe` → **Properties** → check **Unblock** at the bottom of the
   **General** tab → **OK**. This removes the "downloaded from the internet"
   flag, so SmartScreen won't warn on it again.
3. **It gets easier over time, for free** — SmartScreen eases up automatically
   as more people download and run the same file without problems
   ("reputation"). Nothing to configure — it just happens.
4. **Remove the warning entirely (costs money)** — buy a code-signing
   certificate (DigiCert, SSL.com, etc.) and sign the `.exe`
   (`signtool sign /f cert.pfx ...`). A standard cert still builds reputation
   like above; an **EV** cert is trusted immediately but costs more and needs
   a hardware key. Overkill for a free fan project.

### 🍎 macOS (Gatekeeper)

The `.app` is unsigned, so Gatekeeper blocks the normal double-click. Options,
quickest first:

1. **Right-click → Open** (not double-click) the first time, then click
   **Open** in the dialog. macOS remembers your choice, so future launches are
   a normal double-click.
2. **System Settings → Privacy & Security** — if you double-clicked and it was
   blocked, a button appears here saying *"…was blocked"* with an **Open
   Anyway** option.
3. **Strip the quarantine flag from Terminal** — `xattr -dr com.apple.quarantine
   "/Applications/SKZ-Countdown.app"` removes the "downloaded" mark so it opens
   cleanly.
4. **Remove the warning entirely (costs money)** — join the Apple Developer
   Program ($99/yr) and **sign + notarize** the app. This is the only way to
   make it open with no warning on *everyone's* Mac. Overkill for a fan project.

### 🐧 Linux

There's no Gatekeeper/SmartScreen — Linux just needs permission to run the
file: `chmod +x skz-countdown` then `./skz-countdown`. For pop-ups you need
`libnotify` (`notify-send`), and the tray needs an AppIndicator-capable
desktop (GNOME users: install the AppIndicator extension).

## Notes

- Milestones fire once each. If a milestone passes **while the app is shut
  down**, you get a catch-up alert for the most recent one the next time the
  app opens (e.g. "While the app was closed: 1 day to go!") — including an
  "it's out!" alert if the album dropped while the app was closed.
- Milestone alerts fire in real time while the app is running (foreground or
  tray/Dock) — enable "Start at login" so it's always alive after a reboot.

## License

The code in this repository is released under the [MIT License](LICENSE) —
use it, modify it, ship it, no strings attached.

The MIT license covers **this project's own code only.** It does **not** cover:

- The Stray Kids name and the *"This & That"* album title, artwork, tracklist,
  and the two header logo images — property of **JYP Entertainment** (and the
  icon via **Icons8** / album art via **Spotify**; see
  [Image credits](#️-image-credits)).
- The **member photos, group photos, and app-link logos** in `assets/`
  (bundled by this project's author, or added by you). Those are owned by
  their respective rights holders (the photographers, JYP Entertainment,
  Spotify, Apple, etc.), not by this project — using or redistributing them
  further is subject to those owners' terms.

This is a non-commercial fan project and is not affiliated with or endorsed by
JYP Entertainment or Stray Kids.

## About

Built by a computer engineering student at UMass Amherst as a portfolio
project — combining a K-pop comeback with cross-platform desktop development,
OS-level integration, and automated release pipelines. Feedback and PRs
welcome!