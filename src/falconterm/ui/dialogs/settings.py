"""Global settings dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from falconterm.models.settings import FontSpec
from falconterm.services.settings_store import SettingsStore
from falconterm.ui.dialogs.color_editor import ColorSchemeEditor
from falconterm.ui.dialogs.font_picker import FontPicker


class SettingsDialog(QDialog):
    def __init__(self, store: SettingsStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(620, 520)
        self._store = store
        self._working = store.settings.model_copy(deep=True)

        tabs = QTabWidget(self)
        tabs.addTab(self._defaults_tab(), "Defaults")
        tabs.addTab(self._schemes_tab(), "Color Schemes")
        tabs.addTab(self._logs_tab(), "Logging")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(tabs)
        root.addWidget(buttons)

    # ---------- Tabs ----------

    def _defaults_tab(self) -> QWidget:
        w = QWidget(self)
        form = QFormLayout(w)
        self._font = FontPicker(
            self._working.defaults.font.family,
            self._working.defaults.font.size,
            on_change=self._font_changed,
        )
        self._scheme = QComboBox(w)
        for s in self._working.color_schemes:
            self._scheme.addItem(s.name or s.id, userData=s.id)
        self._scheme.setCurrentText(
            self._working.scheme(self._working.defaults.color_scheme_id).name
        )
        self._scheme.currentIndexChanged.connect(
            lambda _: self._set_default_scheme(self._scheme.currentData())
        )
        self._rows = QSpinBox(w)
        self._rows.setRange(10, 500)
        self._rows.setValue(self._working.defaults.rows)
        self._cols = QSpinBox(w)
        self._cols.setRange(20, 500)
        self._cols.setValue(self._working.defaults.cols)
        self._autofit = QCheckBox("Auto-fit terminal to window", w)
        self._autofit.setChecked(self._working.defaults.auto_fit_to_window)
        self._scrollback = QSpinBox(w)
        self._scrollback.setRange(0, 1_000_000)
        self._scrollback.setValue(self._working.defaults.scrollback)
        self._logging = QCheckBox("Enable session logging for new sessions", w)
        self._logging.setChecked(self._working.defaults.logging)

        form.addRow("Default font", self._font)
        form.addRow("Default color scheme", self._scheme)
        form.addRow("Rows", self._rows)
        form.addRow("Cols", self._cols)
        form.addRow("", self._autofit)
        form.addRow("Scrollback lines", self._scrollback)
        form.addRow("", self._logging)
        return w

    def _schemes_tab(self) -> QWidget:
        w = QWidget(self)
        v = QVBoxLayout(w)
        self._scheme_list = QComboBox(w)
        for s in self._working.color_schemes:
            self._scheme_list.addItem(s.name or s.id, userData=s.id)
        self._scheme_list.currentIndexChanged.connect(self._rebuild_scheme_editor)
        v.addWidget(self._scheme_list)
        self._scheme_editor_container = QWidget(w)
        self._scheme_editor_layout = QVBoxLayout(self._scheme_editor_container)
        self._scheme_editor_layout.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self._scheme_editor_container, 1)
        self._rebuild_scheme_editor()
        return w

    def _rebuild_scheme_editor(self) -> None:
        while self._scheme_editor_layout.count():
            item = self._scheme_editor_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.setParent(None)
        scheme_id = self._scheme_list.currentData()
        scheme = self._working.scheme(scheme_id)
        read_only = self._store.is_builtin_scheme(scheme_id)

        def on_change(new_scheme) -> None:
            for i, s in enumerate(self._working.color_schemes):
                if s.id == new_scheme.id:
                    self._working.color_schemes[i] = new_scheme
                    return

        editor = ColorSchemeEditor(scheme, read_only=read_only, on_change=on_change)
        self._scheme_editor_layout.addWidget(editor)

    def _logs_tab(self) -> QWidget:
        w = QWidget(self)
        form = QFormLayout(w)
        self._retention = QSpinBox(w)
        self._retention.setRange(0, 3650)
        self._retention.setValue(self._working.defaults.log_retention_days)
        open_folder = QPushButton("Open log folder", w)
        open_folder.clicked.connect(self._open_log_folder)
        form.addRow("Retention (days, 0 = forever)", self._retention)
        form.addRow("", open_folder)
        return w

    # ---------- Helpers ----------

    def _font_changed(self, family: str, size: int) -> None:
        self._working.defaults.font = FontSpec(family=family, size=size)

    def _set_default_scheme(self, scheme_id: str) -> None:
        self._working.defaults.color_scheme_id = scheme_id

    def _open_log_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from falconterm.services.paths import logs_dir

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir())))

    def _accept(self) -> None:
        self._working.defaults.rows = self._rows.value()
        self._working.defaults.cols = self._cols.value()
        self._working.defaults.auto_fit_to_window = self._autofit.isChecked()
        self._working.defaults.scrollback = self._scrollback.value()
        self._working.defaults.logging = self._logging.isChecked()
        self._working.defaults.log_retention_days = self._retention.value()
        self._store.update(self._working)
        self.accept()
