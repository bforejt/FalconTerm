"""Session tree model. Flat list of folder/session nodes with parent pointers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from falconterm.models.ids import new_id
from falconterm.models.settings import FontSpec, GlobalDefaults, Protocol
from falconterm.utils.constants import (
    CONFIG_VERSION,
    DEFAULT_SSH_PORT,
    DEFAULT_TELNET_PORT,
)

NodeKind = Literal["folder", "session"]
AuthMethod = Literal["password", "key", "agent"]


class SSHAuth(BaseModel):
    method: AuthMethod = "agent"
    key_path: str | None = None
    # Opaque reference into OS keyring (never contains the actual password).
    keyring_ref: str | None = None


class SSHConfig(BaseModel):
    host: str = ""
    port: int = DEFAULT_SSH_PORT
    username: str = ""
    auth: SSHAuth = Field(default_factory=SSHAuth)


class TelnetConfig(BaseModel):
    host: str = ""
    port: int = DEFAULT_TELNET_PORT
    username: str = ""  # Optional login, blank = no auto-login
    keyring_ref: str | None = None


class SerialConfig(BaseModel):
    port: str = ""  # e.g. /dev/tty.usbserial-XXXX or COM3
    baud: int = 9600
    data_bits: int = 8
    stop_bits: float = 1.0  # 1, 1.5, or 2
    parity: Literal["N", "E", "O", "M", "S"] = "N"
    flow: Literal["none", "xonxoff", "rtscts", "dsrdtr"] = "none"


class SessionOverrides(BaseModel):
    """Per-session overrides of GlobalDefaults. None means 'inherit'."""

    font: FontSpec | None = None
    color_scheme_id: str | None = None
    rows: int | None = None
    cols: int | None = None
    auto_fit_to_window: bool | None = None
    encoding: str | None = None
    scrollback: int | None = None
    logging: bool | None = None

    def resolve_font(self, defaults: GlobalDefaults) -> FontSpec:
        return self.font or defaults.font

    def resolve_scheme_id(self, defaults: GlobalDefaults) -> str:
        return self.color_scheme_id or defaults.color_scheme_id

    def resolve_rows(self, defaults: GlobalDefaults) -> int:
        return self.rows if self.rows is not None else defaults.rows

    def resolve_cols(self, defaults: GlobalDefaults) -> int:
        return self.cols if self.cols is not None else defaults.cols

    def resolve_auto_fit(self, defaults: GlobalDefaults) -> bool:
        return (
            self.auto_fit_to_window
            if self.auto_fit_to_window is not None
            else defaults.auto_fit_to_window
        )

    def resolve_encoding(self, defaults: GlobalDefaults) -> str:
        return self.encoding or defaults.encoding

    def resolve_scrollback(self, defaults: GlobalDefaults) -> int:
        return self.scrollback if self.scrollback is not None else defaults.scrollback

    def resolve_logging(self, defaults: GlobalDefaults) -> bool:
        return self.logging if self.logging is not None else defaults.logging


class Node(BaseModel):
    """A folder or session in the hierarchical tree."""

    id: str = Field(default_factory=new_id)
    kind: NodeKind
    parent: str | None = None
    name: str = ""
    order: int = 0

    # Session-only fields
    protocol: Protocol | None = None
    ssh: SSHConfig | None = None
    telnet: TelnetConfig | None = None
    serial: SerialConfig | None = None
    overrides: SessionOverrides = Field(default_factory=SessionOverrides)
    notes: str = ""

    def is_folder(self) -> bool:
        return self.kind == "folder"

    def is_session(self) -> bool:
        return self.kind == "session"


class SessionDocument(BaseModel):
    """Root document persisted to sessions.json."""

    version: int = CONFIG_VERSION
    nodes: list[Node] = Field(default_factory=list)


# ---------- Factory helpers ----------


def new_folder(name: str, parent: str | None = None) -> Node:
    return Node(kind="folder", name=name, parent=parent)


def new_ssh_session(name: str, host: str, username: str = "", parent: str | None = None) -> Node:
    return Node(
        kind="session",
        name=name or host,
        parent=parent,
        protocol="ssh",
        ssh=SSHConfig(host=host, username=username),
    )


def new_telnet_session(name: str, host: str, username: str = "", parent: str | None = None) -> Node:
    return Node(
        kind="session",
        name=name or host,
        parent=parent,
        protocol="telnet",
        telnet=TelnetConfig(host=host, username=username),
    )


def new_serial_session(name: str, port: str, baud: int = 9600, parent: str | None = None) -> Node:
    return Node(
        kind="session",
        name=name or port,
        parent=parent,
        protocol="serial",
        serial=SerialConfig(port=port, baud=baud),
    )
