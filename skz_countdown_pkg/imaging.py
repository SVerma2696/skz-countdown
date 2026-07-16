"""
Drawing pictures with code instead of loading them from a file: the plain
stand-in pictures we show when a real photo is missing, and the flat,
blocky seven-segment "LED" digits the countdown numbers are made of. None
of these functions know about the window or any button — they just take
some numbers in and hand back a finished picture, which is why they can
live outside the main app class.
"""

from .config import PIL_AVAILABLE

if PIL_AVAILABLE:
    from PIL import Image, ImageDraw, ImageFont

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


def make_member_placeholder(name, size, border_color):
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
    # A thin neutral frame — red is saved for the active/important thing,
    # so a placeholder box doesn't get it.
    d.rectangle([1, 1, w - 2, h - 2], outline=border_color, width=2)
    # A tiny "add photo here" hint near the bottom.
    small = _load_font(max(9, int(w * 0.085)))
    hint = "photo →"
    tw = d.textlength(hint, font=small)
    d.text(((w - tw) / 2, h - int(h * 0.20)), hint, fill="#9a9aa2", font=small)
    return img


def make_group_placeholder(index, size, border_color):
    """Draw a simple wide 'group photo' stand-in."""
    w, h = size
    img = Image.new("RGB", (w, h), "#E4E4E8")
    d = ImageDraw.Draw(img)
    d.rectangle([1, 1, w - 2, h - 2], outline=border_color, width=2)
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


def make_logo_placeholder(label, color, size):
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


# ---------------- Drawing the seven-segment countdown digits ----------------
# Real digital clocks light up little bars to make each digit — this draws
# that same look ourselves, instead of just using a computer font.

# Which of the 7 bars (a=top, b=upper-right, c=lower-right, d=bottom,
# e=lower-left, f=upper-left, g=middle) are lit for each digit 0-9.
SEVEN_SEG = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg",
}

# We draw each digit this many times bigger than it's shown on screen,
# then let CTkImage shrink it back down. Windows often displays windows a
# little bigger than "actual size" (DPI scaling) — starting from a much
# bigger, crisp picture means that stretch always shrinks a picture down
# (sharp) instead of blowing a small one up (blurry).
SEG_SUPERSAMPLE = 4

# How big one digit is on screen. Bigger than a plain font would need,
# since a blocky LED digit needs some size to actually read clearly.
DIGIT_W = 78
DIGIT_H = 134


def _segment_bar(orientation, x0, y0, x1, y1, t):
    """One LED "bar": a hexagon with pointed ends, not a plain rectangle —
    this is the classic seven-segment-display shape (see any real digital
    clock), and it's what lets neighboring bars meet at a corner cleanly
    instead of their square corners visibly overlapping each other.

    orientation "h": the bar runs from (x0,y0) to (x1,y0) — y1 is unused.
    orientation "v": the bar runs from (x0,y0) to (x0,y1) — x1 is unused.
    t is the bar's full thickness.
    """
    ht = t / 2
    if orientation == "h":
        yc = y0
        return [
            (x0, yc), (x0 + ht, yc - ht), (x1 - ht, yc - ht),
            (x1, yc), (x1 - ht, yc + ht), (x0 + ht, yc + ht),
        ]
    xc = x0
    return [
        (xc, y0), (xc + ht, y0 + ht), (xc + ht, y1 - ht),
        (xc, y1), (xc - ht, y1 - ht), (xc - ht, y0 + ht),
    ]


def _move_toward(start, target, distance):
    """Nudge a point a little bit along the straight line from itself
    toward another point (but never more than halfway there, so short
    edges don't get walked right past their middle)."""
    sx, sy = start
    tx, ty = target
    dx, dy = tx - sx, ty - sy
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        return start
    step = min(distance / length, 0.5)
    return (sx + dx * step, sy + dy * step)


def _soften_corners(points, radius):
    """Turn every sharp corner of a shape into two corners close together
    instead of one — like snipping the tip off each pointy corner of a
    piece of paper. A real LED segment is molded plastic, so up close its
    corners are gently rounded, never a perfectly sharp mathematical point
    like a shape drawn in a vector program. Once this picture gets smoothed
    down to its small on-screen size (see SEG_SUPERSAMPLE), those tiny
    snipped corners read as soft and rounded instead of hard and computery
    — much closer to how a real seven-segment display actually looks.
    """
    count = len(points)
    softened = []
    for i in range(count):
        here = points[i]
        before = points[i - 1]
        after = points[(i + 1) % count]
        softened.append(_move_toward(here, before, radius))
        softened.append(_move_toward(here, after, radius))
    return softened


def _seven_segment_bars(w, h):
    """Work out the 7 bar polygons for one digit cell of size w×h — the
    same layout every digit shares, just colored differently per digit."""
    # Separate margins for each axis — the cell is much taller than it is
    # wide, so a margin based on width alone would leave almost no gap
    # above/below the digit.
    margin_x = max(3, int(w * 0.12))
    margin_y = max(3, int(h * 0.10))
    left, right = margin_x, w - margin_x
    top, bottom = margin_y, h - margin_y
    mid = (top + bottom) / 2
    t = max(4, int((right - left) * 0.42))   # how thick (wide) each bar is
    notch = t * 0.22   # just enough gap that corners don't overlap
    bars = {
        "a": _segment_bar("h", left + notch, top, right - notch, 0, t),
        "g": _segment_bar("h", left + notch, mid, right - notch, 0, t),
        "d": _segment_bar("h", left + notch, bottom, right - notch, 0, t),
        "f": _segment_bar("v", left, top + notch, 0, mid - notch, t),
        "b": _segment_bar("v", right, top + notch, 0, mid - notch, t),
        "e": _segment_bar("v", left, mid + notch, 0, bottom - notch, t),
        "c": _segment_bar("v", right, mid + notch, 0, bottom - notch, t),
    }
    # Round every corner a little, like a real LED segment's molded
    # plastic — see _soften_corners() for why.
    corner_radius = t * 0.09
    return {name: _soften_corners(points, corner_radius)
            for name, points in bars.items()}


def seven_segment_digit(digit, w, h, lit_color, off_color):
    """Draw one digit as a classic seven-segment "LED" glyph — flat, crisp
    bars, no blur or shadow, the same way a real LED display looks.

    Segments that are OFF are still drawn — as a dim tint of the SAME red
    as the lit ones (see SEG_OFF), the way a real LED display shows the
    rest of the "8" shape dimly powered-down rather than gone, so a "1"
    reads cleanly next to that ghost instead of a mismatched gray block
    cutting into the lit strokes.
    """
    bars = _seven_segment_bars(w, h)
    lit_names = set(SEVEN_SEG.get(digit, ""))

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for name, poly in bars.items():
        d.polygon(poly, fill=lit_color if name in lit_names else off_color)
    return img
