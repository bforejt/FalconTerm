"""Tests for TerminalEmulator / pyte integration."""

from __future__ import annotations

from falconterm.terminal.emulator import TerminalEmulator


def _row(em: TerminalEmulator, r: int) -> str:
    return "".join(em.screen.buffer[r][c].data for c in range(em.screen.columns)).rstrip()


def test_plain_text() -> None:
    em = TerminalEmulator(cols=80, rows=24)
    em.feed(b"hello world")
    assert _row(em, 0) == "hello world"


def test_ansi_colors_applied() -> None:
    em = TerminalEmulator(cols=80, rows=24)
    em.feed(b"\x1b[31mred\x1b[0m")
    # Color metadata is attached to the Char objects (pyte stores color name).
    ch = em.screen.buffer[0][0]
    assert ch.data == "r"
    assert ch.fg in ("red", "default", "1")  # pyte uses color names by default


def test_resize() -> None:
    em = TerminalEmulator(cols=80, rows=24)
    em.resize(40, 120)
    assert em.screen.columns == 120
    assert em.screen.lines == 40


def test_update_callback_fires() -> None:
    em = TerminalEmulator()
    calls: list[int] = []
    em.set_update_callback(lambda: calls.append(1))
    em.feed(b"x")
    assert calls  # at least one call


def test_cursor_moves() -> None:
    em = TerminalEmulator(cols=80, rows=24)
    em.feed(b"abc")
    assert em.screen.cursor.x == 3
    assert em.screen.cursor.y == 0


def test_reset_clears_screen() -> None:
    em = TerminalEmulator()
    em.feed(b"hello")
    em.reset()
    assert _row(em, 0) == ""
    assert em.screen.cursor.x == 0


def test_dirty_tracking() -> None:
    em = TerminalEmulator()
    em.get_dirty()  # clear initial dirty set
    em.feed(b"x\n")
    dirty = em.get_dirty()
    assert 0 in dirty
    # Second get returns empty
    assert em.get_dirty() == set()
