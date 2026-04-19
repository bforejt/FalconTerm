"""Qt key events → VT escape sequences / control bytes."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

ESC = b"\x1b"
CSI = ESC + b"["
SS3 = ESC + b"O"


# Plain cursor keys in "application cursor mode" vs "normal mode".
# The terminal toggles via DECCKM (mode ?1). We expose both sets and let
# the widget pick based on `screen.mode`.
_CURSOR_NORMAL = {
    Qt.Key.Key_Up: CSI + b"A",
    Qt.Key.Key_Down: CSI + b"B",
    Qt.Key.Key_Right: CSI + b"C",
    Qt.Key.Key_Left: CSI + b"D",
    Qt.Key.Key_Home: CSI + b"H",
    Qt.Key.Key_End: CSI + b"F",
}
_CURSOR_APP = {
    Qt.Key.Key_Up: SS3 + b"A",
    Qt.Key.Key_Down: SS3 + b"B",
    Qt.Key.Key_Right: SS3 + b"C",
    Qt.Key.Key_Left: SS3 + b"D",
    Qt.Key.Key_Home: SS3 + b"H",
    Qt.Key.Key_End: SS3 + b"F",
}

_OTHER_KEYS = {
    Qt.Key.Key_Backspace: b"\x7f",  # DEL — most Unix systems expect this
    Qt.Key.Key_Tab: b"\t",
    Qt.Key.Key_Backtab: CSI + b"Z",
    Qt.Key.Key_Return: b"\r",
    Qt.Key.Key_Enter: b"\r",
    Qt.Key.Key_Escape: ESC,
    Qt.Key.Key_Insert: CSI + b"2~",
    Qt.Key.Key_Delete: CSI + b"3~",
    Qt.Key.Key_PageUp: CSI + b"5~",
    Qt.Key.Key_PageDown: CSI + b"6~",
    Qt.Key.Key_F1: SS3 + b"P",
    Qt.Key.Key_F2: SS3 + b"Q",
    Qt.Key.Key_F3: SS3 + b"R",
    Qt.Key.Key_F4: SS3 + b"S",
    Qt.Key.Key_F5: CSI + b"15~",
    Qt.Key.Key_F6: CSI + b"17~",
    Qt.Key.Key_F7: CSI + b"18~",
    Qt.Key.Key_F8: CSI + b"19~",
    Qt.Key.Key_F9: CSI + b"20~",
    Qt.Key.Key_F10: CSI + b"21~",
    Qt.Key.Key_F11: CSI + b"23~",
    Qt.Key.Key_F12: CSI + b"24~",
}


def translate(event: QKeyEvent, *, cursor_app_mode: bool = False) -> bytes | None:
    """Return the bytes to send for a Qt key event, or None to let Qt handle it.

    The widget should call this from keyPressEvent and, if bytes are returned,
    forward them to the transport.
    """
    key = event.key()
    mods = event.modifiers()
    text = event.text()

    # Handle Ctrl+letter control codes (A..Z → 0x01..0x1A).
    if mods & Qt.KeyboardModifier.ControlModifier and not (mods & Qt.KeyboardModifier.AltModifier):
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return bytes([key - Qt.Key.Key_A + 1])
        # Special Ctrl combos
        special = {
            Qt.Key.Key_Space: b"\x00",
            Qt.Key.Key_Backslash: b"\x1c",
            Qt.Key.Key_BracketRight: b"\x1d",
            Qt.Key.Key_AsciiCircum: b"\x1e",
            Qt.Key.Key_Underscore: b"\x1f",
            Qt.Key.Key_Question: b"\x7f",
        }
        if key in special:
            return special[key]

    # Cursor keys
    cursor_map = _CURSOR_APP if cursor_app_mode else _CURSOR_NORMAL
    if key in cursor_map:
        seq = cursor_map[key]
        # Apply modifier escape-sequence numbers for Shift/Ctrl/Alt combos.
        # Format: ESC[1;<mod><final>  where mod = 1 + bitmask(shift=1, alt=2, ctrl=4)
        mod_code = _modifier_code(mods)
        if mod_code > 1 and seq.startswith(CSI):
            final = seq[-1:]
            return CSI + b"1;" + str(mod_code).encode() + final
        return seq

    # Other named keys
    if key in _OTHER_KEYS:
        seq = _OTHER_KEYS[key]
        if mods & Qt.KeyboardModifier.AltModifier:
            return ESC + seq
        return seq

    # Alt + printable → ESC + char (meta prefix)
    if mods & Qt.KeyboardModifier.AltModifier and text:
        return ESC + text.encode("utf-8", errors="replace")

    # Plain printable
    if text:
        return text.encode("utf-8", errors="replace")

    return None


def _modifier_code(mods: Qt.KeyboardModifier) -> int:
    code = 1
    if mods & Qt.KeyboardModifier.ShiftModifier:
        code += 1
    if mods & Qt.KeyboardModifier.AltModifier:
        code += 2
    if mods & Qt.KeyboardModifier.ControlModifier:
        code += 4
    return code
