"""Host-key-not-in-known-hosts prompt."""

from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


async def prompt_known_hosts(
    host: str, key_type: str, fingerprint: str, parent: QWidget | None = None
) -> bool:
    """Async wrapper — opens dialog and returns True/False."""
    # Qt modal dialogs block the event loop — we bridge via a Future.
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[bool] = loop.create_future()

    dlg = QDialog(parent)
    dlg.setWindowTitle("Unknown host key")
    dlg.setModal(True)

    label = QLabel(
        f"The host key for <b>{host}</b> is not in known_hosts.\nAccept and continue?",
        dlg,
    )
    label.setTextFormat(Qt.TextFormat.RichText)
    fp = QPlainTextEdit(dlg)
    fp.setReadOnly(True)
    fp.setPlainText(f"Key type: {key_type}\n\n{fingerprint}")
    fp.setMaximumHeight(120)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No,
        parent=dlg,
    )
    buttons.accepted.connect(lambda: (fut.set_result(True), dlg.accept()))
    buttons.rejected.connect(lambda: (fut.set_result(False), dlg.reject()))

    v = QVBoxLayout(dlg)
    v.addWidget(label)
    v.addWidget(fp)
    v.addWidget(buttons)

    dlg.show()
    try:
        return await fut
    finally:
        dlg.close()
