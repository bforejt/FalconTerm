"""Load / save the global AppSettings document."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from falconterm.models.settings import BUILTIN_SCHEME_IDS, BUILTIN_SCHEMES, AppSettings
from falconterm.services.paths import settings_file


class SettingsStore(QObject):
    changed = Signal()

    def __init__(self, path: Path | None = None) -> None:
        super().__init__()
        self._path = path or settings_file()
        self._settings = AppSettings()
        self.reload()

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def reload(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._settings = AppSettings.model_validate(data)
            except Exception:
                self._settings = AppSettings()
        # Ensure builtin schemes are always present.
        have = {s.id for s in self._settings.color_schemes}
        for bs in BUILTIN_SCHEMES:
            if bs.id not in have:
                self._settings.color_schemes.append(bs)
        self.changed.emit()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            self._settings.model_dump_json(indent=2, exclude_none=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)
        self.changed.emit()

    def update(self, new: AppSettings) -> None:
        self._settings = new
        self.save()

    def is_builtin_scheme(self, scheme_id: str) -> bool:
        return scheme_id in BUILTIN_SCHEME_IDS
