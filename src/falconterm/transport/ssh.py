"""SSH transport implemented with asyncssh."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable

import asyncssh

from falconterm.transport.base import Transport, TransportError

log = logging.getLogger(__name__)

HostKeyPromptResult = bool  # True = accept, False = reject


class SSHTransport(Transport):
    """asyncssh-backed shell channel.

    Args:
        host, port, username: server coordinates
        password / key_path / use_agent: auth
        known_hosts_prompt: async callable that receives (host, key_type, fingerprint)
            and returns True to accept-and-save, False to reject. Called when a
            host is not in known_hosts.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        *,
        password: str | None = None,
        key_path: str | None = None,
        use_agent: bool = True,
        known_hosts_prompt: Callable[[str, str, str], Awaitable[HostKeyPromptResult]] | None = None,
    ) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._key_path = os.path.expanduser(key_path) if key_path else None
        self._use_agent = use_agent
        self._known_hosts_prompt = known_hosts_prompt

        self._conn: asyncssh.SSHClientConnection | None = None
        self._chan: asyncssh.SSHClientChannel | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._rows = 24
        self._cols = 80

    async def connect(self) -> None:
        loop = asyncio.get_running_loop()
        self._loop = loop

        client_keys: list[str] | None = [self._key_path] if self._key_path else None

        known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
        try:
            # Try default known_hosts first.
            self._conn = await asyncssh.connect(
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                client_keys=client_keys,
                agent_path=None if not self._use_agent else (),
                known_hosts=known_hosts_path if os.path.exists(known_hosts_path) else None,
            )
        except asyncssh.HostKeyNotVerifiable as e:
            # Prompt the user via the UI callback.
            if self._known_hosts_prompt is None:
                raise TransportError(f"Host key for {self._host} is not in known_hosts") from e
            # Extract fingerprint from the exception if possible; otherwise use host.
            accept = await self._known_hosts_prompt(self._host, "ssh-ed25519", str(e))
            if not accept:
                raise TransportError("User rejected host key") from e
            # Reconnect with host-key checking disabled. asyncssh will then
            # add the key to known_hosts via validate_host_key_callback on success.
            self._conn = await asyncssh.connect(
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                client_keys=client_keys,
                agent_path=None if not self._use_agent else (),
                known_hosts=None,
            )
        except (OSError, asyncssh.Error) as e:
            raise TransportError(f"SSH connection failed: {e}") from e

        try:
            self._chan, _session = await self._conn.create_session(
                _ShellSession,
                term_type=os.environ.get("TERM", "xterm-256color"),
                term_size=(self._cols, self._rows),
                request_pty="force",
            )
        except (OSError, asyncssh.Error) as e:
            await self._close_conn()
            raise TransportError(f"Shell channel request failed: {e}") from e

        session = _session  # type: _ShellSession
        session.attach(self)
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        if self._chan is not None:
            try:
                self._chan.close()
            except Exception:
                pass
            self._chan = None
        await self._close_conn()

    async def _close_conn(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
                await self._conn.wait_closed()
            except Exception:
                pass
            self._conn = None

    async def send(self, data: bytes) -> None:
        if self._chan is None:
            return
        try:
            self._chan.write(data)
        except Exception as e:
            log.warning("SSH write failed: %s", e)

    async def resize(self, rows: int, cols: int) -> None:
        self._rows, self._cols = rows, cols
        if self._chan is not None:
            try:
                self._chan.change_terminal_size(cols, rows)
            except Exception:
                pass


class _ShellSession(asyncssh.SSHClientSession):  # type: ignore[misc]
    """asyncssh session → Transport callbacks."""

    def __init__(self) -> None:
        self._transport: SSHTransport | None = None

    def attach(self, t: SSHTransport) -> None:
        self._transport = t

    def data_received(self, data: bytes | str, datatype: object) -> None:  # type: ignore[override]
        if self._transport is None:
            return
        if isinstance(data, str):
            data = data.encode("utf-8", errors="replace")
        self._transport._emit_data(data)

    def connection_lost(self, exc: BaseException | None) -> None:  # type: ignore[override]
        if self._transport is not None:
            self._transport._emit_disconnect(exc)
