"""Ring icons drawn with Pillow."""

from __future__ import annotations

from typing import Optional

from PIL import Image, ImageDraw

SIZE = 64      # drawn large; the OS scales down to tray size
SS = 4         # supersampling factor for smooth edges

GREEN = (74, 222, 128, 255)
YELLOW = (245, 180, 40, 255)
RED = (239, 68, 68, 255)
GREY = (150, 150, 150, 255)
TRACK = (128, 128, 128, 110)


def color_for(pct: Optional[int], stale: bool) -> tuple:
    if stale or pct is None:
        return GREY
    if pct >= 90:
        return RED
    if pct >= 70:
        return YELLOW
    return GREEN


def _ring(draw: ImageDraw.ImageDraw, inset: float, width: float, pct: Optional[int], color: tuple) -> None:
    s = SIZE * SS
    box = [inset * SS, inset * SS, s - inset * SS - 1, s - inset * SS - 1]
    w = max(1, int(width * SS))
    draw.ellipse(box, outline=TRACK, width=w)
    p = 0 if pct is None else max(0, min(100, pct))
    if p >= 100:
        draw.ellipse(box, outline=color, width=w)
    elif p > 0:
        draw.arc(box, start=-90, end=-90 + 360 * p / 100, fill=color, width=w)


def ring_icon(pct: Optional[int], stale: bool = False, ring: float = 12) -> Image.Image:
    """Single ring. `ring` = stroke width in px at SIZE=64."""
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    _ring(ImageDraw.Draw(img), 1, ring, pct, color_for(pct, stale))
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def combined_icon(session_pct: Optional[int], session_stale: bool,
                  weekly_pct: Optional[int], weekly_stale: bool) -> Image.Image:
    """Outer ring = weekly, inner ring = 5-hour session."""
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _ring(d, 1, 10, weekly_pct, color_for(weekly_pct, weekly_stale))
    _ring(d, 15, 10, session_pct, color_for(session_pct, session_stale))
    return img.resize((SIZE, SIZE), Image.LANCZOS)
