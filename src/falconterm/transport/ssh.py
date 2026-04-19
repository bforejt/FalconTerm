"""SSH transport implemented with asyncssh."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
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
        known_hosts = known_hosts_path if os.path.exists(known_hosts_path) else None
        agent_path: object = () if self._use_agent else None

        family = await self._pick_address_family(loop)

        log.info(
            "SSH connect: host=%r port=%d user=%r auth=%s key=%r known_hosts=%r family=%s",
            self._host,
            self._port,
            self._username,
            "agent" if self._use_agent else ("key" if self._key_path else "password"),
            self._key_path,
            known_hosts,
            _family_name(family),
        )

        try:
            self._conn = await asyncssh.connect(
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                client_keys=client_keys,
                agent_path=agent_path,
                known_hosts=known_hosts,
                family=family,
            )
        except asyncssh.HostKeyNotVerifiable as e:
            log.info("host key not in known_hosts for %s: %s", self._host, e)
            if self._known_hosts_prompt is None:
                raise TransportError(f"Host key for {self._host} is not in known_hosts") from e
            accept = await self._known_hosts_prompt(self._host, "ssh-ed25519", str(e))
            if not accept:
                raise TransportError("User rejected host key") from e
            log.info("user accepted host key; reconnecting with known_hosts=None")
            self._conn = await asyncssh.connect(
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                client_keys=client_keys,
                agent_path=agent_path,
                known_hosts=None,
                family=family,
            )
        except OSError as e:
            log.warning(
                "SSH OSError connecting to %s:%d — errno=%s: %s",
                self._host,
                self._port,
                getattr(e, "errno", "?"),
                e,
                exc_info=True,
            )
            raise TransportError(f"SSH connection failed: {e}") from e
        except asyncssh.Error as e:
            log.warning("asyncssh.Error: %s", e, exc_info=True)
            raise TransportError(f"SSH connection failed: {e}") from e

        log.info("SSH connected; requesting shell PTY (%dx%d)", self._cols, self._rows)
        try:
            self._chan, _session = await self._conn.create_session(
                _ShellSession,
                term_type=os.environ.get("TERM", "xterm-256color"),
                term_size=(self._cols, self._rows),
                request_pty="force",
            )
        except (OSError, asyncssh.Error) as e:
            log.warning("shell channel request failed: %s", e, exc_info=True)
            await self._close_conn()
            raise TransportError(f"Shell channel request failed: {e}") from e

        session = _session  # type: _ShellSession
        session.attach(self)
        self._connected = True
        log.info("SSH session ready for %s", self._host)

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

    async def _pick_address_family(self, loop: asyncio.AbstractEventLoop) -> int:
        """Return an address-family hint for asyncssh.connect.

        Workaround for a macOS / Python 3.13 bug: asyncio.create_connection
        calls ``setsockopt(TCP_NODELAY)`` on the socket *before* connect(),
        and that call returns ``EINVAL`` for link-local IPv6 sockets. Bonjour
        / mDNS ``.local`` hostnames commonly resolve to link-local v6.

        Strategy: resolve the host ourselves. If the address list contains
        any link-local IPv6 AND IPv4 is available, force AF_INET — the
        link-local entry is usually first in the list and asyncio won't fall
        through to a later v6 or v4 entry after setsockopt fails. Pure-v6
        hosts without v4 still go through AF_UNSPEC so global-v6 works.
        """
        try:
            infos = await loop.getaddrinfo(
                self._host, self._port, type=socket.SOCK_STREAM
            )
        except socket.gaierror:
            return socket.AF_UNSPEC  # let asyncssh report the DNS error

        has_v4 = any(f == socket.AF_INET for f, *_ in infos)
        has_linklocal_v6 = any(
            f == socket.AF_INET6 and len(sa) >= 4 and sa[3] != 0
            for f, _, _, _, sa in infos
        )

        if has_linklocal_v6 and has_v4:
            log.info(
                "resolved addresses include link-local IPv6; forcing AF_INET "
                "to avoid macOS / Py3.13 TCP_NODELAY EINVAL on link-local sockets"
            )
            return socket.AF_INET
        return socket.AF_UNSPEC


def _family_name(family: int) -> str:
    return {
        socket.AF_UNSPEC: "AF_UNSPEC",
        socket.AF_INET: "AF_INET (v4 only)",
        socket.AF_INET6: "AF_INET6 (v6 only)",
    }.get(family, str(family))


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
