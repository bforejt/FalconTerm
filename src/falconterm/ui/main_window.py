"""Main window: sidebar (session tree) + tab area."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
)

from falconterm.models.session import Node, new_folder
from falconterm.services import logging_svc
from falconterm.services.import_export import export_bundle, load_bundle
from falconterm.services.session_store import SessionStore
from falconterm.services.settings_store import SettingsStore
from falconterm.ui.dialogs.known_hosts import prompt_known_hosts
from falconterm.ui.dialogs.quick_connect import QuickConnectDialog
from falconterm.ui.dialogs.session_edit import SessionEditDialog
from falconterm.ui.dialogs.settings import SettingsDialog
from falconterm.ui.session_tab import SessionTab
from falconterm.ui.session_tree import SessionTreeView
from falconterm.ui.tab_area import TabArea
from falconterm.utils.constants import (
    APP_NAME,
    BUNDLE_EXTENSION,
    SIDEBAR_DEFAULT_WIDTH,
    SIDEBAR_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._settings_store = SettingsStore()
        self._session_store = SessionStore()

        # Prune old logs on launch.
        logging_svc.prune_old_logs(self._settings_store.settings.defaults.log_retention_days)

        self._sidebar = SessionTreeView(self._session_store, self)
        self._sidebar.connect_requested.connect(self._connect_saved)
        self._sidebar.edit_requested.connect(self._edit_node)
        self._sidebar.new_session_requested.connect(self._new_session)
        self._sidebar.new_folder_requested.connect(self._new_folder)
        self._sidebar.quick_connect_requested.connect(self._quick_connect)

        self._tabs = TabArea(self)

        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._tabs)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes(
            [
                self._settings_store.settings.ui.sidebar_width or SIDEBAR_DEFAULT_WIDTH,
                max(200, WINDOW_MIN_WIDTH - SIDEBAR_DEFAULT_WIDTH),
            ]
        )
        self._sidebar.setMinimumWidth(SIDEBAR_MIN_WIDTH)

        self.setCentralWidget(self._splitter)

        self.resize(
            max(WINDOW_MIN_WIDTH, self._settings_store.settings.ui.window_width),
            max(WINDOW_MIN_HEIGHT, self._settings_store.settings.ui.window_height),
        )

        self._build_menus()
        self._build_shortcuts()

    # ---------- Menus & shortcuts ----------

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        act_new_session = QAction("New Session…", self)
        act_new_session.setShortcut(QKeySequence.StandardKey.New)
        act_new_session.triggered.connect(self._new_session)
        file_menu.addAction(act_new_session)

        act_new_folder = QAction("New Folder…", self)
        act_new_folder.triggered.connect(self._new_folder)
        file_menu.addAction(act_new_folder)

        act_quick = QAction("Quick Connect…", self)
        act_quick.setShortcut(QKeySequence("Ctrl+K"))
        act_quick.triggered.connect(self._quick_connect)
        file_menu.addAction(act_quick)

        file_menu.addSeparator()

        act_close_tab = QAction("Close Tab", self)
        act_close_tab.setShortcut(QKeySequence.StandardKey.Close)
        act_close_tab.triggered.connect(self._tabs.close_current)
        file_menu.addAction(act_close_tab)

        file_menu.addSeparator()

        act_export = QAction("Export Sessions…", self)
        act_export.triggered.connect(self._export)
        file_menu.addAction(act_export)

        act_import = QAction("Import Sessions…", self)
        act_import.triggered.connect(self._import)
        file_menu.addAction(act_import)

        file_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Edit / Session
        sess_menu = menubar.addMenu("&Session")
        act_disc = QAction("Disconnect", self)
        act_disc.setShortcut(QKeySequence("Ctrl+D"))
        act_disc.triggered.connect(self._disconnect_current)
        sess_menu.addAction(act_disc)

        act_rec = QAction("Reconnect", self)
        act_rec.setShortcut(QKeySequence("Ctrl+R"))
        act_rec.triggered.connect(self._reconnect_current)
        sess_menu.addAction(act_rec)

        sess_menu.addSeparator()

        act_next = QAction("Next Tab", self)
        act_next.setShortcut(QKeySequence("Ctrl+Shift+]"))
        act_next.triggered.connect(self._tabs.next_tab)
        sess_menu.addAction(act_next)

        act_prev = QAction("Previous Tab", self)
        act_prev.setShortcut(QKeySequence("Ctrl+Shift+["))
        act_prev.triggered.connect(self._tabs.previous_tab)
        sess_menu.addAction(act_prev)

        # View
        view_menu = menubar.addMenu("&View")
        act_sidebar = QAction("Toggle Sidebar", self)
        act_sidebar.setShortcut(QKeySequence("Ctrl+0"))
        act_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(act_sidebar)

        act_logs = QAction("Open Log Folder", self)
        act_logs.setShortcut(QKeySequence("Ctrl+Shift+L"))
        act_logs.triggered.connect(self._open_logs)
        view_menu.addAction(act_logs)

        # Preferences (Qt puts this under the app menu on macOS automatically
        # when role=PreferencesRole)
        act_prefs = QAction("Settings…", self)
        act_prefs.setMenuRole(QAction.MenuRole.PreferencesRole)
        act_prefs.setShortcut(QKeySequence.StandardKey.Preferences)
        act_prefs.triggered.connect(self._open_settings)
        file_menu.addAction(act_prefs)

    def _build_shortcuts(self) -> None:
        # macOS-style Cmd+W is covered by Close shortcut above. Add fallbacks.
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self._quick_connect)

    # ---------- Actions ----------

    def _new_session(self) -> None:
        placeholder = Node(kind="session", name="New Session", protocol="ssh")
        dlg = SessionEditDialog(placeholder, self._settings_store.settings, self)
        if dlg.exec() == SessionEditDialog.DialogCode.Accepted:
            self._session_store.add(dlg.result_node())

    def _new_folder(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            self._session_store.add(new_folder(name.strip()))

    def _edit_node(self, node_id: str) -> None:
        node = self._session_store.get(node_id)
        if node is None:
            return
        if node.is_folder():
            from PySide6.QtWidgets import QInputDialog

            name, ok = QInputDialog.getText(self, "Rename Folder", "Folder name:", text=node.name)
            if ok and name.strip():
                node.name = name.strip()
                self._session_store.update(node)
            return
        dlg = SessionEditDialog(node, self._settings_store.settings, self)
        if dlg.exec() == SessionEditDialog.DialogCode.Accepted:
            self._session_store.update(dlg.result_node())

    def _connect_saved(self, node_id: str) -> None:
        node = self._session_store.get(node_id)
        if node is None or not node.is_session():
            return
        self._open_tab(node)

    def _quick_connect(self) -> None:
        dlg = QuickConnectDialog(self)
        if dlg.exec() == QuickConnectDialog.DialogCode.Accepted:
            node = dlg.result_node()
            if node is not None:
                self._open_tab(node, password_override=dlg.password())

    def _open_tab(self, node: Node, password_override: str | None = None) -> None:
        async def prompt_cb(host: str, key_type: str, fp: str) -> bool:
            return await prompt_known_hosts(host, key_type, fp, parent=self)

        tab = SessionTab(
            node=node,
            settings=self._settings_store.settings,
            password_override=password_override,
            known_hosts_prompt=prompt_cb,
            parent=self._tabs,
        )
        self._tabs.add_tab(tab)

    def _disconnect_current(self) -> None:
        tab = self._tabs.current()
        if tab is not None:
            tab.disconnect()

    def _reconnect_current(self) -> None:
        tab = self._tabs.current()
        if tab is not None:
            tab.reconnect()

    def _toggle_sidebar(self) -> None:
        if self._sidebar.isVisible():
            self._sidebar.hide()
        else:
            self._sidebar.show()

    def _open_logs(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logging_svc.open_logs_dir())))

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings_store, self)
        dlg.exec()

    # ---------- Import / export ----------

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sessions",
            f"falconterm-sessions{BUNDLE_EXTENSION}",
            f"FalconTerm bundle (*{BUNDLE_EXTENSION})",
        )
        if not path:
            return
        try:
            export_bundle(
                self._session_store.document,
                self._settings_store.settings.color_schemes,
                Path(path),
            )
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Sessions",
            "",
            f"FalconTerm bundle (*{BUNDLE_EXTENSION})",
        )
        if not path:
            return
        try:
            bundle = load_bundle(Path(path))
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))
            return

        resp = QMessageBox.question(
            self,
            "Import mode",
            "Replace all existing sessions? (No = merge into existing tree)",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._session_store.replace_all(bundle.nodes)
        elif resp == QMessageBox.StandardButton.No:
            self._session_store.merge(bundle.nodes)

        # Merge color schemes — keep existing by id, append new ones.
        have = {s.id for s in self._settings_store.settings.color_schemes}
        for s in bundle.color_schemes:
            if s.id not in have:
                self._settings_store.settings.color_schemes.append(s)
        self._settings_store.save()

    # ---------- Close ----------

    def closeEvent(self, event) -> None:
        # Persist window geometry.
        self._settings_store.settings.ui.window_width = self.width()
        self._settings_store.settings.ui.window_height = self.height()
        sizes = self._splitter.sizes()
        if sizes:
            self._settings_store.settings.ui.sidebar_width = sizes[0]
        self._settings_store.save()

        # Shutdown active tabs.
        from falconterm.utils.asyncio_bridge import spawn

        tab = self._tabs.current()
        while tab is not None:
            spawn(tab.shutdown())
            self._tabs.close_current()
            tab = self._tabs.current()

        super().closeEvent(event)
