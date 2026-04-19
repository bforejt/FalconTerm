"""Telnet transport via telnetlib3 (async)."""

from __future__ import annotations

import asyncio
import logging

import telnetlib3

from falconterm.transport.base import Transport, TransportError

log = logging.getLogger(__name__)


class TelnetTransport(Transport):
    def __init__(self, host: str, port: int, encoding: str = "utf-8") -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._encoding = encoding
        self._reader: telnetlib3.TelnetReader | None = None
        self._writer: telnetlib3.TelnetWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await telnetlib3.open_connection(
                host=self._host,
                port=self._port,
                encoding=False,  # raw bytes — we want to feed pyte directly
                connect_minwait=0.1,
                connect_maxwait=0.5,
            )
        except OSError as e:
            raise TransportError(f"Telnet connection failed: {e}") from e
        self._connected = True
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        err: BaseException | None = None
        try:
            assert self._reader is not None
            while True:
                data = await self._reader.read(4096)
                if not data:
                    break
                if isinstance(data, str):
                    data = data.encode(self._encoding, errors="replace")
                self._emit_data(data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            err = e
        finally:
            self._connected = False
            self._emit_disconnect(err)

    async def send(self, data: bytes) -> None:
        if self._writer is None:
            return
        try:
            # telnetlib3 TelnetWriter accepts bytes or str depending on encoding mode.
            self._writer.write(data.decode(self._encoding, errors="replace"))
            await self._writer.drain()
        except Exception as e:
            log.warning("Telnet write failed: %s", e)

    async def disconnect(self) -> None:
        self._connected = False
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):
                pass
            self._reader_task = None
        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                pass
            self._writer = None
        self._reader = None
