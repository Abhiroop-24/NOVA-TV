#!/usr/bin/env bash
#
# NOVA TV — Uninstaller.
#
# Removes the systemd units, stops the service, and deletes the install
# prefix.  User configuration (~/.config/nova-tv) is preserved by default so
# settings and favourites survive a reinstall; pass --purge to also remove it.

set -euo pipefail

INSTALL_PREFIX="/opt/nova-tv"
SERVICE_DIR="/etc/systemd/system"
USER_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/nova-tv"

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
info()  { color "36" "→ $*"; }
ok()    { color "32" "✓ $*"; }

[[ $EUID -eq 0 ]] || { echo "Run with sudo"; exit 1; }

info "Stopping and disabling service..."
systemctl stop nova-tv.service 2>/dev/null || true
systemctl disable nova-tv.service 2>/dev/null || true
rm -f "${SERVICE_DIR}/nova-tv.service" "${SERVICE_DIR}/nova-tv.target"
rm -rf "${SERVICE_DIR}/nova-tv.target.wants"
systemctl daemon-reload
ok "Service removed"

info "Removing install prefix ${INSTALL_PREFIX}..."
rm -rf "${INSTALL_PREFIX}"
ok "Install prefix removed"

if [[ "${1:-}" == "--purge" ]]; then
    info "Purging user configuration at ${USER_CONFIG}..."
    rm -rf "${USER_CONFIG}"
    ok "User configuration purged"
else
    echo "User configuration kept at ${USER_CONFIG} (pass --purge to remove it)."
fi

echo "$(color '32' 'NOVA TV uninstalled.')"
