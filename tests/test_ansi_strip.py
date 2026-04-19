"""Tests for ANSI escape sequence stripping."""

from __future__ import annotations

from falconterm.utils.ansi_strip import strip_ansi


def test_strip_csi() -> None:
    assert strip_ansi("\x1b[31mred\x1b[0m") == "red"


def test_strip_multiple_csi() -> None:
    assert strip_ansi("\x1b[1;32mbold green\x1b[0m normal") == "bold green normal"


def test_strip_osc() -> None:
    # OSC 0 ; title BEL
    assert strip_ansi("\x1b]0;my title\x07after") == "after"


def test_preserves_newlines_and_tabs() -> None:
    assert strip_ansi("a\nb\tc\r\nd") == "a\nb\tc\r\nd"


def test_removes_other_control_bytes() -> None:
    assert strip_ansi("a\x01b\x02c") == "abc"


def test_empty() -> None:
    assert strip_ansi("") == ""


def test_no_escape_passthrough() -> None:
    assert strip_ansi("plain text 123") == "plain text 123"


def test_complex_sequence() -> None:
    s = "hello \x1b[1;31;4mBOLD RED UNDERLINE\x1b[0m back"
    assert strip_ansi(s) == "hello BOLD RED UNDERLINE back"
