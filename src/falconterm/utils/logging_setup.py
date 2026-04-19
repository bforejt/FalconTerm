"""Root logging configuration.

Call ``configure()`` once at process startup (done from ``falconterm.app``).

Environment variables:
    FALCONTERM_LOG_LEVEL    One of DEBUG, INFO, WARNING, ERROR (default INFO).
                            Applied to *our* loggers AND to asyncssh.
    FALCONTERM_DEBUG=1      Shorthand for FALCONTERM_LOG_LEVEL=DEBUG.
    FALCONTERM_LOG_FILE     Override the log file path. Default is
                            platformdirs.user_log_dir("FalconTerm")/falconterm.log.

Stream logs go to stderr. File logs rotate at 2 MB x 5 files.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

_CONFIGURED = False


def configure() -> Path | None:
    """Install console + rotating-file handlers on the root logger. Idempotent.

    Returns the log-file path (or None if the file handler couldn't be opened).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return _current_log_path()

    level_name = os.environ.get("FALCONTERM_LOG_LEVEL")
    if not level_name and os.environ.get("FALCONTERM_DEBUG"):
        level_name = "DEBUG"
    level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(min(level, logging.INFO))  # never raise the floor above INFO

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # --- console ---
    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(fmt)
    root.addHandler(stream)

    # --- rotating file ---
    log_path = _resolve_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)  # file always captures DEBUG
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        log_path = None  # type: ignore[assignment]

    # Calm the noisy libraries unless the user explicitly asked for debug.
    if level > logging.DEBUG:
        for noisy in ("asyncssh", "asyncio"):
            logging.getLogger(noisy).setLevel(logging.INFO)
    else:
        # User asked for DEBUG — give them asyncssh DEBUG too, but keep asyncio at INFO
        # (asyncio DEBUG is extremely chatty — connection polling, selector events, etc.).
        logging.getLogger("asyncssh").setLevel(logging.DEBUG)
        logging.getLogger("asyncio").setLevel(logging.INFO)

    _CONFIGURED = True
    logging.getLogger(__name__).info(
        "logging configured: level=%s, file=%s", logging.getLevelName(level), log_path
    )
    return log_path


def _resolve_log_path() -> Path:
    override = os.environ.get("FALCONTERM_LOG_FILE")
    if override:
        return Path(override).expanduser()
    # Lazy import to avoid pulling platformdirs before it's needed.
    from falconterm.services.paths import logs_dir

    return logs_dir() / "falconterm.log"


def _current_log_path() -> Path | None:
    for h in logging.getLogger().handlers:
        if isinstance(h, logging.handlers.RotatingFileHandler):
            return Path(h.baseFilename)
    return None
