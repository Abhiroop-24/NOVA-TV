#!/usr/bin/env bash
#
# NOVA TV — Development/simulation runner (Linux / macOS / Pi desktop).
#
# Runs the interface in a windowed "dev" mode with HDMI-CEC disabled so you
# can test navigation with a keyboard on a normal desktop computer without
# Raspberry Pi hardware.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# Use a venv if present, otherwise system python
if [[ -d "${REPO_ROOT}/.venv" ]]; then
    PY="${REPO_ROOT}/.venv/bin/python"
else
    PY="python3"
fi

export NOVA_DEV=1
exec "${PY}" -m nova.main --dev --no-cec "$@"
