"""QTreeView + QStandardItemModel over SessionStore."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from falconterm.models.session import Node
from falconterm.services.session_store import SessionStore

ROLE_NODE_ID = Qt.ItemDataRole.UserRole + 1


class SessionTreeView(QWidget):
    """Sidebar widget: search field + tree + footer buttons."""

    connect_requested = Signal(str)  # node_id
    edit_requested = Signal(str)
    new_session_requested = Signal()
    new_folder_requested = Signal()
    quick_connect_requested = Signal()

    def __init__(self, store: SessionStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Filter sessions…")
        self._search.textChanged.connect(self._apply_filter)

        self._tree = QTreeView(self)
        self._tree.setHeaderHidden(True)
        self._tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.doubleClicked.connect(self._on_double_click)
        self._tree.setDragDropMode(QTreeView.DragDropMode.InternalMove)

        self._model = QStandardItemModel(self)
        self._tree.setModel(self._model)

        self._btn_new_session = QPushButton("+ Session", self)
        self._btn_new_folder = QPushButton("+ Folder", self)
        self._btn_quick = QPushButton("⚡ Quick", self)
        self._btn_new_session.clicked.connect(self.new_session_requested.emit)
        self._btn_new_folder.clicked.connect(self.new_folder_requested.emit)
        self._btn_quick.clicked.connect(self.quick_connect_requested.emit)

        footer = QHBoxLayout()
        footer.setContentsMargins(4, 2, 4, 2)
        footer.addWidget(self._btn_new_session)
        footer.addWidget(self._btn_new_folder)
        footer.addWidget(self._btn_quick)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self._search)
        layout.addWidget(self._tree, 1)
        layout.addLayout(footer)

        self._store.changed.connect(self.rebuild)
        self.rebuild()

    def selected_node_id(self) -> str | None:
        idx = self._tree.currentIndex()
        if not idx.isValid():
            return None
        item = self._model.itemFromIndex(idx)
        if item is None:
            return None
        return item.data(ROLE_NODE_ID)

    # ---------- Rebuild ----------

    def rebuild(self) -> None:
        self._model.clear()
        root = self._model.invisibleRootItem()
        self._populate(root, parent_id=None)
        self._tree.expandAll()
        self._apply_filter(self._search.text())

    def _populate(self, parent_item: QStandardItem, parent_id: str | None) -> None:
        for node in self._store.children(parent_id):
            item = QStandardItem(self._render_label(node))
            item.setData(node.id, ROLE_NODE_ID)
            item.setEditable(False)
            parent_item.appendRow(item)
            if node.is_folder():
                self._populate(item, node.id)

    @staticmethod
    def _render_label(node: Node) -> str:
        if node.is_folder():
            return node.name or "(folder)"
        # session
        suffix = ""
        if node.protocol == "ssh" and node.ssh:
            suffix = f"  {node.ssh.username}@{node.ssh.host}"
        elif node.protocol == "telnet" and node.telnet:
            suffix = f"  telnet://{node.telnet.host}:{node.telnet.port}"
        elif node.protocol == "serial" and node.serial:
            suffix = f"  {node.serial.port} @ {node.serial.baud}"
        return f"{node.name}{suffix}"

    # ---------- Filter ----------

    def _apply_filter(self, text: str) -> None:
        q = text.strip().lower()
        if not q:
            self._set_all_visible(self._model.invisibleRootItem(), True)
            return
        self._filter_recursive(self._model.invisibleRootItem(), q)

    def _filter_recursive(self, parent: QStandardItem, query: str) -> bool:
        any_visible = False
        for row in range(parent.rowCount()):
            child = parent.child(row)
            node_id = child.data(ROLE_NODE_ID)
            node = self._store.get(node_id)
            if node is None:
                continue
            child_visible = False
            if node.is_session():
                label = self._render_label(node).lower()
                child_visible = query in label or query in node.name.lower()
            else:
                # Folder visible if any descendant matches.
                child_visible = self._filter_recursive(child, query)
            self._tree.setRowHidden(row, parent.index(), not child_visible)
            any_visible = any_visible or child_visible
        return any_visible

    def _set_all_visible(self, parent: QStandardItem, visible: bool) -> None:
        for row in range(parent.rowCount()):
            self._tree.setRowHidden(row, parent.index(), not visible)
            child = parent.child(row)
            if child is not None:
                self._set_all_visible(child, visible)

    # ---------- Interaction ----------

    def _on_double_click(self, index) -> None:
        item = self._model.itemFromIndex(index)
        if item is None:
            return
        node_id = item.data(ROLE_NODE_ID)
        node = self._store.get(node_id)
        if node is None:
            return
        if node.is_session():
            self.connect_requested.emit(node_id)

    def _show_context_menu(self, pos) -> None:
        idx = self._tree.indexAt(pos)
        menu = QMenu(self)
        node_id = None
        node: Node | None = None
        if idx.isValid():
            item = self._model.itemFromIndex(idx)
            if item is not None:
                node_id = item.data(ROLE_NODE_ID)
                node = self._store.get(node_id)

        if node is not None:
            if node.is_session():
                act_connect = QAction("Connect", self)
                act_connect.triggered.connect(lambda: self.connect_requested.emit(node_id))
                menu.addAction(act_connect)
                menu.addSeparator()
                act_edit = QAction("Edit…", self)
                act_edit.triggered.connect(lambda: self.edit_requested.emit(node_id))
                menu.addAction(act_edit)
                act_dup = QAction("Duplicate", self)
                act_dup.triggered.connect(lambda: self._store.duplicate(node_id))
                menu.addAction(act_dup)
            else:
                act_edit = QAction("Rename…", self)
                act_edit.triggered.connect(lambda: self.edit_requested.emit(node_id))
                menu.addAction(act_edit)
            menu.addSeparator()
            act_del = QAction("Delete", self)
            act_del.triggered.connect(self._confirm_delete)
            menu.addAction(act_del)
            menu.addSeparator()

        act_new_s = QAction("New Session…", self)
        act_new_s.triggered.connect(self.new_session_requested.emit)
        menu.addAction(act_new_s)
        act_new_f = QAction("New Folder…", self)
        act_new_f.triggered.connect(self.new_folder_requested.emit)
        menu.addAction(act_new_f)

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _confirm_delete(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        node_id = self.selected_node_id()
        if node_id is None:
            return
        node = self._store.get(node_id)
        if node is None:
            return
        kind = "folder and all its contents" if node.is_folder() else "session"
        resp = QMessageBox.question(
            self,
            "Delete?",
            f"Delete {kind} “{node.name}”?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._store.delete(node_id)
