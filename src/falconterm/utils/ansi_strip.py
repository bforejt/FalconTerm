"""Strip ANSI control sequences from terminal output for clean log files."""

from __future__ import annotations

import re

# CSI (ESC [ ... letter), OSC (ESC ] ... BEL or ESC \), single-char escapes, etc.
# Order matters: multi-char forms (OSC, CSI) must come before the single-char fallback,
# since `]` is in the single-char C1 character class.
_ANSI_PATTERN = re.compile(
    r"""
    \x1B          # ESC
    (?:
        \[ [0-?]* [ -/]* [@-~]                # CSI: ESC [ params intermediates final
        |
        \] [^\x07\x1B]* (?: \x07 | \x1B\\ )   # OSC: ESC ] ... (BEL or ST)
        |
        [PX^_] [^\x1B]* \x1B\\                # DCS/SOS/PM/APC
        |
        [@-Z\\-_]                             # 7-bit C1 single-char fallback
    )
    """,
    re.VERBOSE,
)

# Other control bytes we don't want in logs (except \n, \r, \t)
_CTRL_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences and most control bytes. Keep \\n \\r \\t."""
    return _CTRL_PATTERN.sub("", _ANSI_PATTERN.sub("", text))
