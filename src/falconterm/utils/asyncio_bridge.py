"""Helpers to bridge asyncio coroutines with Qt widget callbacks."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


def spawn(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    """Schedule a coroutine on the running (qasync) event loop and return the Task.

    Safe to call from Qt signal handlers — qasync installs the loop on the Qt thread.
    """
    loop = asyncio.get_event_loop()
    return loop.create_task(coro)
