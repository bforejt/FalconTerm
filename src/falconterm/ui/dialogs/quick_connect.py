"""Quick Connect — transient one-off connection without saving."""

from __future__ import annotations

import getpass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from falconterm.models.session import (
    Node,
    SerialConfig,
    SSHAuth,
    SSHConfig,
    TelnetConfig,
    new_id,
)
from falconterm.transport.serial import list_serial_ports
from falconterm.utils.constants import DEFAULT_SSH_PORT, DEFAULT_TELNET_PORT


class QuickConnectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Quick Connect")
        self.resize(420, 240)
        self._result_node: Node | None = None
        self._password: str | None = None

        self._protocol = QComboBox(self)
        self._protocol.addItems(["SSH", "Telnet", "Serial"])
        self._protocol.currentIndexChanged.connect(self._on_protocol_change)

        self._host = QLineEdit(self)
        self._host.setPlaceholderText("hostname or IP")
        self._port = QSpinBox(self)
        self._port.setRange(1, 65535)
        self._port.setValue(DEFAULT_SSH_PORT)
        self._username = QLineEdit(getpass.getuser(), self)
        self._auth = QComboBox(self)
        self._auth.addItems(["Agent", "Key", "Password"])
        self._auth.currentIndexChanged.connect(self._on_auth_change)
        self._key_path = QLineEdit(self)
        self._key_path.setPlaceholderText("~/.ssh/id_ed25519")
        self._password_field = QLineEdit(self)
        self._password_field.setEchoMode(QLineEdit.EchoMode.Password)

        self._serial_port = QComboBox(self)
        for dev, desc in list_serial_ports():
            self._serial_port.addItem(f"{dev}  —  {desc}", userData=dev)
        if self._serial_port.count() == 0:
            self._serial_port.addItem("(no ports found)", userData="")
        self._baud = QComboBox(self)
        for b in ("9600", "19200", "38400", "57600", "115200"):
            self._baud.addItem(b)

        form = QFormLayout()
        form.addRow("Protocol", self._protocol)
        form.addRow("Host", self._host)
        form.addRow("Port", self._port)
        form.addRow("Username", self._username)
        form.addRow("Auth", self._auth)
        form.addRow("Key path", self._key_path)
        form.addRow("Password", self._password_field)
        form.addRow("Serial port", self._serial_port)
        form.addRow("Baud", self._baud)
        self._form = form

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._on_protocol_change()
        self._on_auth_change()

    def _on_protocol_change(self) -> None:
        proto = self._protocol.currentText().lower()
        is_ssh = proto == "ssh"
        is_telnet = proto == "telnet"
        is_serial = proto == "serial"
        self._form.labelForField(self._host).setVisible(not is_serial)
        self._host.setVisible(not is_serial)
        self._form.labelForField(self._port).setVisible(not is_serial)
        self._port.setVisible(not is_serial)
        self._form.labelForField(self._username).setVisible(not is_serial)
        self._username.setVisible(not is_serial)
        self._form.labelForField(self._auth).setVisible(is_ssh)
        self._auth.setVisible(is_ssh)
        self._form.labelForField(self._serial_port).setVisible(is_serial)
        self._serial_port.setVisible(is_serial)
        self._form.labelForField(self._baud).setVisible(is_serial)
        self._baud.setVisible(is_serial)
        if is_telnet:
            self._port.setValue(DEFAULT_TELNET_PORT)
        elif is_ssh:
            self._port.setValue(DEFAULT_SSH_PORT)
        self._on_auth_change()

    def _on_auth_change(self) -> None:
        proto = self._protocol.currentText().lower()
        auth_kind = self._auth.currentText().lower()
        key_visible = proto == "ssh" and auth_kind == "key"
        pw_visible = proto == "ssh" and auth_kind == "password"
        self._form.labelForField(self._key_path).setVisible(key_visible)
        self._key_path.setVisible(key_visible)
        self._form.labelForField(self._password_field).setVisible(pw_visible)
        self._password_field.setVisible(pw_visible)

    def _accept(self) -> None:
        proto = self._protocol.currentText().lower()
        if proto == "ssh":
            if not self._host.text().strip():
                return
            auth_kind = self._auth.currentText().lower()
            auth_method = {"agent": "agent", "key": "key", "password": "password"}[auth_kind]
            node = Node(
                id=new_id(),
                kind="session",
                name=f"{self._username.text()}@{self._host.text()}",
                protocol="ssh",
                ssh=SSHConfig(
                    host=self._host.text(),
                    port=self._port.value(),
                    username=self._username.text(),
                    auth=SSHAuth(
                        method=auth_method,
                        key_path=self._key_path.text() or None,
                    ),
                ),
            )
            self._password = self._password_field.text() or None
        elif proto == "telnet":
            if not self._host.text().strip():
                return
            node = Node(
                id=new_id(),
                kind="session",
                name=f"telnet://{self._host.text()}",
                protocol="telnet",
                telnet=TelnetConfig(
                    host=self._host.text(),
                    port=self._port.value(),
                    username=self._username.text(),
                ),
            )
        else:  # serial
            port = self._serial_port.currentData()
            if not port:
                return
            node = Node(
                id=new_id(),
                kind="session",
                name=f"serial://{port}",
                protocol="serial",
                serial=SerialConfig(port=port, baud=int(self._baud.currentText())),
            )
        self._result_node = node
        self.accept()

    def result_node(self) -> Node | None:
        return self._result_node

    def password(self) -> str | None:
        return self._password
