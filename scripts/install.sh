#!/usr/bin/env bash
#
# NOVA TV — Raspberry Pi installer.
#
# Run with:  sudo bash scripts/install.sh
# Safe to re-run. SSH and networking are never touched.

set -euo pipefail

INSTALL_PREFIX="/opt/nova-tv"
VENV_DIR="${INSTALL_PREFIX}/venv"
SERVICE_DIR="/etc/systemd/system"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

info()  { printf '\033[36m→ %s\033[0m\n' "$*"; }
ok()    { printf '\033[32m✓ %s\033[0m\n' "$*"; }
warn()  { printf '\033[33m! %s\033[0m\n' "$*"; }
die()   { printf '\033[31m✗ %s\033[0m\n' "$*"; exit 1; }

[[ $EUID -eq 0 ]] || die "Run with sudo: sudo bash scripts/install.sh"

# ── 1. Checks ────────────────────────────────────────────────────────────────
info "Checking environment..."
command -v python3 >/dev/null || die "python3 not found"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' \
    || die "Python 3.9+ required"

if [[ -f /proc/device-tree/model ]]; then
    MODEL="$(tr -d '\0' < /proc/device-tree/model)"
    ok "Device: ${MODEL}"
else
    warn "Not on a Raspberry Pi — hardware features will be unavailable"
fi

# ── 2. OS packages ───────────────────────────────────────────────────────────
info "Installing OS packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0 \
    fonts-dejavu-core \
    mpv \
    cec-utils \
    xserver-xorg xserver-xorg-video-fbdev xinit openbox \
    >/dev/null
ok "OS packages installed"

# ── 3. Virtualenv ────────────────────────────────────────────────────────────
info "Setting up virtualenv at ${VENV_DIR}..."
mkdir -p "${INSTALL_PREFIX}"
[[ -d "${VENV_DIR}" ]] || python3 -m venv "${VENV_DIR}"
PY="${VENV_DIR}/bin/python"
PIP="${VENV_DIR}/bin/pip"

"${PIP}" install --upgrade pip -q
"${PIP}" install -r "${REPO_ROOT}/requirements.txt" -q
ok "Python dependencies installed (pygame, yt-dlp)"

# ── 4. Install package ───────────────────────────────────────────────────────
info "Installing NOVA TV..."
cp -r "${REPO_ROOT}/." "${INSTALL_PREFIX}/"
"${PIP}" install -e "${INSTALL_PREFIX}" -q
ok "NOVA TV installed to ${INSTALL_PREFIX}"

# ── 5. Generate assets ───────────────────────────────────────────────────────
info "Generating assets..."
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
    "${PY}" "${INSTALL_PREFIX}/scripts/generate_assets.py" all \
    || warn "Asset generation failed — will use placeholders"
ok "Assets ready"

# ── 6. yt-dlp update ────────────────────────────────────────────────────────
info "Updating yt-dlp to latest..."
"${PIP}" install -U yt-dlp -q
ok "yt-dlp up to date"

# ── 7. systemd units ────────────────────────────────────────────────────────
info "Installing systemd units..."
install -m 644 "${REPO_ROOT}/systemd/nova-tv.service" "${SERVICE_DIR}/nova-tv.service"
install -m 644 "${REPO_ROOT}/systemd/nova-tv.target" "${SERVICE_DIR}/nova-tv.target"
systemctl daemon-reload
systemctl enable nova-tv.service >/dev/null
ok "systemd units installed and enabled"

# ── 8. Done ──────────────────────────────────────────────────────────────────
printf '\n\033[32mNOVA TV installed successfully.\033[0m\n\n'
echo "Start now:     sudo systemctl start nova-tv.service"
echo "Follow logs:   journalctl -u nova-tv.service -f"
echo "Stop:          sudo systemctl stop nova-tv.service"
echo ""
echo "SSH and networking are untouched."
echo "See docs/installation.md for the SD card deployment guide."
