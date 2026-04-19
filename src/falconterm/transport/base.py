"""Transport protocol and base implementation shared by SSH / Telnet / Serial."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable

DataCallback = Callable[[bytes], None]
DisconnectCallback = Callable[[BaseException | None], None]


class TransportError(RuntimeError):
    """Generic transport-layer error with human-readable message."""


class Transport(ABC):
    """Abstract transport: SSH/Telnet/Serial all present this interface."""

    def __init__(self) -> None:
        self._data_cbs: list[DataCallback] = []
        self._disc_cbs: list[DisconnectCallback] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = False

    # ---------- Public API ----------

    @abstractmethod
    async def connect(self) -> None:
        """Open the transport. Raises TransportError on failure."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close cleanly."""

    @abstractmethod
    async def send(self, data: bytes) -> None:
        """Send bytes toward the remote end."""

    async def resize(self, rows: int, cols: int) -> None:
        """Propagate a new terminal window size. Default = no-op."""

    # ---------- Callbacks ----------

    def on_data(self, cb: DataCallback) -> None:
        self._data_cbs.append(cb)

    def on_disconnect(self, cb: DisconnectCallback) -> None:
        self._disc_cbs.append(cb)

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ---------- Subclass helpers ----------

    def _emit_data(self, data: bytes) -> None:
        for cb in list(self._data_cbs):
            try:
                cb(data)
            except Exception:
                pass

    def _emit_disconnect(self, err: BaseException | None) -> None:
        self._connected = False
        for cb in list(self._disc_cbs):
            try:
                cb(err)
            except Exception:
                pass
