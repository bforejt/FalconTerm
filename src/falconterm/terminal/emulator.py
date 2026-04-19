"""Wraps pyte.HistoryScreen + ByteStream with dirty-line tracking and feed throttling.

The rendering widget only cares about:
  - a snapshot of visible lines + cursor position
  - which lines changed since the last paint

pyte already maintains `screen.dirty`. We snapshot it on each feed and reset.
"""

from __future__ import annotations

from collections.abc import Callable

import pyte

from falconterm.utils.constants import DEFAULT_SCROLLBACK


class TerminalEmulator:
    """Owns the pyte screen + stream. Call `feed(data)` with raw bytes."""

    def __init__(
        self,
        cols: int = 80,
        rows: int = 24,
        scrollback: int = DEFAULT_SCROLLBACK,
        encoding: str = "utf-8",
    ) -> None:
        self._encoding = encoding
        # HistoryScreen provides top/bottom scrollback.
        self.screen: pyte.HistoryScreen = pyte.HistoryScreen(cols, rows, history=scrollback)
        self.screen.set_mode(pyte.modes.LNM)
        self.stream: pyte.ByteStream = pyte.ByteStream(self.screen)
        self._on_update: Callable[[], None] | None = None
        self._title: str = ""

    # ---------- Public API ----------

    def set_update_callback(self, cb: Callable[[], None]) -> None:
        self._on_update = cb

    def feed(self, data: bytes) -> None:
        if not data:
            return
        self.stream.feed(data)
        # pyte writes to screen.dirty; we don't clear here — the widget does,
        # after it repaints.
        if self._on_update is not None:
            self._on_update()

    def write_local(self, text: str) -> None:
        """Echo text into the screen locally (no transport). Useful for Phase-1 echo."""
        self.feed(text.encode(self._encoding, errors="replace"))

    def resize(self, rows: int, cols: int) -> None:
        self.screen.resize(rows, cols)

    @property
    def title(self) -> str:
        return self.screen.title if hasattr(self.screen, "title") else self._title

    def get_dirty(self) -> set[int]:
        """Return (and clear) the set of dirty line indices (relative to live screen)."""
        d = set(self.screen.dirty)
        self.screen.dirty.clear()
        return d

    def mark_all_dirty(self) -> None:
        for i in range(self.screen.lines):
            self.screen.dirty.add(i)
        if self._on_update is not None:
            self._on_update()

    # ---------- Scrollback helpers ----------

    def scroll_up(self, lines: int = 1) -> None:
        for _ in range(lines):
            self.screen.prev_page()
        self.mark_all_dirty()

    def scroll_down(self, lines: int = 1) -> None:
        for _ in range(lines):
            self.screen.next_page()
        self.mark_all_dirty()

    @property
    def history_size(self) -> int:
        """Total lines in scrollback (top buffer)."""
        return len(self.screen.history.top)

    def reset(self) -> None:
        self.screen.reset()
        self.mark_all_dirty()
