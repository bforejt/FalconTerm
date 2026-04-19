"""Glyph cache + color conversion for the terminal widget."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import pyte
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPixmap

from falconterm.models.settings import ColorScheme
from falconterm.utils.constants import GLYPH_CACHE_CAP


def qcolor_from_hex(hex_str: str) -> QColor:
    c = QColor(hex_str)
    if not c.isValid():
        return QColor("#ffffff")
    return c


@dataclass(frozen=True)
class GlyphKey:
    char: str
    fg_hex: str
    bg_hex: str
    bold: bool
    italic: bool
    underline: bool


class GlyphCache:
    """LRU cache of per-cell QPixmaps."""

    def __init__(self, font: QFont, cell_w: int, cell_h: int, cap: int = GLYPH_CACHE_CAP) -> None:
        self._font = font
        self._cell_w = cell_w
        self._cell_h = cell_h
        self._cap = cap
        self._cache: OrderedDict[GlyphKey, QPixmap] = OrderedDict()
        self._fm = QFontMetricsF(font)
        self._baseline_y = self._fm.ascent()

    def update_font(self, font: QFont, cell_w: int, cell_h: int) -> None:
        self._font = font
        self._cell_w = cell_w
        self._cell_h = cell_h
        self._fm = QFontMetricsF(font)
        self._baseline_y = self._fm.ascent()
        self._cache.clear()

    def get(self, key: GlyphKey) -> QPixmap:
        pm = self._cache.get(key)
        if pm is not None:
            self._cache.move_to_end(key)
            return pm
        pm = self._render(key)
        self._cache[key] = pm
        if len(self._cache) > self._cap:
            self._cache.popitem(last=False)
        return pm

    def _render(self, key: GlyphKey) -> QPixmap:
        pm = QPixmap(self._cell_w, self._cell_h)
        pm.fill(qcolor_from_hex(key.bg_hex))
        p = QPainter(pm)
        try:
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            font = QFont(self._font)
            if key.bold:
                font.setBold(True)
            if key.italic:
                font.setItalic(True)
            if key.underline:
                font.setUnderline(True)
            p.setFont(font)
            p.setPen(qcolor_from_hex(key.fg_hex))
            # Draw at baseline.
            p.drawText(0, int(self._baseline_y), key.char if key.char else " ")
        finally:
            p.end()
        return pm


# ---------- pyte color → hex ----------

# pyte emits color names (like "red", "brightblue") or hex codes (like "ff00ff")
# or numeric 256-color indexes ("11"). Convert into hex (without "#") using the
# active ColorScheme's ANSI palette.

_BASE_NAMES = {
    "black": 0,
    "red": 1,
    "green": 2,
    "brown": 3,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "brightblack": 8,
    "brightred": 9,
    "brightgreen": 10,
    "brightyellow": 11,
    "brightblue": 12,
    "brightmagenta": 13,
    "brightcyan": 14,
    "brightwhite": 15,
}


def resolve_color(value: str, scheme: ColorScheme, default_hex: str) -> str:
    """Map a pyte color value to a hex string (#RRGGBB)."""
    if value == "default":
        return default_hex
    # Named palette colors
    if value in _BASE_NAMES:
        return scheme.ansi[_BASE_NAMES[value]]
    # Numeric 256-color index
    try:
        idx = int(value)
    except ValueError:
        idx = -1
    if 0 <= idx < 16:
        return scheme.ansi[idx]
    if 16 <= idx < 232:
        # 6x6x6 cube
        idx -= 16
        r = (idx // 36) % 6
        g = (idx // 6) % 6
        b = idx % 6

        def s(v: int) -> int:
            return 0 if v == 0 else 55 + 40 * v

        return f"#{s(r):02x}{s(g):02x}{s(b):02x}"
    if 232 <= idx < 256:
        v = 8 + 10 * (idx - 232)
        return f"#{v:02x}{v:02x}{v:02x}"
    # Assume 6-digit hex string sans "#".
    if len(value) == 6 and all(c in "0123456789abcdefABCDEF" for c in value):
        return "#" + value.lower()
    return default_hex


def char_attrs(char: pyte.screens.Char, scheme: ColorScheme) -> tuple[str, str, bool, bool, bool]:
    """Return (fg_hex, bg_hex, bold, italic, underline) for a pyte Char cell."""
    fg = resolve_color(char.fg, scheme, scheme.fg)
    bg = resolve_color(char.bg, scheme, scheme.bg)
    if char.reverse:
        fg, bg = bg, fg
    return fg, bg, bool(char.bold), bool(char.italics), bool(char.underscore)
