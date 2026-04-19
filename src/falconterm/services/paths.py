"""Cross-platform user-data / log paths via platformdirs."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_config_dir, user_log_dir

from falconterm.utils.constants import APP_NAME


def config_dir() -> Path:
    """User config dir. macOS: ~/Library/Application Support/FalconTerm/"""
    p = Path(user_config_dir(APP_NAME, appauthor=False))
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    """User log dir. macOS: ~/Library/Logs/FalconTerm/"""
    p = Path(user_log_dir(APP_NAME, appauthor=False))
    p.mkdir(parents=True, exist_ok=True)
    return p


def sessions_file() -> Path:
    return config_dir() / "sessions.json"


def settings_file() -> Path:
    return config_dir() / "settings.json"
