"""Serial transport via pyserial-asyncio."""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

import serial_asyncio

from falconterm.transport.base import Transport, TransportError

log = logging.getLogger(__name__)

Parity = Literal["N", "E", "O", "M", "S"]
FlowControl = Literal["none", "xonxoff", "rtscts", "dsrdtr"]


class SerialTransport(Transport):
    def __init__(
        self,
        port: str,
        baud: int = 9600,
        data_bits: int = 8,
        stop_bits: float = 1.0,
        parity: Parity = "N",
        flow: FlowControl = "none",
    ) -> None:
        super().__init__()
        self._port = port
        self._baud = baud
        self._data_bits = data_bits
        self._stop_bits = stop_bits
        self._parity = parity
        self._flow = flow
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._port,
                baudrate=self._baud,
                bytesize=self._data_bits,
                stopbits=self._stop_bits,
                parity=self._parity,
                xonxoff=self._flow == "xonxoff",
                rtscts=self._flow == "rtscts",
                dsrdtr=self._flow == "dsrdtr",
            )
        except Exception as e:
            raise TransportError(f"Serial open failed: {e}") from e
        self._connected = True
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        err: BaseException | None = None
        try:
            assert self._reader is not None
            while True:
                data = await self._reader.read(1024)
                if not data:
                    break
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
            self._writer.write(data)
            await self._writer.drain()
        except Exception as e:
            log.warning("Serial write failed: %s", e)

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


def list_serial_ports() -> list[tuple[str, str]]:
    """Returns [(device, description), ...] — for the serial port picker."""
    try:
        from serial.tools import list_ports

        return [(p.device, p.description or p.device) for p in list_ports.comports()]
    except Exception:
        return []
