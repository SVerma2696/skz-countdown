"""
The window itself. Everything the user actually sees and clicks lives in
here — the CountdownApp class. It leans on the other files for the parts
that aren't really "drawing a window": config.py for facts and settings,
logic.py for the pure countdown math, imaging.py for pictures, and
notifications.py / platform_integration.py for talking to the OS.
"""

import os
import random   # lets us shuffle photos so they don't repeat in a row
import threading   # lets the tray icon run in the background
import webbrowser   # lets us open a web page, like our GitHub repo
from datetime import datetime, timezone

import customtkinter as ctk   # the toolbox that draws our pretty window

from .config import (
    ACCENT, ACCENT_HOVER, ALBUM_LINKS, ALBUM_NAME, APP_NAME, APP_VERSION,
    ARTIST_DISPLAY, FANDOM_NAME, IS_MACOS, IS_WINDOWS, MEMBERS, MEMBER_DESCRIPTIONS,
    MEMBER_PHOTO_PREFIX, MILESTONES, MONO_FONT, PIL_AVAILABLE, RELEASE_DT,
    RELEASE_TZ_LABEL, REPO_URL, SKZ_LOGO_FILE, STATUS_BAR_BG,
    THEMES, TITLE_DISPLAY, TRACKLIST_FILE, TRAY_AVAILABLE, TT_LOGO_FILE,
    BOOT_BLINK_MS, BOOT_TYPE_MS, GROUP_CYCLE_MAX_MS, GROUP_CYCLE_MIN_MS,
    MEMBER_CYCLE_MAX_MS, MEMBER_CYCLE_MIN_MS, TICK_HIDDEN_MS, TICK_VISIBLE_MS,
    _cfg_dir, _find_numbered_photo, load_settings, resource_path, save_settings,
)
from .imaging import (
    DIGIT_H, DIGIT_W, SEG_SUPERSAMPLE, make_group_placeholder,
    make_logo_placeholder, make_member_placeholder, seven_segment_digit,
)
from .logic import local_display_dt, milestones_crossed, split_remaining
from .notifications import send_notification
from .platform_integration import is_startup_enabled, set_startup

if PIL_AVAILABLE:
    from PIL import Image, ImageDraw, ImageOps, ImageTk

if TRAY_AVAILABLE:
    import pystray


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
        self._member_job = None        # reminder ID for the member photo shuffle
        self._group_job = None         # reminder ID for the group photo swap
        self._last_shown = {}          # what each number label says right now
        self._celebrating = False      # did we already switch to party mode?
        self._img_cache = {}           # remember finished pictures (CTkImage)
        self._img_cache_raw = {}       # remember raw PIL pictures (digits, PCB)
        self._group_index = 0          # which group photo is showing
        self._boot_generation = 0      # lets us cancel an old boot animation
        # (which photo each member is showing lives in self._member_current,
        # set up in _build_members once we know how many photos each has)

        # Dark mode or light mode? Read the choice we saved last time.
        self.dark_mode = bool(self.settings.get("dark_mode", False))
        self._apply_theme()   # works out self.BG_MAIN, self.FG_STRONG, etc.

        self.title(f"{APP_NAME} — {TITLE_DISPLAY}")
        self.minsize(880, 600)

        # MEMORY SAVER: make our fonts ONCE and reuse them forever.
        # (Making a new font every second would slowly eat RAM.)
        self._font_status = ctk.CTkFont(size=14)
        self._font_celebrate = ctk.CTkFont(size=20, weight="bold")
        self._font_section = ctk.CTkFont(family=MONO_FONT, size=13,
                                         weight="bold")
        self._font_num = ctk.CTkFont(family=MONO_FONT, size=34, weight="bold")
        self._font_unit = ctk.CTkFont(size=11, weight="bold")
        self._font_mono_small = ctk.CTkFont(family=MONO_FONT, size=10)

        self._load_logos()   # open our logo + title pictures, if we can
        self._build_ui()     # draw everything

        # SIZE THE WINDOW TO FIT WHAT WE ACTUALLY DREW, instead of guessing
        # a fixed pixel size: Windows' own "make everything bigger" display
        # setting scales up every widget we asked for by some factor we
        # don't control, so a fixed guess can end up too small and clip the
        # right edge. Asking the content frame what width it actually
        # needs, AFTER drawing everything, always fits — on any screen, at
        # any DPI setting. (Height stays a fixed, reasonable size — the
        # page scrolls vertically on purpose, so extra height just means
        # less scrolling, never anything clipped.)
        self.update_idletasks()
        fit_w = min(self.content.winfo_reqwidth() + 50,
                   self.winfo_screenwidth() - 80)
        fit_h = min(820, self.winfo_screenheight() - 120)
        self.geometry(f"{fit_w}x{fit_h}")

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
        self._cycle_members()   # start swapping member photos
        self._cycle_group()     # start swapping the group photo

    # ---------- Light mode / dark mode ----------

    def _apply_theme(self):
        """Work out which colors to paint with, based on light/dark mode.

        Everything else in the app reads colors off of "self" (like
        self.BG_MAIN) instead of a fixed value, so flipping this and
        redrawing the window is all it takes to re-theme everything.
        """
        theme = THEMES["dark" if self.dark_mode else "light"]
        for key, value in theme.items():
            setattr(self, key, value)
        ctk.set_appearance_mode("dark" if self.dark_mode else "light")

    def _on_dark_mode_toggled(self):
        """The 'Dark mode' switch in Settings was flipped."""
        self.dark_mode = bool(self.dark_mode_switch.get())
        self.settings["dark_mode"] = self.dark_mode
        save_settings(self.settings)
        self._apply_theme()
        # Placeholder pictures have the OLD border color baked in — throw
        # away the picture cache so they get redrawn in the new theme.
        self._img_cache.clear()
        self._img_cache_raw.clear()
        # Keep the Settings window OPEN across the toggle. _rebuild_ui()
        # only tears down the main page — this pop-up is a separate window
        # that's never touched by that rebuild, and every widget inside it
        # already re-paints itself automatically when the appearance mode
        # flips, EXCEPT its own background color, which was only set once
        # at creation time — so just refresh that one thing by hand.
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.configure(fg_color=self.BG_MAIN)
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Tear down and redraw the whole window.

        Re-coloring every single widget by hand when the theme changes
        would be a mess to keep correct — instead we just throw the old
        page away and build a fresh one, the same way it looked the first
        time the app opened.
        """
        for job_name in ("_tick_job", "_member_job", "_group_job"):
            job_id = getattr(self, job_name)
            if job_id is not None:
                self.after_cancel(job_id)
                setattr(self, job_name, None)

        # Remember how far down the page was scrolled, so swapping themes
        # doesn't ALSO jump the user back up to the top — a small thing,
        # but it's what makes the swap feel like "the same page, repainted"
        # instead of "a whole new page appeared."
        scroll_fraction = 0.0
        try:
            scroll_fraction = self.page._parent_canvas.yview()[0]
        except Exception:
            pass   # if this ever fails, just skip restoring position

        # Paint the window's own background in the NEW theme color BEFORE
        # throwing away the old page — otherwise, for one instant between
        # "old page gone" and "new page drawn", the window would still be
        # showing the OLD theme's background color, which is what causes a
        # visible flash when toggling.
        self.configure(fg_color=self.BG_MAIN)
        self.page.destroy()
        # The countdown boxes are BRAND NEW widgets that still just say
        # "--" — forget what we last painted, or _tick() will wrongly
        # think nothing changed and leave them showing "--" forever.
        self._last_shown = {}
        # Likewise, brand new widgets haven't celebrated yet — without this,
        # toggling the theme AFTER release would leave the new countdown
        # boxes stuck on "--" forever, since _tick() would think the
        # celebration already happened and never repaint them.
        self._celebrating = False
        self._build_ui()

        try:
            self.page._parent_canvas.yview_moveto(scroll_fraction)
        except Exception:
            pass

        self._tick()
        self._cycle_members()
        self._cycle_group()

    # ---------- Loading pictures (with a memory-saving cache) ----------

    def _get_image(self, path, size, kind, meta, hug=False):
        """Return a ready-to-show picture, loading it only once.

        path : where the real photo would be (may not exist)
        size : the box to fit the picture into, as (width, height)
        kind : "member", "group", or "logo" — decides the placeholder style
        meta : extra info for the placeholder (a name, number, or (label,color))
        hug  : if True, the picture is handed back at its OWN fitted size
               (no padding), so a frame built around it hugs its real shape
               instead of always being the same fixed box. Only the group
               photo uses this — the member row stays a fixed, aligned grid.

        MEMORY SAVER: once we've made a picture, we keep it in self._img_cache
        and hand back the same one next time instead of rebuilding it.
        """
        cache_key = (path, size, kind, hug)
        if cache_key in self._img_cache:
            return self._img_cache[cache_key]
        if not PIL_AVAILABLE:
            return None

        pic = None
        try:
            if path and os.path.exists(path):
                pic = Image.open(path)           # a real photo exists — use it!
                if pic.mode != "RGBA":
                    pic = pic.convert("RGBA")
                # SHOW THE WHOLE PICTURE: shrink it to fit inside the box
                # while keeping its own shape — never stretched, never
                # cropped. Image.LANCZOS keeps it crisp instead of blurry.
                fitted = ImageOps.contain(pic, size, Image.LANCZOS)
                if hug:
                    # Hand back the picture at its OWN fitted size — no
                    # padding — so a frame built around it hugs its real
                    # shape instead of leaving empty letterboxed strips.
                    pic = fitted
                else:
                    # The box has to stay an exact size (so cards line up),
                    # so we sit the fitted picture in the middle of a
                    # see-through canvas that size — any leftover strip
                    # just shows the card's own background peeking through,
                    # like a frame.
                    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
                    offset = ((size[0] - fitted.width) // 2,
                              (size[1] - fitted.height) // 2)
                    canvas.paste(fitted, offset, fitted)
                    pic = canvas
        except Exception:
            pic = None
        if pic is None:                          # no photo? draw a placeholder
            if kind == "member":
                pic = make_member_placeholder(meta, size, self.CARD_BORDER)
            elif kind == "group":
                pic = make_group_placeholder(meta, size, self.CARD_BORDER)
            else:  # logo
                label, color = meta
                pic = make_logo_placeholder(label, color, size)

        image_size = pic.size if hug else size
        image = ctk.CTkImage(light_image=pic, dark_image=pic, size=image_size)
        self._img_cache[cache_key] = image
        return image

    # ---------- The seven-segment countdown digits ----------

    def _digit_glyphs(self, w, h):
        """Return the 10 digit pictures (0-9), drawing each one only once
        and reusing it forever after (just like our other picture caches)
        — recomposing a whole number is then just pasting a couple of
        these together, which is cheap enough to do every tick.

        SHARPNESS: CustomTkinter secretly re-scales every picture we hand
        it by whatever "make everything bigger" display-scaling factor
        Windows is using (often 125%-150%) — and it does that resize with
        a plain filter that looks noticeably soft. So instead of drawing
        at the plain on-screen size and letting CTkImage do that resize
        alone, we draw at the REAL final pixel size ourselves (on-screen
        size × that scaling factor) using a sharp filter — so whatever
        CTkImage does afterwards is a no-op, not a second blurry resize.
        We still draw SEG_SUPERSAMPLE times bigger than even THAT and
        shrink down with Image.LANCZOS, for a crisp result either way.
        """
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        real_w, real_h = max(1, round(w * scale)), max(1, round(h * scale))
        cache_key = ("digitset", real_w, real_h, self.dark_mode)
        if cache_key not in self._img_cache_raw:
            big_w, big_h = real_w * SEG_SUPERSAMPLE, real_h * SEG_SUPERSAMPLE
            self._img_cache_raw[cache_key] = {
                ch: seven_segment_digit(ch, big_w, big_h, ACCENT, self.SEG_OFF)
                    .resize((real_w, real_h), Image.LANCZOS)
                for ch in "0123456789"
            }
        return self._img_cache_raw[cache_key]

    def _number_image(self, text, w, h, gap=6):
        """Turn a short string of digits into one seven-segment picture."""
        glyphs = self._digit_glyphs(w, h)
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        real_w = max(1, round(w * scale))
        real_h = max(1, round(h * scale))
        real_gap = max(1, round(gap * scale))
        total_real_w = len(text) * real_w + (len(text) - 1) * real_gap
        canvas = Image.new("RGBA", (total_real_w, real_h), (0, 0, 0, 0))
        x = 0
        for ch in text:
            canvas.alpha_composite(glyphs.get(ch, glyphs["0"]), (x, 0))
            x += real_w + real_gap
        total_w = len(text) * w + (len(text) - 1) * gap   # logical size
        return ctk.CTkImage(light_image=canvas, dark_image=canvas,
                            size=(total_w, h))

    # ---------- The faint circuit-board background ----------

    def _pcb_pattern_image(self, w, h):
        """Draw a very faint dot-grid — a subtle 'circuit board' texture.

        Drawn once and cached (like our other pictures), so it costs
        nothing extra on every tick — it's just a picture sitting there.
        """
        cache_key = ("pcb", w, h, self.dark_mode)
        if cache_key not in self._img_cache_raw:
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            # A faint red dot at every grid intersection — barely there,
            # just enough to hint at a circuit board underneath.
            alpha = 22 if self.dark_mode else 14
            dot_color = (228, 0, 43, alpha)
            step = 22
            for y in range(0, h, step):
                for x in range(0, w, step):
                    d.ellipse([x, y, x + 2, y + 2], fill=dot_color)
            self._img_cache_raw[cache_key] = img
        return self._img_cache_raw[cache_key]

    def _paint_pcb_background(self, frame, w=900, h=170):
        """Put the faint dot-grid picture behind a frame's content, like a
        circuit board peeking through underneath — a cheap, one-time-drawn
        decoration, not redrawn per frame."""
        if not PIL_AVAILABLE:
            return
        pic = self._pcb_pattern_image(w, h)
        img = ctk.CTkImage(light_image=pic, dark_image=pic, size=(w, h))
        bg_label = ctk.CTkLabel(frame, text="", image=img)
        bg_label.place(relx=0.5, rely=0, anchor="n")
        bg_label.lower()   # keep it BEHIND the real content in the frame

    def _find_member_photos(self, name, file_name):
        """Find every real photo we have for one member.

        Looks for files named like bc1.jpg, bc2.webp, bc3.jpg, ... (the
        member's short nickname from MEMBER_PHOTO_PREFIX, then 1, 2, 3,
        ...) directly inside assets/members/, trying every picture format
        we support for each number. Keeps counting until a number is
        missing. If none are found at all, falls back to the single flat
        file named after the member (e.g. assets/members/1_bang_chan.png);
        if that's missing too, returns an empty list and the app draws a
        placeholder instead.
        """
        folder = resource_path(os.path.join("assets", "members"))
        prefix = MEMBER_PHOTO_PREFIX.get(name)
        paths = []
        if prefix:
            i = 1
            while True:
                found = _find_numbered_photo(folder, prefix, i)
                if not found:
                    break
                paths.append(found)
                i += 1
        if not paths:
            flat = os.path.join(folder, file_name)
            if os.path.exists(flat):
                paths.append(flat)
        return paths

    def _member_photo(self, index, photo_index, size):
        """Get one specific photo for one member, at a given size (or
        their placeholder, if that member has no real photo yet)."""
        name, file_name = MEMBERS[index]
        paths = self._member_photo_paths[index]
        # Even with no real photo, we pass a stable (non-existent) path so
        # every member still gets their OWN cached placeholder picture.
        path = paths[photo_index] if paths else resource_path(
            os.path.join("assets", "members", file_name))
        return self._get_image(path, size, "member", name)

    def _group_photo(self, index, max_size):
        """Get a group photo by number (or its placeholder).

        Uses hug=True — the group frame has no fixed size of its own, so
        it naturally resizes to match whatever picture size comes back,
        instead of always showing the same padded box.
        """
        folder = resource_path(os.path.join("assets", "group"))
        path = _find_numbered_photo(folder, "", index)
        return self._get_image(path, max_size, "group", index, hug=True)

    def _logo_image(self, file_name, label, color, size):
        """Get a brand/GitHub logo (or a simple lettered placeholder)."""
        path = resource_path(os.path.join("assets", "logos", file_name))
        return self._get_image(path, size, "logo", (label, color))

    def _count_group_photos(self):
        """How many real group photos did the user add? (At least 1, so the
        placeholder always shows.)"""
        folder = resource_path(os.path.join("assets", "group"))
        count = 0
        for i in range(1, 21):   # check 1.* ... 20.*
            if _find_numbered_photo(folder, "", i):
                count += 1
            else:
                break
        return max(count, 1)

    def _load_logos(self):
        """Open the Stray Kids photo and the title-art picture."""
        self.skz_logo_image = None   # the round Stray Kids photo (header)
        self.skz_logo_source = None  # the original picture (for the tray icon)
        self.tt_logo_image = None    # the title-art picture
        self._icon_photos = []       # crisp small copies, for every window
        self._icon_ico_path = None   # a real .ico file (Windows only)
        if not PIL_AVAILABLE:
            return

        try:
            skz_pic = Image.open(resource_path(SKZ_LOGO_FILE)).convert("RGBA")
            self.skz_logo_source = skz_pic

            # MEMORY SAVER / SHARPNESS: shrink with a high-quality filter
            # OURSELVES before handing the picture to CTkImage. Letting the
            # widget toolkit stretch a big picture down to a small box uses
            # a blurrier filter and can look pixelated — doing it first
            # with Image.LANCZOS (a much crisper filter) fixes that.
            header_pic = skz_pic.resize((76, 76), Image.LANCZOS)
            self.skz_logo_image = ctk.CTkImage(
                light_image=header_pic, dark_image=header_pic, size=(76, 76))

            # Make a handful of ready-made small sizes for title bars and
            # taskbars. Giving Windows several crisp, exact-size copies
            # (instead of one huge picture it has to shrink itself) is what
            # keeps every window's icon looking sharp instead of blocky.
            self._icon_photos = [
                ImageTk.PhotoImage(skz_pic.resize((s, s), Image.LANCZOS))
                for s in (16, 20, 24, 32, 40, 48, 64)
            ]

            if IS_WINDOWS:
                # customtkinter secretly swaps the titlebar icon back to its
                # own logo unless we've set an .ico ourselves — so we do.
                # A generous list of sizes means Windows almost always finds
                # an exact match instead of stretching a mismatched one.
                self._icon_ico_path = os.path.join(
                    _cfg_dir, "skz_countdown_icon.ico")
                ico_sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
                skz_pic.save(
                    self._icon_ico_path, format="ICO",
                    sizes=[(s, s) for s in ico_sizes],
                )

            self._set_window_icon(self)
        except Exception:
            pass  # a missing picture should never crash the countdown

        try:
            tt_pic = Image.open(resource_path(TT_LOGO_FILE))
            width, height = tt_pic.size
            target_h = 66
            target_w = int(width * (target_h / height))
            tt_pic = tt_pic.resize((target_w, target_h), Image.LANCZOS)
            self.tt_logo_image = ctk.CTkImage(
                light_image=tt_pic, dark_image=tt_pic,
                size=(target_w, target_h))
        except Exception:
            pass

    def _set_window_icon(self, window):
        """Put the Stray Kids picture in one window's title bar/taskbar spot.

        Every separate window — the main one, Settings, a member's pop-up —
        has to be told about the icon on its own; Windows doesn't share it
        automatically between windows.
        """
        if not self._icon_photos:
            return
        try:
            window.iconphoto(True, *self._icon_photos)
            if IS_WINDOWS and self._icon_ico_path:
                window.iconbitmap(self._icon_ico_path)
        except Exception:
            pass  # a window without our icon should never crash the app

    # ---------- Opening web links ----------

    def _open_url(self, url):
        """Open any web address in the person's normal web browser."""
        webbrowser.open(url)

    # ---------- Small building-block helpers ----------

    def _section_header(self, parent, text):
        """A '// TITLE' row that looks like a code comment, with a line.

        The leading "//" is our one recurring slash motif, tying every
        section back to the same "circuit trace" divider style — that's
        why this text stays red even though most decoration doesn't.
        """
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text=text, font=self._font_section,
                     text_color=ACCENT).grid(row=0, column=0, sticky="w")
        ctk.CTkFrame(row, height=2, fg_color=self.DIVIDER,
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
        self.page = ctk.CTkScrollableFrame(self, fg_color=self.BG_MAIN)
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
        """A thin monospace strip up top — the 'engineering console' touch.

        On launch it "boots up": one line of text types itself out, then a
        cursor block keeps softly blinking, like a real machine powering on.
        """
        bar = ctk.CTkFrame(parent, fg_color=STATUS_BAR_BG, corner_radius=6)
        bar.grid(row=row, column=0, sticky="ew", pady=(8, 14))
        bar.grid_columnconfigure(0, weight=1)
        self.boot_label = ctk.CTkLabel(
            bar, text="", anchor="w",
            font=ctk.CTkFont(family=MONO_FONT, size=11, weight="bold"),
            text_color="#FFFFFF",
        )
        self.boot_label.grid(row=0, column=0, sticky="ew", padx=(10, 10),
                             pady=6)
        self._start_boot_sequence()

    def _start_boot_sequence(self):
        """Kick off the typed 'booting up' line in the status bar."""
        self._boot_generation += 1   # cancels any earlier boot animation
        # The release's own UTC offset (e.g. "+09:00"), worked out from
        # RELEASE_DT itself instead of a hardcoded number — so this line
        # stays correct even if release.json points at a different timezone.
        raw_offset = RELEASE_DT.strftime("%z") or "+0000"   # e.g. "+0900"
        offset = f"{raw_offset[:3]}:{raw_offset[3:]}"        # "+09:00"
        target = RELEASE_DT.strftime("%Y-%m-%dT%H:%M") + offset
        self._boot_full_text = (
            f"> booting {APP_NAME.lower().replace(' ', '-')} "
            f"v{APP_VERSION}... tz-sync OK... target: {target} [LOCKED]"
        )
        self._boot_progress = 0
        self._type_boot_line(self._boot_generation)

    def _type_boot_line(self, generation):
        """Reveal one more character of the boot line, then schedule the
        next one a moment later — cheap to do, and it looks like a machine
        booting up instead of text just appearing all at once."""
        if generation != self._boot_generation:
            return   # a newer boot sequence started (e.g. the theme changed)
        self._boot_progress += 1
        shown = self._boot_full_text[:self._boot_progress]
        cursor = "█" if self._boot_progress % 2 == 0 else " "
        self.boot_label.configure(text=shown + cursor)
        if self._boot_progress < len(self._boot_full_text):
            self.after(BOOT_TYPE_MS, lambda: self._type_boot_line(generation))
        else:
            self._blink_boot_cursor(generation, True)

    def _blink_boot_cursor(self, generation, on):
        """Once the line has finished typing, blink a soft cursor block
        forever — a tiny, cheap 'still alive' touch."""
        if generation != self._boot_generation:
            return
        self.boot_label.configure(text=self._boot_full_text + ("█" if on else " "))
        self.after(BOOT_BLINK_MS, lambda: self._blink_boot_cursor(generation, not on))

    def _build_header(self, parent, row):
        """The logo, title art, and the exact local release time."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=row, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        if self.skz_logo_image is not None:
            ctk.CTkLabel(header, text="", image=self.skz_logo_image).pack(
                pady=(0, 6))
        ctk.CTkLabel(
            header, text=ARTIST_DISPLAY, font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.FG_DIM,
        ).pack()

        if self.tt_logo_image is not None:
            ctk.CTkLabel(header, text="", image=self.tt_logo_image).pack(
                pady=(6, 0))
        else:
            ctk.CTkLabel(
                header, text=f'"{TITLE_DISPLAY}"',
                font=ctk.CTkFont(size=34, weight="bold"), text_color=ACCENT,
            ).pack(pady=(6, 0))

        # Built from RELEASE_DT itself (not a fixed sentence), so this line
        # is always right — even for a release.json pointing at a totally
        # different date, time, timezone, or fandom name.
        release_str = RELEASE_DT.strftime(
            "%B %d, %Y · %I:%M %p").replace(" 0", " ")
        ctk.CTkLabel(
            header,
            text=(f"Drops {release_str} {RELEASE_TZ_LABEL} — "
                  f"for {FANDOM_NAME}"),
            font=ctk.CTkFont(size=13), text_color=self.FG_DIM,
        ).pack(pady=(6, 0))

        # Worked out FRESH here (not from a value saved once at startup) —
        # see _refresh_local_time_label() for why that matters and how
        # this label keeps itself correct while the app keeps running.
        self.local_time_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.FG_STRONG,
        )
        self.local_time_label.pack(pady=(2, 0))
        self._refresh_local_time_label(force=True)

        # A thin red circuit-trace line under the header.
        ctk.CTkFrame(header, height=2, fg_color=ACCENT, corner_radius=0).pack(
            fill="x", padx=60, pady=(14, 0))

    def _refresh_local_time_label(self, force=False):
        """Update the "Your local time: ..." line.

        BUG THIS FIXES: your computer's timezone isn't just one fixed
        number like "-4 hours" — places with daylight saving use a
        DIFFERENT offset in summer than in winter. The old code asked
        "what's my offset RIGHT NOW?" once when the app started, then
        reused that same answer for every date forever — which is wrong
        for any release date in a different daylight-saving season than
        today. local_display_dt() asks the correct question instead:
        "what's the offset on THIS SPECIFIC DATE?"

        We also don't just compute this once — we re-check it here, every
        tick, so an app that's been sitting in the tray for weeks (or
        traveled somewhere new) stays correct through a daylight-saving
        change instead of freezing its answer at startup.
        """
        local_dt = local_display_dt(RELEASE_DT)
        tz_name = local_dt.strftime("%Z") or str(local_dt.tzinfo)
        local_str = local_dt.strftime(
            "%A, %B %d, %Y · %I:%M %p").replace(" 0", " ")
        text = f"Your local time: {local_str} ({tz_name})"
        if force or self._last_shown.get("local_time_str") != text:
            self._last_shown["local_time_str"] = text
            self.local_time_label.configure(text=text)

    def _build_countdown(self, parent, row):
        """The five big number boxes: weeks, days, hours, minutes, seconds.

        The numbers themselves are drawn as flat, crisp seven-segment "LED"
        digits — see imaging.seven_segment_digit(). Only the SECONDS box
        gets a red outline: it's the one thing that's always actively
        ticking, so it's the one box red is allowed to decorate.
        """
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", pady=(16, 6))
        wrap.grid_columnconfigure(0, weight=1)
        self._paint_pcb_background(wrap)   # a faint circuit-board texture

        units = ctk.CTkFrame(wrap, fg_color="transparent")
        units.grid(row=0, column=0)
        self.unit_labels = {}
        for i, name in enumerate(["WEEKS", "DAYS", "HOURS", "MINUTES",
                                  "SECONDS"]):
            is_seconds = name == "SECONDS"
            border = ACCENT if is_seconds else self.CARD_BORDER
            card = ctk.CTkFrame(units, corner_radius=14, fg_color=self.BG_CARD,
                                border_width=1, border_color=border, width=260)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            card.grid_propagate(False)
            card.configure(height=270)
            value = ctk.CTkLabel(card, text="--", font=self._font_num,
                                 text_color=self.FG_STRONG)
            value.pack(pady=(46, 0))
            ctk.CTkLabel(card, text=name, font=self._font_unit,
                         text_color=self.FG_DIM).pack(pady=(12, 20))
            self.unit_labels[name] = value

        self.status_label = ctk.CTkLabel(
            wrap, text="", font=self._font_status, text_color=self.FG_DIM)
        self.status_label.grid(row=1, column=0, pady=(12, 0))

        # A big, obvious "go do the thing" button — built now but kept
        # HIDDEN (never gridded) until the album actually drops. See
        # _tick(): the moment we switch into celebration mode, this button
        # appears right under the countdown instead of making you scroll
        # all the way down to "GET THE ALBUM" to act on the one moment
        # this whole app exists for.
        self.stream_now_btn = ctk.CTkButton(
            wrap, text=f"▶  Stream {TITLE_DISPLAY} now", fg_color=ACCENT,
            hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=ctk.CTkFont(size=16, weight="bold"), height=48,
            corner_radius=10, command=self._open_stream_now,
        )
        if self._celebrating:
            self.stream_now_btn.grid(row=2, column=0, pady=(16, 0))

    def _primary_stream_link(self):
        """Which link should the big 'Stream now' button (and the
        auto-open-at-release setting) use? Prefer Spotify — it's what most
        people mean by "stream" — and if a release.json doesn't happen to
        have one, fall back to whichever link is listed first rather than
        having no button at all. Returns (label, url), or (None, None) if
        somehow there are no links configured at all."""
        for label, url, _color, _logo in ALBUM_LINKS:
            if label.strip().lower() == "spotify":
                return label, url
        if ALBUM_LINKS:
            return ALBUM_LINKS[0][0], ALBUM_LINKS[0][1]
        return None, None

    def _open_stream_now(self):
        """The big 'Stream now' button was clicked (or the auto-open-at-
        release setting fired on its own)."""
        _label, url = self._primary_stream_link()
        if url:
            self._open_url(url)

    def _build_album_links(self, parent, row):
        """Buttons that jump straight to the album online.

        Each label ends with a small "↗" arrow — a quiet, consistent hint
        that the button leaves the app and opens a web page.
        """
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
                btns, text=f"  {label} ↗", image=logo, compound="left",
                fg_color=color, hover_color=color, text_color="#FFFFFF",
                font=ctk.CTkFont(family=MONO_FONT, size=13, weight="bold"),
                height=42, corner_radius=8,
                command=lambda u=url: self._open_url(u),
            )
            btn.grid(row=0, column=i, padx=6)

    def _build_members(self, parent, row):
        """8 columns — one per member — click one to learn more.

        Cards keep a plain neutral outline until you hover one: THEN it
        lights up red and its little mono tag flips to a "status readout" —
        red still means "the thing that's active right now," it's just the
        mouse deciding what's active instead of an automatic timer.
        """
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(24, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// MEMBERS · OT8  (click one to learn more)").grid(
            row=0, column=0, sticky="ew")

        strip = ctk.CTkFrame(box, fg_color="transparent")
        strip.grid(row=1, column=0, pady=(14, 0))

        # Work out (once) which real photos each member has, so we know
        # what to shuffle through later.
        self._member_photo_paths = [
            self._find_member_photos(name, file_name) for name, file_name in MEMBERS
        ]
        self._member_current = [0] * len(MEMBERS)   # which photo is showing now
        self._member_thumb_size = (94, 126)

        self.member_cards = []          # (card, name_label) per member
        self.member_photo_labels = []   # the photo CTkLabel per member
        self.member_meta_labels = []    # the small mono "#01" tag per member
        for i, (name, file_name) in enumerate(MEMBERS):
            card = ctk.CTkFrame(strip, corner_radius=10, fg_color=self.BG_CARD,
                                border_width=2, border_color=self.CARD_BORDER)
            card.grid(row=0, column=i, padx=3, sticky="n")
            photo = self._member_photo(i, 0, self._member_thumb_size)
            img_label = ctk.CTkLabel(card, text="", image=photo)
            img_label.pack(padx=6, pady=6)
            name_label = ctk.CTkLabel(
                card, text=name, font=ctk.CTkFont(size=11, weight="bold"),
                text_color=self.FG_STRONG)
            name_label.pack()
            meta_label = ctk.CTkLabel(
                card, text=f"#{i + 1:02d}", font=self._font_mono_small,
                text_color=self.FG_DIM)
            meta_label.pack(pady=(0, 8))

            # Clicking anywhere on the card opens that member's info pop-up;
            # hovering it is the one moment red is allowed to show up here.
            for widget in (card, img_label, name_label, meta_label):
                widget.bind("<Button-1>",
                            lambda _e, idx=i: self._open_member_popup(idx))
                widget.bind("<Enter>",
                            lambda _e, idx=i: self._on_member_hover(idx, True))
                widget.bind("<Leave>",
                            lambda _e, idx=i: self._on_member_hover(idx, False))
                try:
                    widget.configure(cursor="hand2")   # hint it's clickable
                except Exception:
                    pass

            self.member_cards.append((card, name_label))
            self.member_photo_labels.append(img_label)
            self.member_meta_labels.append(meta_label)

    def _on_member_hover(self, index, entering):
        """The mouse entered or left one member's card."""
        card, _name_label = self.member_cards[index]
        meta_label = self.member_meta_labels[index]
        if entering:
            card.configure(border_color=ACCENT)
            meta_label.configure(text="STATUS: OT8 ✓", text_color=ACCENT)
        else:
            card.configure(border_color=self.CARD_BORDER)
            meta_label.configure(text=f"#{index + 1:02d}", text_color=self.FG_DIM)

    def _build_group(self, parent, row):
        """A wider area that cycles through group photos.

        The frame around the photo has no fixed size of its own, so it
        naturally hugs whatever picture is showing — see _group_photo()'s
        hug=True — instead of always being padded to one fixed box.
        """
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=0, sticky="ew", pady=(24, 6))
        box.grid_columnconfigure(0, weight=1)
        self._section_header(box, "// GROUP").grid(
            row=0, column=0, sticky="ew")

        frame = ctk.CTkFrame(box, corner_radius=10, fg_color=self.BG_CARD,
                             border_width=2, border_color=self.CARD_BORDER)
        frame.grid(row=1, column=0, pady=(14, 0))
        self._group_size = (560, 300)   # the MAX box a group photo fits inside
        self._group_index = 1   # matches the photo we show first, below
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
                pic = pic.resize((target_w, target_h), Image.LANCZOS)
                img = ctk.CTkImage(light_image=pic, dark_image=pic,
                                   size=(target_w, target_h))
        except Exception:
            img = None

        frame = ctk.CTkFrame(box, corner_radius=10, fg_color=self.BG_CARD,
                             border_width=1, border_color=self.CARD_BORDER)
        frame.grid(row=1, column=0, pady=(14, 0))
        if img is not None:
            ctk.CTkLabel(frame, text="", image=img).pack(padx=12, pady=12)
        else:
            ctk.CTkLabel(
                frame, text=f"{TRACKLIST_FILE} not found",
                font=self._font_status, text_color=self.FG_DIM,
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
        gh_logo = self._logo_image("github-logo.webp", "GitHub", self.CHIP_DARK, (20, 20))
        ctk.CTkButton(
            btns, text="  GitHub ↗", image=gh_logo, compound="left",
            fg_color=self.CHIP_DARK, hover_color=ACCENT_HOVER, border_width=1,
            border_color=self.CHIP_TEXT, text_color=self.CHIP_TEXT, height=40,
            font=ctk.CTkFont(family=MONO_FONT, size=13),
            command=lambda: self._open_url(REPO_URL),
        ).grid(row=0, column=1, padx=6)

        ctk.CTkButton(
            btns, text="Quit app", fg_color=self.CHIP_DARK, hover_color=ACCENT_HOVER,
            border_width=1, border_color=self.FG_DIM, text_color=self.CHIP_TEXT,
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
                     text_color=self.FG_DIM).grid(row=1, column=0, pady=(14, 2))

        ctk.CTkLabel(
            box, text=(f"Made for {FANDOM_NAME}. Member & group images are "
                       "placeholders — add your own in assets/. Stray Kids "
                       "icon via Icons8 · Album art via Spotify."),
            font=ctk.CTkFont(size=10), text_color=self.FG_DIM, wraplength=560,
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
        win.geometry("420x580")
        win.configure(fg_color=self.BG_MAIN)
        win.transient(self)          # keep it attached to the main window
        self._set_window_icon(win)   # give this window our icon too
        self.settings_win = win

        ctk.CTkLabel(
            win, text="// APPEARANCE", font=self._font_section,
            text_color=ACCENT).pack(anchor="w", padx=20, pady=(18, 0))
        appearance_row = ctk.CTkFrame(win, fg_color="transparent")
        appearance_row.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(appearance_row, text="Dark mode",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.dark_mode_switch = ctk.CTkSwitch(
            appearance_row, text="", progress_color=ACCENT,
            command=self._on_dark_mode_toggled)
        self.dark_mode_switch.pack(side="right")
        if self.dark_mode:
            self.dark_mode_switch.select()

        ctk.CTkLabel(
            win, text=f"// {FANDOM_NAME} ALERTS", font=self._font_section,
            text_color=ACCENT).pack(anchor="w", padx=20, pady=(14, 0))

        # The big ON/OFF switch for all notifications.
        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(top, text=f"All {FANDOM_NAME} alerts",
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

        ctk.CTkLabel(
            win, text="// AT RELEASE", font=self._font_section,
            text_color=ACCENT).pack(anchor="w", padx=20, pady=(14, 0))
        self.auto_open_var = ctk.BooleanVar(
            value=self.settings.get("auto_open_at_release", False))
        stream_label, _stream_url = self._primary_stream_link()
        ctk.CTkCheckBox(
            win, text=f"Open {stream_label or 'the album link'} automatically "
                      "the moment it drops",
            variable=self.auto_open_var, fg_color=ACCENT,
            hover_color=ACCENT_HOVER, command=self._on_setting_changed,
        ).pack(anchor="w", padx=24, pady=(8, 4))

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

    # ---------- The pop-up "about this member" window ----------

    def _open_member_popup(self, index):
        """Show one member's photo, name, and a short description."""
        name, _file_name = MEMBERS[index]
        description = MEMBER_DESCRIPTIONS.get(name, "")

        win = ctk.CTkToplevel(self)
        win.title(f"{APP_NAME} — {name}")
        win.geometry("360x480")
        win.configure(fg_color=self.BG_MAIN)
        win.transient(self)
        self._set_window_icon(win)   # this pop-up gets our icon too

        # A bigger version of whichever photo that member is showing
        # right now (loaded fresh at a bigger size — our picture cache
        # remembers it, so re-opening the same member is instant).
        big_size = (200, 268)
        photo = self._member_photo(index, self._member_current[index], big_size)
        ctk.CTkLabel(win, text="", image=photo).pack(pady=(26, 12))
        ctk.CTkLabel(
            win, text=name, font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.FG_STRONG,
        ).pack()
        ctk.CTkLabel(
            win, text=f"#{index + 1:02d}  ·  OT8", font=self._font_mono_small,
            text_color=self.FG_DIM,
        ).pack(pady=(2, 0))
        ctk.CTkLabel(
            win, text=description, font=ctk.CTkFont(size=13),
            text_color=self.FG_DIM, wraplength=300, justify="center",
        ).pack(padx=24, pady=(12, 20))

    # ---------- The tray icon (Windows / Linux only) ----------

    def _make_tray_image(self, days_left=None):
        """Draw our tray icon: the real Stray Kids picture if we have it,
        otherwise a simple red circle so the app still looks finished.

        If days_left is given, we also stamp a tiny red LED-style number
        into the bottom-right corner — the SAME seven-segment digits the
        big countdown boxes use, just tiny. The app spends almost all of
        its life living quietly in the tray, never opened — this way you
        can tell "how many days left?" just by glancing at the tray, with
        no click required, which is the whole point of living there.
        """
        if self.skz_logo_source is not None:
            base = self.skz_logo_source.resize((64, 64), Image.LANCZOS).convert("RGBA")
        else:
            base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))  # see-through square
            d = ImageDraw.Draw(base)
            d.ellipse([4, 4, 60, 60], fill=ACCENT)       # big red circle
            d.ellipse([22, 22, 42, 42], fill="#111114")  # dark hole in the middle

        if days_left is None or not PIL_AVAILABLE:
            return base

        base = base.copy()   # don't scribble on the shared logo picture
        text = str(max(0, min(days_left, 99)))   # keep it to at most 2 digits
        digit_w, digit_h = 12, 20
        gap = 2
        badge_w = len(text) * digit_w + (len(text) - 1) * gap + 6
        badge_h = digit_h + 6
        # A small near-black plate behind the digits, so the red LED look
        # reads clearly no matter what's behind the tray icon (a light
        # taskbar, a dark one, a busy desktop background through it, ...).
        badge = Image.new("RGBA", (badge_w, badge_h), (17, 17, 20, 235))
        x = 3
        for ch in text:
            glyph = seven_segment_digit(
                ch, digit_w * SEG_SUPERSAMPLE, digit_h * SEG_SUPERSAMPLE,
                ACCENT, "#3A171C",
            ).resize((digit_w, digit_h), Image.LANCZOS)
            badge.alpha_composite(glyph, (x, 3))
            x += digit_w + gap
        base.alpha_composite(badge, (64 - badge_w - 1, 64 - badge_h - 1))
        return base

    def _update_tray(self, remaining):
        """Keep the tray icon's tooltip text AND its little corner number
        fresh. Together these are the whole point of a tray icon: you
        should be able to tell how long is left WITHOUT opening the
        window at all.
        """
        if not self.tray_icon:
            return

        if remaining <= 0:
            title = f"{TITLE_DISPLAY}: IT'S OUT!"
            days_left = 0
        else:
            total_seconds = int(remaining)
            _weeks, _days, hours, _minutes, _seconds = split_remaining(total_seconds)
            days_left = total_seconds // 86400
            title = f"{days_left}d {hours}h · {TITLE_DISPLAY}"

        if self._last_shown.get("tray_title") != title:
            self._last_shown["tray_title"] = title
            try:
                self.tray_icon.title = title
            except Exception:
                pass   # not every tray backend supports live tooltip text

        # Redrawing the little digit picture is a bit more work than just
        # changing text, so we only do it when the NUMBER actually changes
        # (at most once a day) instead of on every tick.
        if self._last_shown.get("tray_days_badge") != days_left:
            self._last_shown["tray_days_badge"] = days_left
            try:
                self.tray_icon.icon = self._make_tray_image(days_left)
            except Exception:
                pass   # not every tray backend supports live icon swaps

    def _start_tray(self):
        """Put our icon next to the clock, with a right-click menu."""
        try:
            # A thin separator line before "Quit" is a small, modern touch —
            # it visually sets the one-way, exit-the-app action apart from
            # the safe "just open the window" one above it.
            menu = pystray.Menu(
                pystray.MenuItem("Open SKZ Countdown", self._tray_show,
                                 default=True),   # double-click = open
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit SKZ Countdown", self._tray_quit),
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
        self.settings["auto_open_at_release"] = bool(self.auto_open_var.get())
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

    # ---------- The member photo shuffle (every card stays lit up) ----------

    def _cycle_members(self):
        """Give any member with more than one photo a fresh random one —
        shuffled so the same picture never shows twice in a row. Members
        with only one photo (or none yet) just stay put. Borders always
        stay lit; only the picture inside ever changes.

        The WAIT before the next change is random too (see
        MEMBER_CYCLE_MIN_MS/MAX_MS), so photos change at random moments
        instead of on a predictable beat, and stick around a good while.
        """
        if not self.member_cards:
            return
        if self.state() != "withdrawn":   # don't bother while hidden
            for i in range(len(MEMBERS)):
                paths = self._member_photo_paths[i]
                if len(paths) < 2:
                    continue   # nothing to shuffle for this member yet
                choices = [j for j in range(len(paths))
                           if j != self._member_current[i]]
                self._member_current[i] = random.choice(choices)
                photo = self._member_photo(
                    i, self._member_current[i], self._member_thumb_size)
                self.member_photo_labels[i].configure(image=photo)
        next_wait = random.randint(MEMBER_CYCLE_MIN_MS, MEMBER_CYCLE_MAX_MS)
        self._member_job = self.after(next_wait, self._cycle_members)

    def _cycle_group(self):
        """Swap to a fresh random group photo — shuffled so the same
        picture never shows twice in a row. Only bothers if there's more
        than one, and only while the window is visible. The frame around
        it always stays lit up (and hugs whichever photo is showing).

        Like the members above, the wait before the next swap is random
        (see GROUP_CYCLE_MIN_MS/MAX_MS) instead of a fixed beat.
        """
        total = self._count_group_photos()
        if total > 1 and self.state() != "withdrawn":
            choices = [i for i in range(1, total + 1) if i != self._group_index]
            self._group_index = random.choice(choices)
            self.group_label.configure(
                image=self._group_photo(self._group_index, self._group_size))
        next_wait = random.randint(GROUP_CYCLE_MIN_MS, GROUP_CYCLE_MAX_MS)
        self._group_job = self.after(next_wait, self._cycle_group)

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

        # Cheap to redo every tick, and keeps the "Your local time" line
        # correct even if a daylight-saving change happens while this app
        # has been quietly running in the tray for a while.
        if not hidden:
            self._refresh_local_time_label()

        if remaining <= 0:
            # THE ALBUM IS OUT! Switch to party mode (but only once).
            if not self._celebrating:
                self._celebrating = True
                for name in self.unit_labels:
                    # Fix: these labels hold IMAGES (the seven-segment
                    # digits), not plain text, once PIL is available — so
                    # setting text="0" alone leaves the old digit picture
                    # sitting on top and the countdown looks frozen. Paint
                    # a real "0" glyph instead, the same way every other
                    # digit update does.
                    if PIL_AVAILABLE:
                        zero_img = self._number_image("0", DIGIT_W, DIGIT_H)
                        self.unit_labels[name].configure(image=zero_img, text="")
                    else:
                        self.unit_labels[name].configure(image=None, text="0")
                self.status_label.configure(
                    text=(f'🎉 "{TITLE_DISPLAY}" IS OUT — {FANDOM_NAME}, '
                          'go stream! 🎉'),
                    text_color=ACCENT, font=self._font_celebrate)

                # MAKE THE MOMENT ACTIONABLE: don't just SAY "go stream" —
                # put the button to actually do it right here, instead of
                # making someone scroll past it down to "GET THE ALBUM".
                self.stream_now_btn.grid(row=2, column=0, pady=(16, 0))

                # If they opted in (Settings → "auto-open at release"),
                # open the stream link for them, once, right now.
                if self.settings.get("auto_open_at_release", False):
                    self._open_stream_now()

            # POST-RELEASE MODE: once a full day has passed, swap the
            # one-time celebration line for a running "Day N since
            # release" counter, so the app stays alive and useful long
            # after the countdown itself hits zero — not a dead screen.
            days_since = int((-remaining) // 86400)
            if days_since >= 1 and self._last_shown.get("days_since") != days_since:
                self._last_shown["days_since"] = days_since
                self.status_label.configure(
                    text=f"Day {days_since} since release · {FANDOM_NAME}, go stream!",
                    text_color=self.FG_DIM, font=self._font_status)
        elif not hidden:
            # Split the leftover seconds into weeks/days/hours/min/sec.
            weeks, days, hours, minutes, seconds = split_remaining(int(remaining))

            # Only touch labels whose number actually changed.
            for name, val in (("WEEKS", weeks), ("DAYS", days),
                              ("HOURS", hours), ("MINUTES", minutes),
                              ("SECONDS", seconds)):
                if self._last_shown.get(name) != val:
                    self._last_shown[name] = val
                    text = str(val) if name == "WEEKS" else f"{val:02d}"
                    if PIL_AVAILABLE:
                        # Draw it as a flat, crisp seven-segment "LED" picture.
                        img = self._number_image(text, DIGIT_W, DIGIT_H)
                        self.unit_labels[name].configure(image=img, text="")
                    else:
                        self.unit_labels[name].configure(text=text)

            day_count = int(remaining) // 86400
            if self._last_shown.get("day_count") != day_count:
                self._last_shown["day_count"] = day_count
                self.status_label.configure(
                    text=f"{day_count} total days remaining",
                    text_color=self.FG_DIM, font=self._font_status)

        # Even when hidden, we still check whether it's time for an alert,
        # and still keep the tray icon's own tooltip/number fresh — those
        # are the one thing you CAN still see while the window is hidden.
        self._check_milestones(remaining)
        self._update_tray(remaining)

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
        crossed = milestones_crossed(remaining, fired, self.settings)
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
