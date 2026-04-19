"""Entry point: `python -m falconterm` or `falconterm` console script."""

from __future__ import annotations

import sys


def main() -> int:
    # Import here so the qasync event loop policy is installed before any
    # asyncio import creates a loop (see app.bootstrap).
    from falconterm.app import run

    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
