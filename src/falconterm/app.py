"""Application bootstrap.

CRITICAL: qasync must install its event loop policy *before* any module
creates an asyncio loop. If asyncssh or telnetlib3 touch asyncio first, they
end up on the default loop and the Qt integration breaks silently.
Keep imports tight in this file.
"""

from __future__ import annotations

import asyncio
import signal
import sys

# qasync brings in Qt; do this before asyncio.get_event_loop().
import qasync
from PySide6.QtWidgets import QApplication


def run(argv: list[str]) -> int:
    """Start the Qt application under a qasync event loop."""
    app = QApplication(argv)
    app.setApplicationName("FalconTerm")
    app.setApplicationDisplayName("FalconTerm")
    app.setOrganizationName("FalconTerm")
    app.setOrganizationDomain("falconterm.app")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Graceful Ctrl+C handling on POSIX.
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, app.quit)

    # Lazy import so PySide6 is already set up.
    from falconterm.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    with loop:
        return loop.run_forever() or 0
