# SKZ Countdown — Stray Kids "This & That"

A desktop countdown app for the Stray Kids *"This & That"* album release:
**August 7, 2026 at 1:00 PM KST**. The app reads your computer's local
timezone and converts the release moment automatically — a STAY in Seoul,
New York, or London all see the correct countdown for *their* clock.

A clean white, black, and red look (Stray Kids' own red) with the group's
icon and the album's title art built right into the header, plus a one-click
button back to this GitHub page.

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
> [Getting Windows to trust the app](#-getting-windows-to-trust-the-app) below
> for the full explanation and your options.

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
| Notifications | A real Windows 10/11 toast (via PowerShell + the WinRT notification API) on Windows; [plyer](https://github.com/kivy/plyer) with native fallbacks (`osascript` on macOS, `notify-send` on Linux) everywhere else |
| Images | [Pillow](https://python-pillow.org/) — loads the two logo pictures and draws the tray icon |
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
- **CI/CD removes the "works on my machine" packaging problem.** PyInstaller
  can only build for the OS it runs on; a GitHub Actions matrix builds all
  three targets on every version tag and publishes them to Releases
  automatically.

## Features

- Live countdown (weeks, days, hours, minutes, seconds), updates every second
- **Timezone-aware:** anchored to 1:00 PM KST and converted to your system's
  local timezone, DST included. Your local release time is shown in the header.
- **A white, black & red look**, built around the group's own icon and the
  album's title art, with a **"View on GitHub" button** built right into the
  window so anyone using the app can find the source in one click.
- **Keeps running when you close it:**
  - Windows / Linux → minimizes to the system tray; right-click the tray icon
    to reopen or quit
  - macOS → keeps running in the Dock; click the Dock icon to reopen
  - A "Quit app" button in the UI fully exits on any platform
- **Never loses time:** the countdown is always computed live from the release
  timestamp vs. your system clock — even a full quit and relaunch shows the
  exact correct remaining time.
- Desktop notifications at milestones (1 week, 1 day, 1 hour, release) with
  per-milestone checkboxes and a master switch. On Windows this uses a real
  Windows toast; macOS and Linux use plyer with native fallbacks (`osascript`
  / `notify-send`).
- **Start at login** checkbox on all platforms:
  - Windows → per-user registry Run entry
  - macOS → LaunchAgent plist in `~/Library/LaunchAgents`
  - Linux → XDG autostart entry in `~/.config/autostart`
  - Unchecking removes it cleanly.
- Settings persist between launches (AppData / Application Support / .config)
- Celebration state once the album drops

## 🖼️ Image credits

The two pictures in the app header aren't drawn by the app — they're:

- **Stray Kids icon** — [Icons8](https://icons8.com/icons/set/stray-kids)
  ([image source](https://img.icons8.com/plasticine/1200/stray-kids.jpg))
- **"This & That" title art** — from the album's page on
  [Spotify](https://open.spotify.com/album/46TYlDjLrEsOLFgxfxNiUy)
  ([image source](https://i.scdn.co/image/ab67616d00001e02cad184e653ea5dea71bc7365))

Both are also credited in a small line of text at the bottom of the app
window itself.

## Build a downloadable app for each OS

PyInstaller builds for the OS you run it on — so build the Windows .exe on
Windows, the .app on a Mac, and the Linux binary on Linux. Build scripts are
included, and each one packs the two logo pictures inside the finished app
(via `--add-data`) so they still show up once it's installed somewhere else;
the Windows build also sets `skz-logo.ico` as the .exe's own icon (via
`--icon`), so it shows correctly in File Explorer and the taskbar too.

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

## 🛡️ Getting Windows to trust the app

Windows SmartScreen warns on *any* app it hasn't "seen" from enough other
people yet, regardless of how safe it is — that's normal for a small free
project, not a sign something's wrong. Here's what you can do about it, from
quickest to most involved:

1. **"More info → Run anyway"** — click **More info** on the SmartScreen
   warning, then **Run anyway**. This is the standard, free way past it and
   is all most people need to do, once.
2. **Unblock the file before running it** — right-click the downloaded
   `.exe` → **Properties** → check **Unblock** at the bottom of the
   **General** tab → **OK**. This removes the "downloaded from the internet"
   flag Windows attaches to the file, so SmartScreen won't warn on it again.
3. **It gets easier over time, for free** — SmartScreen's warnings ease up
   automatically as more people download and run the same file without
   reporting problems ("reputation"). There's nothing to configure for
   this — it just happens as the Release gets more downloads.
4. **Remove the warning entirely (costs money)** — buy a code-signing
   certificate from a certificate authority (DigiCert, SSL.com, etc.) and
   sign the `.exe` with it (`signtool sign /f cert.pfx ...` after building).
   A standard certificate still needs to build up reputation like above; an
   **EV (Extended Validation)** certificate skips that and is trusted
   immediately, but costs noticeably more and requires a hardware security
   key. This is the only option that removes the warning for every user
   right away — reasonable for a paid or widely-distributed app, usually
   overkill for a free fan project like this one.

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

The Stray Kids name, the *"This & That"* album title, and the two logo
pictures (see [Image credits](#️-image-credits) above) are the property of
their respective owners (JYP Entertainment / Icons8 / Spotify) and are used
here for a non-commercial fan project. The MIT license covers this project's
own code only, not those third-party assets.

## About

Built by a computer engineering student at UMass Amherst as a portfolio
project — combining a K-pop comeback with cross-platform desktop development,
OS-level integration, and automated release pipelines. Feedback and PRs
welcome!
