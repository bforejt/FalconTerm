"""UUID helpers."""

from __future__ import annotations

import uuid


def new_id() -> str:
    """Short URL-safe unique ID for nodes."""
    return uuid.uuid4().hex[:12]
