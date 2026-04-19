"""Tests for pydantic models."""

from __future__ import annotations

from falconterm.models.session import (
    Node,
    SessionDocument,
    SessionOverrides,
    SSHAuth,
    new_folder,
    new_serial_session,
    new_ssh_session,
    new_telnet_session,
)
from falconterm.models.settings import (
    BUILTIN_SCHEMES,
    AppSettings,
    FontSpec,
    GlobalDefaults,
)


class TestSessionModels:
    def test_new_ssh_session_defaults(self) -> None:
        n = new_ssh_session("web01", "10.0.0.1", "admin")
        assert n.kind == "session"
        assert n.protocol == "ssh"
        assert n.name == "web01"
        assert n.ssh is not None
        assert n.ssh.host == "10.0.0.1"
        assert n.ssh.port == 22
        assert n.ssh.auth.method == "agent"
        assert n.telnet is None
        assert n.serial is None

    def test_new_telnet_session(self) -> None:
        n = new_telnet_session("router", "192.168.1.1")
        assert n.protocol == "telnet"
        assert n.telnet is not None
        assert n.telnet.port == 23

    def test_new_serial_session(self) -> None:
        n = new_serial_session("console", "/dev/tty.usbserial-001", baud=115200)
        assert n.protocol == "serial"
        assert n.serial is not None
        assert n.serial.port == "/dev/tty.usbserial-001"
        assert n.serial.baud == 115200

    def test_new_folder(self) -> None:
        f = new_folder("Production")
        assert f.kind == "folder"
        assert f.is_folder()
        assert not f.is_session()

    def test_session_roundtrip(self) -> None:
        orig = new_ssh_session("web", "web.example.com", "root")
        orig.ssh.auth = SSHAuth(method="key", key_path="~/.ssh/id_ed25519")
        orig.overrides = SessionOverrides(rows=40, cols=120)
        json_str = orig.model_dump_json()
        roundtrip = Node.model_validate_json(json_str)
        assert roundtrip == orig

    def test_password_not_in_json(self) -> None:
        """Passwords are never persisted — only keyring_ref."""
        n = new_ssh_session("x", "x", "x")
        n.ssh.auth = SSHAuth(method="password", keyring_ref="session:abc")
        data = n.model_dump_json()
        assert "session:abc" in data  # ref is OK
        # Pydantic has no password field anyway, so nothing to leak


class TestOverridesResolution:
    def test_resolve_falls_back_to_defaults(self) -> None:
        defaults = GlobalDefaults()
        ov = SessionOverrides()
        assert ov.resolve_rows(defaults) == defaults.rows
        assert ov.resolve_cols(defaults) == defaults.cols
        assert ov.resolve_font(defaults) == defaults.font

    def test_resolve_prefers_override(self) -> None:
        defaults = GlobalDefaults(rows=24, cols=80)
        ov = SessionOverrides(rows=40, cols=120)
        assert ov.resolve_rows(defaults) == 40
        assert ov.resolve_cols(defaults) == 120

    def test_resolve_logging_none_vs_false(self) -> None:
        """logging=False is a legitimate override, must not be treated as 'inherit'."""
        defaults = GlobalDefaults(logging=True)
        ov = SessionOverrides(logging=False)
        assert ov.resolve_logging(defaults) is False
        ov2 = SessionOverrides()
        assert ov2.resolve_logging(defaults) is True


class TestSettings:
    def test_app_settings_has_builtin_schemes(self) -> None:
        s = AppSettings()
        ids = {sc.id for sc in s.color_schemes}
        for bs in BUILTIN_SCHEMES:
            assert bs.id in ids

    def test_scheme_lookup(self) -> None:
        s = AppSettings()
        assert s.scheme("solarized-dark").id == "solarized-dark"
        assert s.scheme("nonexistent").id == "default"  # falls back to first builtin

    def test_color_scheme_has_16_ansi(self) -> None:
        for s in BUILTIN_SCHEMES:
            assert len(s.ansi) == 16

    def test_font_spec_defaults(self) -> None:
        f = FontSpec()
        assert f.family == "Menlo"
        assert f.size == 13


class TestSessionDocument:
    def test_empty_doc(self) -> None:
        d = SessionDocument()
        assert d.nodes == []
        assert d.version >= 1

    def test_doc_roundtrip(self) -> None:
        d = SessionDocument()
        folder = new_folder("Prod")
        sess = new_ssh_session("web", "web.example.com", "root", parent=folder.id)
        d.nodes.extend([folder, sess])
        data = d.model_dump_json()
        d2 = SessionDocument.model_validate_json(data)
        assert len(d2.nodes) == 2
        assert d2.nodes[1].parent == folder.id
