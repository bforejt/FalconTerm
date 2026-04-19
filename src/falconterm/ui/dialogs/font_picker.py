"""Monospace-only font family + size picker with live preview."""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_MONO_DB_CACHE: list[str] | None = None


def _monospace_families() -> list[str]:
    global _MONO_DB_CACHE
    if _MONO_DB_CACHE is not None:
        return _MONO_DB_CACHE
    families = QFontDatabase.families()
    mono: list[str] = []
    for fam in families:
        if QFontDatabase.isFixedPitch(fam) or any(
            tok in fam.lower() for tok in ("mono", "courier", "menlo", "consolas")
        ):
            mono.append(fam)
    mono.sort()
    _MONO_DB_CACHE = mono
    return mono


class FontPicker(QWidget):
    """Composite widget: family combo + size spinner + preview."""

    def __init__(
        self,
        family: str,
        size: int,
        on_change: callable,  # type: ignore[valid-type]
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_change = on_change

        self._combo = QComboBox(self)
        for fam in _monospace_families():
            self._combo.addItem(fam)
        if family in _monospace_families():
            self._combo.setCurrentText(family)
        else:
            self._combo.insertItem(0, family)
            self._combo.setCurrentIndex(0)

        self._size = QSpinBox(self)
        self._size.setRange(8, 32)
        self._size.setValue(size)

        self._preview = QLabel("The quick brown fox jumps over the lazy dog", self)
        self._preview.setFrameShape(QLabel.Shape.Box)
        self._preview.setMinimumHeight(40)

        top = QHBoxLayout()
        top.addWidget(QLabel("Family:", self))
        top.addWidget(self._combo, 1)
        top.addSpacing(8)
        top.addWidget(QLabel("Size:", self))
        top.addWidget(self._size)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self._preview)

        self._combo.currentTextChanged.connect(self._emit_change)
        self._size.valueChanged.connect(self._emit_change)
        self._update_preview()

    def family(self) -> str:
        return self._combo.currentText()

    def size(self) -> int:
        return self._size.value()

    def _update_preview(self) -> None:
        f = QFont(self.family(), self.size())
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setFixedPitch(True)
        self._preview.setFont(f)

    def _emit_change(self, *_a: object) -> None:
        self._update_preview()
        self._on_change(self.family(), self.size())
