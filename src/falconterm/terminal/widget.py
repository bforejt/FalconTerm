"""TerminalWidget — Qt widget that renders a pyte emulator with a glyph cache.

Data flow:
    Transport bytes  ->  emulator.feed()  ->  schedules repaint
    Qt paintEvent    ->  reads pyte screen + draws cached glyph pixmaps
    Qt keyPressEvent ->  keymap.translate() -> transport.send()
    Qt resizeEvent   ->  debounce -> emulator.resize() + transport.resize()
"""

from __future__ import annotations

import pyte
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import (
    QClipboard,
    QColor,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from falconterm.models.settings import ColorScheme
from falconterm.terminal.emulator import TerminalEmulator
from falconterm.terminal.keymap import translate
from falconterm.terminal.renderer import GlyphCache, GlyphKey, char_attrs, qcolor_from_hex
from falconterm.utils.constants import PAINT_FRAME_MS


class TerminalWidget(QWidget):
    """Cross-platform terminal widget driven by a pyte emulator."""

    # Emitted when bytes should be sent to the transport.
    send_bytes = Signal(bytes)
    # Emitted when the grid size changes (rows, cols).
    resized = Signal(int, int)
    # Emitted when the terminal title changes (OSC 0/2).
    title_changed = Signal(str)

    def __init__(
        self,
        emulator: TerminalEmulator | None = None,
        font_family: str = "Menlo",
        font_size: int = 13,
        scheme: ColorScheme | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)

        self._emulator = emulator or TerminalEmulator()
        self._emulator.set_update_callback(self._schedule_repaint)

        self._scheme = scheme or ColorScheme(id="default", name="Default")
        self._font = self._build_font(font_family, font_size)
        self._cell_w, self._cell_h = self._measure(self._font)
        self._glyphs = GlyphCache(self._font, self._cell_w, self._cell_h)

        # Selection state
        self._selecting = False
        self._sel_anchor: tuple[int, int] | None = None  # (col, row)
        self._sel_cursor: tuple[int, int] | None = None

        # Scrollback state (lines scrolled above the live screen).
        # pyte.HistoryScreen manages this via prev/next_page; we just read screen.
        self._scrolled_up = False

        # Debounced repaint timer.
        self._paint_timer = QTimer(self)
        self._paint_timer.setSingleShot(True)
        self._paint_timer.setInterval(PAINT_FRAME_MS)
        self._paint_timer.timeout.connect(self._do_repaint)

        # Debounced resize timer.
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._apply_grid_size)

        self.setMinimumSize(200, 120)

    # ---------- Public API ----------

    @property
    def emulator(self) -> TerminalEmulator:
        return self._emulator

    @property
    def rows(self) -> int:
        return self._emulator.screen.lines

    @property
    def cols(self) -> int:
        return self._emulator.screen.columns

    def feed(self, data: bytes) -> None:
        """Feed raw bytes from a transport."""
        self._emulator.feed(data)

    def apply_font(self, family: str, size: int) -> None:
        self._font = self._build_font(family, size)
        self._cell_w, self._cell_h = self._measure(self._font)
        self._glyphs.update_font(self._font, self._cell_w, self._cell_h)
        self._emulator.mark_all_dirty()
        self._apply_grid_size()

    def apply_scheme(self, scheme: ColorScheme) -> None:
        self._scheme = scheme
        self._glyphs.update_font(self._font, self._cell_w, self._cell_h)  # clears cache
        self._emulator.mark_all_dirty()
        self.update()

    # ---------- Font measurement ----------

    @staticmethod
    def _build_font(family: str, size: int) -> QFont:
        f = QFont(family, size)
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setFixedPitch(True)
        f.setKerning(False)
        return f

    @staticmethod
    def _measure(font: QFont) -> tuple[int, int]:
        fm = QFontMetricsF(font)
        # Use a wide char (M) to get consistent monospace width.
        advance = fm.horizontalAdvance("M")
        w = max(1, int(advance))
        h = max(1, int(fm.height()))
        return w, h

    # ---------- Events ----------

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._resize_timer.start()

    def _apply_grid_size(self) -> None:
        cols = max(1, self.width() // self._cell_w)
        rows = max(1, self.height() // self._cell_h)
        if cols == self._emulator.screen.columns and rows == self._emulator.screen.lines:
            return
        self._emulator.resize(rows, cols)
        self._emulator.mark_all_dirty()
        self.resized.emit(rows, cols)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        try:
            screen = self._emulator.screen
            # Clear background in exposed rect.
            bg = qcolor_from_hex(self._scheme.bg)
            painter.fillRect(event.rect(), bg)

            # Determine row range from exposed rect.
            exposed = event.rect()
            row_start = max(0, exposed.top() // self._cell_h)
            row_end = min(screen.lines - 1, exposed.bottom() // self._cell_h)

            for row in range(row_start, row_end + 1):
                line = screen.buffer[row]
                for col in range(screen.columns):
                    ch: pyte.screens.Char = line[col]
                    fg, bg_hex, bold, italic, underline = char_attrs(ch, self._scheme)
                    key = GlyphKey(
                        char=ch.data or " ",
                        fg_hex=fg,
                        bg_hex=bg_hex,
                        bold=bold,
                        italic=italic,
                        underline=underline,
                    )
                    pm = self._glyphs.get(key)
                    painter.drawPixmap(col * self._cell_w, row * self._cell_h, pm)

            # Draw cursor
            self._paint_cursor(painter)
            # Draw selection overlay
            self._paint_selection(painter)

            # Clear pyte's dirty set now that we've rendered.
            self._emulator.get_dirty()
        finally:
            painter.end()

    def _paint_cursor(self, p: QPainter) -> None:
        screen = self._emulator.screen
        if screen.cursor.hidden:
            return
        cx = screen.cursor.x * self._cell_w
        cy = screen.cursor.y * self._cell_h
        cursor_color = qcolor_from_hex(self._scheme.cursor)
        if self.hasFocus():
            p.fillRect(cx, cy, self._cell_w, self._cell_h, cursor_color)
            # Redraw the glyph on top in the bg color for contrast.
            try:
                ch: pyte.screens.Char = screen.buffer[screen.cursor.y][screen.cursor.x]
                fg_hex = self._scheme.bg
                bg_hex = self._scheme.cursor
                key = GlyphKey(
                    char=ch.data or " ",
                    fg_hex=fg_hex,
                    bg_hex=bg_hex,
                    bold=bool(ch.bold),
                    italic=bool(ch.italics),
                    underline=bool(ch.underscore),
                )
                p.drawPixmap(cx, cy, self._glyphs.get(key))
            except IndexError:
                pass
        else:
            # Hollow cursor when unfocused.
            p.setPen(cursor_color)
            p.drawRect(cx, cy, self._cell_w - 1, self._cell_h - 1)

    def _paint_selection(self, p: QPainter) -> None:
        if self._sel_anchor is None or self._sel_cursor is None:
            return
        a = self._sel_anchor
        b = self._sel_cursor
        if a == b:
            return
        start, end = (a, b) if (a[1], a[0]) <= (b[1], b[0]) else (b, a)
        color = QColor(qcolor_from_hex(self._scheme.fg))
        color.setAlpha(80)
        if start[1] == end[1]:
            x = start[0] * self._cell_w
            y = start[1] * self._cell_h
            w = (end[0] - start[0] + 1) * self._cell_w
            p.fillRect(x, y, w, self._cell_h, color)
            return
        # First line: from start col to end of row
        p.fillRect(
            start[0] * self._cell_w,
            start[1] * self._cell_h,
            self.width() - start[0] * self._cell_w,
            self._cell_h,
            color,
        )
        # Middle lines: full width
        for r in range(start[1] + 1, end[1]):
            p.fillRect(0, r * self._cell_h, self.width(), self._cell_h, color)
        # Last line: from col 0 to end col
        p.fillRect(
            0,
            end[1] * self._cell_h,
            (end[0] + 1) * self._cell_w,
            self._cell_h,
            color,
        )

    # ---------- Input ----------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Cmd/Ctrl+Shift+C — copy selection
        mods = event.modifiers()
        if (
            mods & Qt.KeyboardModifier.ControlModifier
            and mods & Qt.KeyboardModifier.ShiftModifier
            and event.key() == Qt.Key.Key_C
        ):
            self._copy_selection()
            return
        # Cmd/Ctrl+Shift+V — paste
        if (
            mods & Qt.KeyboardModifier.ControlModifier
            and mods & Qt.KeyboardModifier.ShiftModifier
            and event.key() == Qt.Key.Key_V
        ):
            self._paste_clipboard()
            return
        # macOS: Cmd+C/V (MetaModifier on Qt/macOS)
        if mods & Qt.KeyboardModifier.MetaModifier and event.key() == Qt.Key.Key_C:
            self._copy_selection()
            return
        if mods & Qt.KeyboardModifier.MetaModifier and event.key() == Qt.Key.Key_V:
            self._paste_clipboard()
            return

        cursor_app = (
            pyte.modes.DECAPP in self._emulator.screen.mode
            if hasattr(pyte.modes, "DECAPP")
            else False
        )
        # pyte uses DECCKM (?1) for application cursor mode; present in screen.mode as 1<<0 offset
        # Easier: use 1 in screen.mode? pyte stores as the private mode int.
        cursor_app = 1 in self._emulator.screen.mode

        seq = translate(event, cursor_app_mode=cursor_app)
        if seq is not None:
            self.send_bytes.emit(seq)
            # Auto-scroll to bottom on typing
            if self._scrolled_up:
                self._emulator.scroll_down(self._emulator.history_size)
                self._scrolled_up = False
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            cell = self._point_to_cell(event.position().toPoint())
            self._sel_anchor = cell
            self._sel_cursor = cell
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selecting:
            self._sel_cursor = self._point_to_cell(event.position().toPoint())
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        steps = max(1, abs(delta) // 120) * 3
        if delta > 0:
            self._emulator.scroll_up(steps)
            self._scrolled_up = True
        else:
            self._emulator.scroll_down(steps)
            # If we've exhausted history we may be back at live view
            # — HistoryScreen handles the flag internally.

    def focusInEvent(self, event: QEvent) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event: QEvent) -> None:
        super().focusOutEvent(event)
        self.update()

    # ---------- Helpers ----------

    def _point_to_cell(self, pt: QPoint) -> tuple[int, int]:
        col = max(0, min(self._emulator.screen.columns - 1, pt.x() // self._cell_w))
        row = max(0, min(self._emulator.screen.lines - 1, pt.y() // self._cell_h))
        return col, row

    def _selected_text(self) -> str:
        if self._sel_anchor is None or self._sel_cursor is None:
            return ""
        a, b = self._sel_anchor, self._sel_cursor
        if a == b:
            return ""
        start, end = (a, b) if (a[1], a[0]) <= (b[1], b[0]) else (b, a)
        screen = self._emulator.screen
        lines: list[str] = []
        for r in range(start[1], end[1] + 1):
            line = screen.buffer[r]
            if r == start[1] and r == end[1]:
                c0, c1 = start[0], end[0]
            elif r == start[1]:
                c0, c1 = start[0], screen.columns - 1
            elif r == end[1]:
                c0, c1 = 0, end[0]
            else:
                c0, c1 = 0, screen.columns - 1
            text = "".join(line[c].data or " " for c in range(c0, c1 + 1))
            lines.append(text.rstrip())
        return "\n".join(lines)

    def _copy_selection(self) -> None:
        text = self._selected_text()
        if text:
            from PySide6.QtWidgets import QApplication

            cb = QApplication.clipboard()
            cb.setText(text, QClipboard.Mode.Clipboard)

    def _paste_clipboard(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = QApplication.clipboard().text(QClipboard.Mode.Clipboard)
        if not text:
            return
        # Bracketed paste mode? pyte tracks mode 2004.
        if 2004 in self._emulator.screen.mode:
            self.send_bytes.emit(b"\x1b[200~" + text.encode("utf-8") + b"\x1b[201~")
        else:
            self.send_bytes.emit(text.encode("utf-8"))

    # ---------- Repaint scheduling ----------

    def _schedule_repaint(self) -> None:
        if not self._paint_timer.isActive():
            self._paint_timer.start()

    def _do_repaint(self) -> None:
        # Request a full paint — pyte's dirty tracking is read per paint anyway
        # and we already short-circuit via exposed rect.
        self.update()
