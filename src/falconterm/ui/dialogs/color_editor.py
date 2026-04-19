"""Color scheme editor with live preview."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from falconterm.models.settings import ColorScheme

_ANSI_NAMES = [
    "Black",
    "Red",
    "Green",
    "Yellow",
    "Blue",
    "Magenta",
    "Cyan",
    "White",
    "Bright Black",
    "Bright Red",
    "Bright Green",
    "Bright Yellow",
    "Bright Blue",
    "Bright Magenta",
    "Bright Cyan",
    "Bright White",
]


class ColorSwatch(QPushButton):
    """Clickable color swatch that opens a QColorDialog."""

    def __init__(self, hex_value: str, on_change: callable, parent: QWidget | None = None) -> None:  # type: ignore[valid-type]
        super().__init__(parent)
        self.setFixedSize(40, 24)
        self._on_change = on_change
        self._hex = hex_value
        self._apply_style()
        self.clicked.connect(self._pick)

    def value(self) -> str:
        return self._hex

    def set_value(self, hex_value: str) -> None:
        self._hex = hex_value
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(f"QPushButton {{ background: {self._hex}; border: 1px solid #888; }}")

    def _pick(self) -> None:
        c = QColorDialog.getColor(QColor(self._hex), self, "Choose color")
        if c.isValid():
            self._hex = c.name()
            self._apply_style()
            self._on_change(self._hex)


class ColorSchemeEditor(QWidget):
    def __init__(
        self,
        scheme: ColorScheme,
        read_only: bool = False,
        on_change: callable | None = None,  # type: ignore[valid-type]
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._scheme = scheme.model_copy(deep=True)
        self._on_change = on_change
        self._read_only = read_only

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)

        grid.addWidget(QLabel("Foreground"), 0, 0)
        self._fg = ColorSwatch(self._scheme.fg, self._update_fg)
        grid.addWidget(self._fg, 0, 1)

        grid.addWidget(QLabel("Background"), 1, 0)
        self._bg = ColorSwatch(self._scheme.bg, self._update_bg)
        grid.addWidget(self._bg, 1, 1)

        grid.addWidget(QLabel("Cursor"), 2, 0)
        self._cursor = ColorSwatch(self._scheme.cursor, self._update_cursor)
        grid.addWidget(self._cursor, 2, 1)

        self._ansi_swatches: list[ColorSwatch] = []
        ansi_grid = QGridLayout()
        for i, hex_v in enumerate(self._scheme.ansi):
            row = i // 4
            col = i % 4
            lab = QLabel(_ANSI_NAMES[i])
            lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ansi_grid.addWidget(lab, row, col * 2)
            sw = ColorSwatch(hex_v, lambda h, idx=i: self._update_ansi(idx, h))
            ansi_grid.addWidget(sw, row, col * 2 + 1)
            self._ansi_swatches.append(sw)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addWidget(QLabel("ANSI palette:"))
        layout.addLayout(ansi_grid)

        if read_only:
            self.setEnabled(False)

    def scheme(self) -> ColorScheme:
        return self._scheme

    def _update_fg(self, hex_v: str) -> None:
        self._scheme.fg = hex_v
        self._notify()

    def _update_bg(self, hex_v: str) -> None:
        self._scheme.bg = hex_v
        self._notify()

    def _update_cursor(self, hex_v: str) -> None:
        self._scheme.cursor = hex_v
        self._notify()

    def _update_ansi(self, index: int, hex_v: str) -> None:
        self._scheme.ansi[index] = hex_v
        self._notify()

    def _notify(self) -> None:
        if self._on_change is not None:
            self._on_change(self._scheme)
