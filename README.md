# SKZ Countdown — Stray Kids "This & That"

A desktop countdown app for the Stray Kids *"This & That"* album release:
**August 7, 2026 at 1:00 PM KST**. The app reads your computer's local
timezone and converts the release moment automatically — a STAY in Seoul,
New York, or London all see the correct countdown for *their* clock.

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
> free indie apps. Click **More info → Run anyway**.

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
| Timezone handling | `zoneinfo` (standard library) + `tzdata` — release anchored to `Asia/Seoul`, converted to the user's local timezone |
| Notifications | [plyer](https://github.com/kivy/plyer) with native fallbacks (`osascript` on macOS, `notify-send` on Linux) |
| System tray | [pystray](https://github.com/moses-palmer/pystray) + Pillow (Windows/Linux); Dock + `tk::mac::ReopenApplication` on macOS |
| Persistence | JSON settings in the OS-appropriate config directory (AppData / Application Support / `~/.config`) |
| Start at login | `winreg` Run key (Windows) · LaunchAgent plist (macOS) · XDG autostart entry (Linux) |
| Packaging | PyInstaller — standalone .exe / .app / binary, no Python required |
| CI/CD | GitHub Actions matrix build across `windows-latest`, `macos-latest`, `ubuntu-latest`, auto-attaching binaries to Releases |

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
- **CI/CD removes the "works on my machine" packaging problem.** PyInstaller
  can only build for the OS it runs on; a GitHub Actions matrix builds all
  three targets on every version tag and publishes them to Releases
  automatically.

## Features

- Live countdown (weeks, days, hours, minutes, seconds), updates every second
- **Timezone-aware:** anchored to 1:00 PM KST and converted to your system's
  local timezone, DST included. Your local release time is shown in the header.
- **Keeps running when you close it:**
  - Windows / Linux → minimizes to the system tray; right-click the tray icon
    to reopen or quit
  - macOS → keeps running in the Dock; click the Dock icon to reopen
  - A "Quit app" button in the UI fully exits on any platform
- **Never loses time:** the countdown is always computed live from the release
  timestamp vs. your system clock — even a full quit and relaunch shows the
  exact correct remaining time.
- Desktop notifications at milestones (1 week, 1 day, 1 hour, release) with
  per-milestone checkboxes and a master switch. Uses plyer with native
  fallbacks (`osascript` on macOS, `notify-send` on Linux).
- **Start at login** checkbox on all platforms:
  - Windows → per-user registry Run entry
  - macOS → LaunchAgent plist in `~/Library/LaunchAgents`
  - Linux → XDG autostart entry in `~/.config/autostart`
  - Unchecking removes it cleanly.
- Settings persist between launches (AppData / Application Support / .config)
- Celebration state once the album drops

## Build a downloadable app for each OS

PyInstaller builds for the OS you run it on — so build the Windows .exe on
Windows, the .app on a Mac, and the Linux binary on Linux. Build scripts are
included:

| OS      | Run                | Output                          |
|---------|--------------------|---------------------------------|
| Windows | `build_windows.bat`| `dist\SKZ Countdown.exe`        |
| macOS   | `./build_macos.sh` | `dist/SKZ Countdown.app`        |
| Linux   | `./build_linux.sh` | `dist/skz-countdown` (binary)   |

Each output is fully standalone — no Python needed on the target machine.

### Automated builds (GitHub Actions)

You don't need a Mac or Linux machine — the included workflow at
`.github/workflows/build.yml` builds all three automatically. After pushing
the repo to GitHub, cut a release like this:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub spins up Windows, macOS, and Linux runners, builds each binary with
PyInstaller, and publishes a Release with all three attached (`SKZ
Countdown.exe`, `SKZ-Countdown-macOS.zip`, `skz-countdown`). You can also
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

## Notes

- Milestones fire once each. If a milestone passes **while the app is shut
  down**, you get a catch-up alert for the most recent one the next time the
  app opens (e.g. "While the app was closed: 1 day to go!") — including an
  "it's out!" alert if the album dropped while the app was closed.
- Milestone alerts fire in real time while the app is running (foreground or
  tray/Dock) — enable "Start at login" so it's always alive after a reboot.

## About

Built by a computer engineering student at UMass Amherst as a portfolio
project — combining a K-pop comeback with cross-platform desktop development,
OS-level integration, and automated release pipelines. Feedback and PRs
welcome!