"""Per-session terminal log files. ANSI-stripped, timestamped filenames."""

from __future__ import annotations

import datetime as dt
import logging
import threading
from pathlib import Path

from falconterm.services.paths import logs_dir
from falconterm.utils.ansi_strip import strip_ansi
from falconterm.utils.constants import LOG_BUFFER_BYTES

log = logging.getLogger(__name__)


def sanitize(name: str) -> str:
    bad = '/\\:*?"<>| \t\n\r'
    out = "".join(c if c not in bad else "_" for c in name).strip("._")
    return out or "session"


class SessionLogger:
    """Append ANSI-stripped terminal output to a timestamped log file."""

    def __init__(self, session_name: str, encoding: str = "utf-8") -> None:
        self._encoding = encoding
        ts = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe = sanitize(session_name)
        self.path = logs_dir() / f"{safe}_{ts}.log"
        self._lock = threading.Lock()
        self._fh = self.path.open("ab", buffering=0)
        # Header
        header = (
            f"--- FalconTerm session log ---\n"
            f"session: {session_name}\n"
            f"started: {dt.datetime.now().isoformat()}\n"
            f"---\n\n"
        ).encode(encoding, errors="replace")
        self._fh.write(header)
        self._buf = bytearray()

    def write(self, data: bytes) -> None:
        """Accept raw terminal output bytes, strip ANSI, buffer, flush when full."""
        try:
            text = data.decode(self._encoding, errors="replace")
        except Exception:
            return
        clean = strip_ansi(text).encode(self._encoding, errors="replace")
        with self._lock:
            self._buf.extend(clean)
            if len(self._buf) >= LOG_BUFFER_BYTES:
                self._flush_locked()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if not self._buf:
            return
        try:
            self._fh.write(bytes(self._buf))
        except Exception as e:
            log.warning("Log write failed (%s): %s", self.path, e)
        self._buf.clear()

    def close(self) -> None:
        self.flush()
        try:
            self._fh.close()
        except Exception:
            pass


def prune_old_logs(retention_days: int) -> None:
    """Delete log files older than retention_days."""
    if retention_days <= 0:
        return
    cutoff = dt.datetime.now() - dt.timedelta(days=retention_days)
    try:
        for p in logs_dir().glob("*.log"):
            try:
                mtime = dt.datetime.fromtimestamp(p.stat().st_mtime)
                if mtime < cutoff:
                    p.unlink(missing_ok=True)
            except OSError:
                continue
    except Exception as e:
        log.warning("Log prune failed: %s", e)


def open_logs_dir() -> Path:
    return logs_dir()
