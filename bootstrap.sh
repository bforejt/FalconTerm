#!/usr/bin/env bash
# bootstrap.sh — one-shot clean setup for FalconTerm.
#
# What it does:
#   1. Finds a supported Python (3.11, 3.12, or 3.13 — PySide6 6.11 does
#      not yet support 3.14).
#   2. Removes any existing .venv.
#   3. Creates a fresh .venv and upgrades pip.
#   4. Installs FalconTerm with the [dev] extras.
#   5. Runs the test suite.
#   6. Prints how to launch.
#
# Usage:
#     ./bootstrap.sh                      # auto-pick python3.13 -> 3.12 -> 3.11
#     ./bootstrap.sh python3.12           # use a specific interpreter
#     ./bootstrap.sh /opt/homebrew/bin/python3.13

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# --- pretty printing ---------------------------------------------------------
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
    BOLD=$(tput bold); DIM=$(tput dim); GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3); RED=$(tput setaf 1); RESET=$(tput sgr0)
else
    BOLD="" DIM="" GREEN="" YELLOW="" RED="" RESET=""
fi

step() { printf "\n${BOLD}${GREEN}==>${RESET} ${BOLD}%s${RESET}\n" "$*"; }
info() { printf "    %s\n" "$*"; }
warn() { printf "${BOLD}${YELLOW}warning:${RESET} %s\n" "$*" >&2; }
die()  { printf "${BOLD}${RED}error:${RESET} %s\n" "$*" >&2; exit 1; }

# --- pick a Python -----------------------------------------------------------
if [[ $# -gt 0 ]]; then
    PYTHON_CMD="$1"
    command -v "$PYTHON_CMD" >/dev/null 2>&1 || die "Python command '$PYTHON_CMD' not found on PATH"
else
    PYTHON_CMD=""
    for candidate in python3.13 python3.12 python3.11; do
        if command -v "$candidate" >/dev/null 2>&1; then
            PYTHON_CMD="$candidate"
            break
        fi
    done
fi

if [[ -z "$PYTHON_CMD" ]]; then
    cat >&2 <<EOF
${BOLD}${RED}No supported Python found on PATH.${RESET}

FalconTerm needs Python 3.11, 3.12, or 3.13.
PySide6 6.11 does not yet ship plugins that load under Python 3.14.

Install one:
    ${BOLD}brew install python@3.13${RESET}       # macOS (Homebrew)
    ${BOLD}sudo apt install python3.13${RESET}    # Debian / Ubuntu
    ${BOLD}uv python install 3.13${RESET}         # via astral.sh/uv

Or pass an explicit interpreter path:
    ${BOLD}./bootstrap.sh /path/to/python3.13${RESET}
EOF
    exit 1
fi

PY_VERSION="$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

case "$PY_VERSION" in
    3.11|3.12|3.13)
        info "Using ${BOLD}$PYTHON_CMD${RESET} (Python $PY_VERSION) ✓"
        ;;
    3.14|3.15)
        warn "Python $PY_VERSION is outside the supported range (3.11–3.13)."
        warn "PySide6 plugins are known to fail to load. Continue at your own risk."
        read -r -p "Continue anyway? [y/N] " yn
        [[ "$yn" =~ ^[Yy] ]] || die "aborted"
        ;;
    *)
        die "Python $PY_VERSION is too old. Need 3.11 or newer."
        ;;
esac

# --- nuke existing venv ------------------------------------------------------
if [[ -d .venv ]]; then
    step "Removing existing .venv"
    rm -rf .venv
fi

# --- create + install --------------------------------------------------------
step "Creating fresh .venv"
"$PYTHON_CMD" -m venv .venv

step "Upgrading pip"
.venv/bin/pip install --disable-pip-version-check -q -U pip

step "Installing FalconTerm and dev dependencies"
info "(this may take a minute — PySide6 is a large wheel)"
.venv/bin/pip install --disable-pip-version-check -e ".[dev]"

# --- verify ------------------------------------------------------------------
step "Running test suite"
if .venv/bin/pytest -q; then
    info "${GREEN}all tests passed${RESET}"
else
    warn "tests failed — see output above"
    exit 1
fi

# --- done --------------------------------------------------------------------
cat <<EOF

${BOLD}${GREEN}✓ FalconTerm is ready.${RESET}

Launch:        ${BOLD}.venv/bin/falconterm${RESET}
Run tests:     ${BOLD}.venv/bin/pytest${RESET}
Lint + format: ${BOLD}.venv/bin/ruff check . && .venv/bin/ruff format .${RESET}

Tip: ${DIM}source .venv/bin/activate${RESET} to put the venv's tools on your PATH.

EOF
