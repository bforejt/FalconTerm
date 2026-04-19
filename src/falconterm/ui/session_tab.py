"""One tab: TerminalWidget + transport + optional SessionLogger."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from falconterm.models.session import Node
from falconterm.models.settings import AppSettings
from falconterm.services.logging_svc import SessionLogger
from falconterm.terminal.widget import TerminalWidget
from falconterm.transport.base import Transport, TransportError
from falconterm.transport.factory import build_transport
from falconterm.utils.asyncio_bridge import spawn

log = logging.getLogger(__name__)

HostKeyPrompt = Callable[[str, str, str], Awaitable[bool]]


class SessionTab(QWidget):
    """One connected (or disconnected) session, hosting a TerminalWidget."""

    title_changed = Signal(str)
    closed = Signal()

    def __init__(
        self,
        node: Node,
        settings: AppSettings,
        password_override: str | None = None,
        known_hosts_prompt: HostKeyPrompt | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._node = node
        self._settings = settings
        self._password_override = password_override
        self._known_hosts_prompt = known_hosts_prompt
        self._transport: Transport | None = None
        self._logger: SessionLogger | None = None
        self._connected = False
        self._disconnect_reason = ""

        defaults = settings.defaults
        overrides = node.overrides
        font = overrides.resolve_font(defaults)
        scheme = settings.scheme(overrides.resolve_scheme_id(defaults))
        scrollback = overrides.resolve_scrollback(defaults)
        encoding = overrides.resolve_encoding(defaults)
        logging_on = overrides.resolve_logging(defaults)

        self._terminal = TerminalWidget(
            font_family=font.family,
            font_size=font.size,
            scheme=scheme,
            parent=self,
        )
        self._terminal.emulator.screen.resize(
            overrides.resolve_rows(defaults), overrides.resolve_cols(defaults)
        )
        self._terminal.send_bytes.connect(self._on_send)
        self._terminal.resized.connect(self._on_resize)
        self._encoding = encoding
        self._scrollback = scrollback

        self._status_label = QLabel("Connecting…", self)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._status_label.setStyleSheet(
            "QLabel { background: rgba(20,20,30,0.92); color: #f0f0f0; "
            "padding: 10px 14px; font-size: 12px; border-top: 1px solid #444; }"
        )
        self._status_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._terminal, 1)
        layout.addWidget(self._status_label)

        if logging_on:
            try:
                self._logger = SessionLogger(session_name=node.name or "session", encoding=encoding)
            except Exception as e:
                log.warning("Could not open session log: %s", e)

    # ---------- Lifecycle ----------

    def start(self) -> None:
        self._show_status("Connecting…")
        spawn(self._connect())

    async def _connect(self) -> None:
        try:
            self._transport = build_transport(
                self._node,
                password_override=self._password_override,
                known_hosts_prompt=self._known_hosts_prompt,
            )
            self._transport.on_data(self._on_data)
            self._transport.on_disconnect(self._on_disconnect)
            await self._transport.connect()
            # Initial size
            await self._transport.resize(self._terminal.rows, self._terminal.cols)
            self._connected = True
            self._hide_status()
        except TransportError as e:
            self._show_status(f"Connection failed: {e}")
        except Exception as e:
            self._show_status(f"Error: {e}")

    def reconnect(self) -> None:
        spawn(self._reconnect())

    async def _reconnect(self) -> None:
        await self._close_transport()
        self._terminal.emulator.reset()
        self._show_status("Reconnecting…")
        await self._connect()

    def disconnect(self) -> None:
        spawn(self._close_transport())

    async def _close_transport(self) -> None:
        if self._transport is not None:
            try:
                await self._transport.disconnect()
            except Exception:
                pass
            self._transport = None
        self._connected = False

    async def shutdown(self) -> None:
        await self._close_transport()
        if self._logger is not None:
            self._logger.close()
            self._logger = None

    # ---------- Transport <-> terminal ----------

    def _on_data(self, data: bytes) -> None:
        self._terminal.feed(data)
        if self._logger is not None:
            self._logger.write(data)

    def _on_disconnect(self, err: BaseException | None) -> None:
        self._connected = False
        msg = f"Disconnected ({err})" if err else "Disconnected. Press Enter to reconnect."
        self._show_status(msg)

    def _on_send(self, data: bytes) -> None:
        if self._transport is None or not self._connected:
            # Enter in a disconnected state → reconnect
            if data in (b"\r", b"\n", b"\r\n") and not self._connected:
                self.reconnect()
            return
        spawn(self._send_async(data))

    async def _send_async(self, data: bytes) -> None:
        try:
            assert self._transport is not None
            await self._transport.send(data)
        except Exception as e:
            log.warning("Send failed: %s", e)

    def _on_resize(self, rows: int, cols: int) -> None:
        if self._transport is not None and self._connected:
            spawn(self._transport.resize(rows, cols))

    # ---------- Status banner ----------

    def _show_status(self, text: str) -> None:
        self._status_label.setText(text)
        self._status_label.setVisible(True)

    def _hide_status(self) -> None:
        self._status_label.setVisible(False)

    @property
    def node(self) -> Node:
        return self._node

    @property
    def terminal(self) -> TerminalWidget:
        return self._terminal

    def display_name(self) -> str:
        return self._node.name or "session"

    def focus_terminal(self) -> None:
        self._terminal.setFocus(Qt.FocusReason.OtherFocusReason)
