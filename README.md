# FalconTerm

A cross-platform GUI terminal inspired by SecureCRT. Built with Python + PySide6.

## Features

- **SSH**, **Telnet**, and **Serial** connections
- **Hierarchical session manager** — organize hundreds of devices in nested folders
- **Per-session settings** — font, colors, terminal size, scrollback, logging
- **Global defaults** — new sessions inherit, overrides per-session
- **Tabs** — multiple concurrent sessions in one window
- **Session logging** to timestamped files
- **Password storage** via the OS keyring (Keychain / Credential Manager / Secret Service)
- **Import/export** session bundles for syncing between machines
- **Quick Connect** for one-off connections
- **Font picker** (monospace only) and **color scheme editor** with live preview

## Platforms

- **macOS** (priority target, arm64 + x86_64)
- **Windows**
- **Linux**

## Install

Requires Python 3.11–3.13 (PySide6 6.11 does not yet support Python 3.14).

### Quick start

```bash
./bootstrap.sh
```

The script picks a supported Python (prefers `python3.13`), nukes any existing
`.venv`, creates a fresh one, installs FalconTerm with dev deps, and runs the
test suite. Pass an explicit interpreter if needed: `./bootstrap.sh python3.12`.

### Manual

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Run

```bash
falconterm
# or
python -m falconterm
```

## Development

```bash
# Tests
pytest

# Lint + format
ruff check .
ruff format .

# Type check
mypy src/falconterm
```

## Configuration

- **Session config:** `platformdirs.user_config_dir("FalconTerm") / "sessions.json"`
- **Session logs:** `platformdirs.user_log_dir("FalconTerm")`
- **Passwords:** OS keyring (never in config files)

## Tech Stack

| Concern | Library |
|---|---|
| GUI | PySide6 (Qt 6) |
| Terminal emulation | pyte + custom QWidget |
| SSH | asyncssh |
| Telnet | telnetlib3 |
| Serial | pyserial + pyserial-asyncio |
| Async event loop | qasync |
| Passwords | keyring |
| Paths | platformdirs |
| Models | pydantic v2 |

## License

Apache 2.0 — see [LICENSE](LICENSE).
