"""Password storage via OS keyring, with graceful fallback on headless Linux."""

from __future__ import annotations

import logging

import keyring
import keyring.errors

from falconterm.utils.constants import APP_ID

log = logging.getLogger(__name__)

_DISABLED = False


def _try() -> bool:
    """Detect whether the platform has a usable keyring backend."""
    global _DISABLED
    if _DISABLED:
        return False
    try:
        # Probe: setting + getting a sentinel.
        keyring.get_password(APP_ID, "__probe__")
        return True
    except keyring.errors.NoKeyringError:
        log.warning("No keyring backend available; password storage disabled.")
        _DISABLED = True
        return False
    except Exception as e:
        log.warning("Keyring probe failed (%s); continuing without stored passwords.", e)
        _DISABLED = True
        return False


def store(ref: str, password: str) -> bool:
    """Store a password under ``ref``. Returns True on success."""
    if not _try():
        return False
    try:
        keyring.set_password(APP_ID, ref, password)
        return True
    except Exception as e:
        log.warning("Keyring set failed for %s: %s", ref, e)
        return False


def fetch(ref: str) -> str | None:
    """Retrieve a password by ref, or None if unavailable / not found."""
    if not _try():
        return None
    try:
        return keyring.get_password(APP_ID, ref)
    except Exception as e:
        log.warning("Keyring get failed for %s: %s", ref, e)
        return None


def delete(ref: str) -> None:
    if not _try():
        return
    try:
        keyring.delete_password(APP_ID, ref)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception as e:
        log.warning("Keyring delete failed for %s: %s", ref, e)


def available() -> bool:
    return _try()
