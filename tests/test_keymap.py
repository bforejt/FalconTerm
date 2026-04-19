"""Tests for Qt key event → VT escape translation.

Skipped if Qt platform plugin can't load on the test host.
"""

from __future__ import annotations

import sys

import pytest

try:
    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtGui import QKeyEvent

    _app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    from falconterm.terminal.keymap import translate

    _QT_OK = True
except Exception:
    _QT_OK = False

pytestmark = pytest.mark.skipif(not _QT_OK, reason="Qt platform plugin unavailable")


def _ev(key, mods=Qt.KeyboardModifier.NoModifier, text=""):
    return QKeyEvent(QKeyEvent.Type.KeyPress, key, mods, text)


def test_plain_letter() -> None:
    assert translate(_ev(Qt.Key.Key_A, text="a")) == b"a"


def test_ctrl_letter() -> None:
    assert translate(_ev(Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)) == b"\x03"
    assert translate(_ev(Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)) == b"\x04"


def test_backspace_is_del() -> None:
    assert translate(_ev(Qt.Key.Key_Backspace)) == b"\x7f"


def test_enter() -> None:
    assert translate(_ev(Qt.Key.Key_Return)) == b"\r"


def test_cursor_normal_mode() -> None:
    assert translate(_ev(Qt.Key.Key_Up)) == b"\x1b[A"
    assert translate(_ev(Qt.Key.Key_Down)) == b"\x1b[B"
    assert translate(_ev(Qt.Key.Key_Right)) == b"\x1b[C"
    assert translate(_ev(Qt.Key.Key_Left)) == b"\x1b[D"


def test_cursor_application_mode() -> None:
    assert translate(_ev(Qt.Key.Key_Up), cursor_app_mode=True) == b"\x1bOA"
    assert translate(_ev(Qt.Key.Key_Right), cursor_app_mode=True) == b"\x1bOC"


def test_function_keys() -> None:
    assert translate(_ev(Qt.Key.Key_F1)) == b"\x1bOP"
    assert translate(_ev(Qt.Key.Key_F5)) == b"\x1b[15~"


def test_page_keys() -> None:
    assert translate(_ev(Qt.Key.Key_PageUp)) == b"\x1b[5~"
    assert translate(_ev(Qt.Key.Key_PageDown)) == b"\x1b[6~"


def test_modifier_arrow() -> None:
    # Shift+Up: ESC[1;2A
    out = translate(_ev(Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier))
    assert out == b"\x1b[1;2A"


def test_alt_letter_is_esc_prefix() -> None:
    out = translate(_ev(Qt.Key.Key_B, Qt.KeyboardModifier.AltModifier, text="b"))
    assert out == b"\x1bb"
