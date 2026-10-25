#!/usr/bin/env bash
# NOVA TV — xinit client script.
# xinit runs this script as the X client after X server starts.
# DISPLAY is set by xinit automatically.

export DISPLAY=:0
export HOME=/root
export XDG_RUNTIME_DIR=/tmp/runtime-root
export SDL_VIDEODRIVER=x11
export SDL_AUDIODRIVER=alsa

# Hide the mouse cursor
xsetroot -cursor_name left_ptr 2>/dev/null || true

# Disable screen blanking / DPMS
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# Launch NOVA TV
exec /opt/nova-tv/venv/bin/python -m nova.main
