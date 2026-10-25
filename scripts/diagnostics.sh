#!/usr/bin/env bash
#
# NOVA TV — Hardware diagnostics.
#
# Prints a quick health snapshot useful when something is wrong on the Pi.
# Does not modify anything.  Safe to run any time.

set -euo pipefail

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
hdr()   { color "36" "=== $* ==="; }

hdr "System"
hostnamectl 2>/dev/null || true
echo "Uptime: $(uptime -p 2>/dev/null || echo 'n/a')"
echo "Kernel: $(uname -a)"

hdr "Memory"
free -h

hdr "Storage"
df -h / 2>/dev/null || true

hdr "CPU temperature"
if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
    awk '{printf "%.1f °C\n", $1/1000}' /sys/class/thermal/thermal_zone0/temp
else
    echo "n/a (not on Pi?)"
fi

hdr "Network"
ip -o addr show 2>/dev/null | awk '{print $2, $4}' || true
echo "Wi-Fi SSID: $(iwgetid -r 2>/dev/null || echo 'n/a')"

hdr "HDMI-CEC"
if command -v cec-client >/dev/null 2>&1; then
    echo "cec-client: installed"
    timeout 3 cec-client -i 1 2>/dev/null | head -n 20 || true
else
    echo "cec-client NOT installed (apt install cec-utils)"
fi

hdr "Media player"
command -v mpv >/dev/null 2>&1 && echo "mpv: $(mpv --version | head -n 1)" \
    || echo "mpv NOT installed"

hdr "Browser"
command -v chromium-browser >/dev/null 2>&1 && echo "chromium: $(chromium-browser --version 2>/dev/null | head -n 1)" \
    || echo "chromium-browser NOT installed"

hdr "NOVA TV service"
systemctl status nova-tv.service --no-pager 2>/dev/null || echo "service not installed"

hdr "Recent NOVA TV logs (last 30 lines)"
journalctl -u nova-tv.service -n 30 --no-pager 2>/dev/null || true
