"""Tab container for open session tabs."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QStackedWidget, QTabWidget, QVBoxLayout, QWidget

from falconterm.ui.session_tab import SessionTab


class TabArea(QWidget):
    """QTabWidget wrapper that shows an empty-state placeholder when no tabs."""

    current_tab_changed = Signal(object)  # SessionTab | None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._stack = QStackedWidget(self)

        self._tabs = QTabWidget(self)
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_current_changed)

        self._empty = QLabel(
            "No Active Sessions\n\nDouble-click a session in the sidebar,\nor press ⌘K for Quick Connect.",
            self,
        )
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #888;")

        self._stack.addWidget(self._empty)
        self._stack.addWidget(self._tabs)
        self._stack.setCurrentWidget(self._empty)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

    def add_tab(self, tab: SessionTab) -> int:
        idx = self._tabs.addTab(tab, tab.display_name())
        tab.title_changed.connect(lambda title, t=tab: self._update_tab_title(t, title))
        self._tabs.setCurrentIndex(idx)
        self._stack.setCurrentWidget(self._tabs)
        tab.start()
        tab.focus_terminal()
        return idx

    def _update_tab_title(self, tab: SessionTab, title: str) -> None:
        idx = self._tabs.indexOf(tab)
        if idx != -1:
            self._tabs.setTabText(idx, title or tab.display_name())

    def _close_tab(self, index: int) -> None:
        w = self._tabs.widget(index)
        if isinstance(w, SessionTab):
            from falconterm.utils.asyncio_bridge import spawn

            spawn(w.shutdown())
        self._tabs.removeTab(index)
        if self._tabs.count() == 0:
            self._stack.setCurrentWidget(self._empty)

    def next_tab(self) -> None:
        count = self._tabs.count()
        if count <= 1:
            return
        self._tabs.setCurrentIndex((self._tabs.currentIndex() + 1) % count)

    def previous_tab(self) -> None:
        count = self._tabs.count()
        if count <= 1:
            return
        self._tabs.setCurrentIndex((self._tabs.currentIndex() - 1) % count)

    def close_current(self) -> None:
        idx = self._tabs.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    def current(self) -> SessionTab | None:
        w = self._tabs.currentWidget()
        return w if isinstance(w, SessionTab) else None

    def _on_current_changed(self, _index: int) -> None:
        self.current_tab_changed.emit(self.current())
