"""New / Edit session dialog."""

from __future__ import annotations

import getpass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from falconterm.models.session import (
    Node,
    SerialConfig,
    SSHAuth,
    SSHConfig,
    TelnetConfig,
)
from falconterm.models.settings import AppSettings
from falconterm.services import keyring_svc
from falconterm.transport.serial import list_serial_ports
from falconterm.ui.dialogs.font_picker import FontPicker
from falconterm.utils.constants import DEFAULT_SSH_PORT, DEFAULT_TELNET_PORT


class SessionEditDialog(QDialog):
    """Edits a Session node in place. Pass a copy — only on accept do you commit."""

    def __init__(
        self,
        node: Node,
        settings: AppSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Session" if node.name else "New Session")
        self.resize(520, 560)
        self._node = node.model_copy(deep=True)
        self._settings = settings
        self._password_to_store: str | None = None

        # --- General tab ---
        self._name = QLineEdit(self._node.name, self)
        self._protocol = QComboBox(self)
        self._protocol.addItems(["ssh", "telnet", "serial"])
        self._protocol.setCurrentText(self._node.protocol or "ssh")
        self._protocol.currentIndexChanged.connect(self._on_protocol_change)

        gen_form = QFormLayout()
        gen_form.addRow("Name", self._name)
        gen_form.addRow("Protocol", self._protocol)

        general_tab = QWidget(self)
        gv = QVBoxLayout(general_tab)
        gv.addLayout(gen_form)
        gv.addStretch()

        # --- SSH tab ---
        self._ssh_host = QLineEdit((self._node.ssh.host if self._node.ssh else ""), self)
        self._ssh_port = QSpinBox(self)
        self._ssh_port.setRange(1, 65535)
        self._ssh_port.setValue(self._node.ssh.port if self._node.ssh else DEFAULT_SSH_PORT)
        self._ssh_user = QLineEdit(
            (self._node.ssh.username if self._node.ssh else getpass.getuser()), self
        )
        self._ssh_auth = QComboBox(self)
        self._ssh_auth.addItems(["agent", "key", "password"])
        if self._node.ssh:
            self._ssh_auth.setCurrentText(self._node.ssh.auth.method)
        self._ssh_auth.currentIndexChanged.connect(self._on_auth_change)
        key_row = QHBoxLayout()
        self._ssh_key = QLineEdit(self._node.ssh.auth.key_path if self._node.ssh else "", self)
        browse = QPushButton("Browse…", self)
        browse.clicked.connect(self._browse_key)
        key_row.addWidget(self._ssh_key, 1)
        key_row.addWidget(browse)
        self._ssh_password = QLineEdit(self)
        self._ssh_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._ssh_password.setPlaceholderText("(stored in keyring on save)")

        ssh_form = QFormLayout()
        ssh_form.addRow("Host", self._ssh_host)
        ssh_form.addRow("Port", self._ssh_port)
        ssh_form.addRow("Username", self._ssh_user)
        ssh_form.addRow("Auth", self._ssh_auth)
        ssh_form.addRow("Key path", key_row)
        ssh_form.addRow("Password", self._ssh_password)
        self._ssh_form = ssh_form
        ssh_tab = QWidget(self)
        ssh_tab.setLayout(ssh_form)

        # --- Telnet tab ---
        self._tel_host = QLineEdit(self._node.telnet.host if self._node.telnet else "", self)
        self._tel_port = QSpinBox(self)
        self._tel_port.setRange(1, 65535)
        self._tel_port.setValue(
            self._node.telnet.port if self._node.telnet else DEFAULT_TELNET_PORT
        )
        self._tel_user = QLineEdit(self._node.telnet.username if self._node.telnet else "", self)
        tel_form = QFormLayout()
        tel_form.addRow("Host", self._tel_host)
        tel_form.addRow("Port", self._tel_port)
        tel_form.addRow("Login (optional)", self._tel_user)
        tel_tab = QWidget(self)
        tel_tab.setLayout(tel_form)

        # --- Serial tab ---
        self._ser_port = QComboBox(self)
        for dev, desc in list_serial_ports():
            self._ser_port.addItem(f"{dev}  —  {desc}", userData=dev)
        if self._node.serial and self._node.serial.port:
            # Ensure current value shows even if not detected right now.
            self._ser_port.insertItem(0, self._node.serial.port, userData=self._node.serial.port)
            self._ser_port.setCurrentIndex(0)
        self._ser_baud = QComboBox(self)
        for b in ("9600", "19200", "38400", "57600", "115200", "230400"):
            self._ser_baud.addItem(b)
        if self._node.serial:
            self._ser_baud.setCurrentText(str(self._node.serial.baud))
        self._ser_data = QComboBox(self)
        for n in (5, 6, 7, 8):
            self._ser_data.addItem(str(n))
        self._ser_data.setCurrentText(str(self._node.serial.data_bits if self._node.serial else 8))
        self._ser_stop = QComboBox(self)
        for s in ("1", "1.5", "2"):
            self._ser_stop.addItem(s)
        self._ser_stop.setCurrentText(str(self._node.serial.stop_bits if self._node.serial else 1))
        self._ser_parity = QComboBox(self)
        for p in ("N", "E", "O", "M", "S"):
            self._ser_parity.addItem(p)
        self._ser_parity.setCurrentText(self._node.serial.parity if self._node.serial else "N")
        self._ser_flow = QComboBox(self)
        for f in ("none", "xonxoff", "rtscts", "dsrdtr"):
            self._ser_flow.addItem(f)
        self._ser_flow.setCurrentText(self._node.serial.flow if self._node.serial else "none")
        ser_form = QFormLayout()
        ser_form.addRow("Port", self._ser_port)
        ser_form.addRow("Baud", self._ser_baud)
        ser_form.addRow("Data bits", self._ser_data)
        ser_form.addRow("Stop bits", self._ser_stop)
        ser_form.addRow("Parity", self._ser_parity)
        ser_form.addRow("Flow control", self._ser_flow)
        ser_tab = QWidget(self)
        ser_tab.setLayout(ser_form)

        # --- Appearance tab ---
        font = self._node.overrides.resolve_font(settings.defaults)
        self._font_picker = FontPicker(
            font.family, font.size, on_change=lambda *_: self._mark_font_override()
        )
        self._scheme_combo = QComboBox(self)
        for scheme in settings.color_schemes:
            self._scheme_combo.addItem(scheme.name or scheme.id, userData=scheme.id)
        self._scheme_combo.setCurrentText(
            settings.scheme(self._node.overrides.resolve_scheme_id(settings.defaults)).name
        )
        self._rows = QSpinBox(self)
        self._rows.setRange(10, 500)
        self._rows.setValue(self._node.overrides.resolve_rows(settings.defaults))
        self._cols = QSpinBox(self)
        self._cols.setRange(20, 500)
        self._cols.setValue(self._node.overrides.resolve_cols(settings.defaults))
        self._scrollback = QSpinBox(self)
        self._scrollback.setRange(0, 1_000_000)
        self._scrollback.setValue(self._node.overrides.resolve_scrollback(settings.defaults))
        self._logging = QCheckBox("Enable session logging", self)
        self._logging.setChecked(self._node.overrides.resolve_logging(settings.defaults))

        app_form = QFormLayout()
        app_form.addRow("Font", self._font_picker)
        app_form.addRow("Color scheme", self._scheme_combo)
        app_form.addRow("Rows", self._rows)
        app_form.addRow("Cols", self._cols)
        app_form.addRow("Scrollback", self._scrollback)
        app_form.addRow("", self._logging)
        app_tab = QWidget(self)
        app_tab.setLayout(app_form)

        # --- Notes tab ---
        self._notes = QPlainTextEdit(self._node.notes, self)
        notes_tab = QWidget(self)
        nv = QVBoxLayout(notes_tab)
        nv.addWidget(self._notes)

        # --- Tab widget ---
        self._tabs = QTabWidget(self)
        self._tabs.addTab(general_tab, "General")
        self._tabs.addTab(ssh_tab, "SSH")
        self._tabs.addTab(tel_tab, "Telnet")
        self._tabs.addTab(ser_tab, "Serial")
        self._tabs.addTab(app_tab, "Appearance")
        self._tabs.addTab(notes_tab, "Notes")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(self._tabs)
        root.addWidget(buttons)

        self._on_protocol_change()
        self._on_auth_change()

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select private key", str(_home_ssh_dir()))
        if path:
            self._ssh_key.setText(path)

    def _on_protocol_change(self) -> None:
        proto = self._protocol.currentText()
        self._tabs.setTabEnabled(1, proto == "ssh")
        self._tabs.setTabEnabled(2, proto == "telnet")
        self._tabs.setTabEnabled(3, proto == "serial")

    def _on_auth_change(self) -> None:
        auth = self._ssh_auth.currentText()
        self._ssh_form.labelForField(self._ssh_key).setVisible(auth == "key")
        self._ssh_key.setVisible(auth == "key")
        self._ssh_form.labelForField(self._ssh_password).setVisible(auth == "password")
        self._ssh_password.setVisible(auth == "password")

    def _mark_font_override(self) -> None:
        # User edited font picker → override from defaults.
        pass  # We read from picker on save.

    def _accept(self) -> None:
        proto = self._protocol.currentText()
        self._node.name = self._name.text() or "(unnamed)"
        self._node.protocol = proto  # type: ignore[assignment]

        if proto == "ssh":
            auth_method = self._ssh_auth.currentText()
            # Handle password storage via keyring on save.
            keyring_ref = None
            if self._node.ssh and self._node.ssh.auth.method == "password":
                keyring_ref = self._node.ssh.auth.keyring_ref
            if auth_method == "password" and self._ssh_password.text():
                if keyring_ref is None:
                    keyring_ref = f"session:{self._node.id}"
                keyring_svc.store(keyring_ref, self._ssh_password.text())
            self._node.ssh = SSHConfig(
                host=self._ssh_host.text(),
                port=self._ssh_port.value(),
                username=self._ssh_user.text(),
                auth=SSHAuth(
                    method=auth_method,  # type: ignore[arg-type]
                    key_path=self._ssh_key.text() or None,
                    keyring_ref=keyring_ref if auth_method == "password" else None,
                ),
            )
            self._node.telnet = None
            self._node.serial = None
        elif proto == "telnet":
            self._node.telnet = TelnetConfig(
                host=self._tel_host.text(),
                port=self._tel_port.value(),
                username=self._tel_user.text(),
            )
            self._node.ssh = None
            self._node.serial = None
        else:  # serial
            self._node.serial = SerialConfig(
                port=self._ser_port.currentData() or self._ser_port.currentText(),
                baud=int(self._ser_baud.currentText()),
                data_bits=int(self._ser_data.currentText()),
                stop_bits=float(self._ser_stop.currentText()),
                parity=self._ser_parity.currentText(),  # type: ignore[arg-type]
                flow=self._ser_flow.currentText(),  # type: ignore[arg-type]
            )
            self._node.ssh = None
            self._node.telnet = None

        # Appearance — store as overrides.
        defaults = self._settings.defaults
        fam = self._font_picker.family()
        sz = self._font_picker.size()
        ov = self._node.overrides
        ov.font = (
            None
            if fam == defaults.font.family and sz == defaults.font.size
            else type(defaults.font)(family=fam, size=sz)
        )
        scheme_id = self._scheme_combo.currentData()
        ov.color_scheme_id = None if scheme_id == defaults.color_scheme_id else scheme_id
        ov.rows = None if self._rows.value() == defaults.rows else self._rows.value()
        ov.cols = None if self._cols.value() == defaults.cols else self._cols.value()
        ov.scrollback = (
            None if self._scrollback.value() == defaults.scrollback else self._scrollback.value()
        )
        ov.logging = (
            None if self._logging.isChecked() == defaults.logging else self._logging.isChecked()
        )
        self._node.overrides = ov

        self._node.notes = self._notes.toPlainText()
        self.accept()

    def result_node(self) -> Node:
        return self._node


def _home_ssh_dir() -> str:
    import os

    return os.path.expanduser("~/.ssh")
