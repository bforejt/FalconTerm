"""Session → Transport factory."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from falconterm.models.session import Node
from falconterm.services import keyring_svc
from falconterm.transport.base import Transport, TransportError
from falconterm.transport.serial import SerialTransport
from falconterm.transport.ssh import SSHTransport
from falconterm.transport.telnet import TelnetTransport

HostKeyPrompt = Callable[[str, str, str], Awaitable[bool]]


def build_transport(
    node: Node,
    password_override: str | None = None,
    known_hosts_prompt: HostKeyPrompt | None = None,
) -> Transport:
    if node.protocol == "ssh":
        if node.ssh is None:
            raise TransportError("Session has no SSH config")
        cfg = node.ssh
        password = password_override
        if password is None and cfg.auth.method == "password" and cfg.auth.keyring_ref:
            password = keyring_svc.fetch(cfg.auth.keyring_ref)
        return SSHTransport(
            host=cfg.host,
            port=cfg.port,
            username=cfg.username,
            password=password,
            key_path=cfg.auth.key_path if cfg.auth.method == "key" else None,
            use_agent=cfg.auth.method == "agent",
            known_hosts_prompt=known_hosts_prompt,
        )
    if node.protocol == "telnet":
        if node.telnet is None:
            raise TransportError("Session has no Telnet config")
        return TelnetTransport(host=node.telnet.host, port=node.telnet.port)
    if node.protocol == "serial":
        if node.serial is None:
            raise TransportError("Session has no Serial config")
        s = node.serial
        return SerialTransport(
            port=s.port,
            baud=s.baud,
            data_bits=s.data_bits,
            stop_bits=s.stop_bits,
            parity=s.parity,
            flow=s.flow,
        )
    raise TransportError(f"Unknown protocol: {node.protocol}")
