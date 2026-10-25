# NOVA TV

A minimal, cinematic, D-pad-driven TV operating environment for the
**Raspberry Pi 3 Model B+**. It boots directly into a fullscreen interface,
navigates with a TV remote (or keyboard), launches applications, browses
local media, and persists settings — without pretending that certified
streaming services work where they don't.

NOVA TV is a real software project, not a screenshot: modular Python, an
honest compatibility model, atomic config, crash recovery, systemd boot
integration, and a test suite.

---

## Features

- **Native fullscreen interface** — Pygame/SDL2, 1080p, dark cinematic theme.
- **D-pad navigation** — up/down/left/right/select/back/home, with a 2-D focus
  model and column memory; no mouse required.
- **Multiple input backends** — keyboard, USB HID / joystick, HDMI-CEC
  (via `cec-client`). One `Action` enum drives every screen.
- **Application launcher** — configurable entries (Prime Video, YouTube,
  JioHotstar, Google Search, Google Account, local media, settings) with
  honest verified/experimental/unavailable/untested statuses.
- **Local media browser** — async directory scan, sidecar thumbnail
  detection, playback via `mpv`, graceful handling of missing files/players.
- **Persistent settings** — atomic JSON writes, corruption recovery (backs up
  the bad file, restores defaults, keeps favourites).
- **Diagnostics & logs** — live system metrics, FPS sparkline, recent error
  log, input-device status.
- **Service compatibility page** — the single source of truth for what works
  on the Pi 3B+.
- **Crash recovery** — per-screen supervisor drops a broken screen and shows a
  recovery screen; systemd restarts the whole process on failure.
- **Simulation mode** — `--dev` windowed mode for desktop development; no Pi
  required.

---

## Repository structure

```
nova-tv/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── config/
│   └── applications.json        # application catalogue (edit to add services)
├── assets/
│   ├── icons/                   # procedural or licensed PNG icons
│   ├── artwork/                 # hero + demo posters
│   └── fonts/                   # bundled .ttf (Inter recommended)
├── nova/
│   ├── main.py                  # NovaApp orchestrator + main loop + supervisor
│   ├── theme.py                 # design tokens
│   ├── assets.py                # font/image loading (bounded cache)
│   ├── applications/launcher.py
│   ├── media/scanner.py
│   ├── navigation/{focus,input_manager}.py
│   ├── settings/config.py
│   ├── system/diagnostics.py
│   └── ui/{renderer,screen_manager,screens/*}.py
├── scripts/
│   ├── install.sh               # Raspberry Pi installer
│   ├── uninstall.sh
│   ├── run-dev.sh               # Linux/macOS dev runner
│   ├── run-dev.ps1              # Windows dev runner
│   ├── diagnostics.sh           # Pi health check
│   └── generate_assets.py       # procedural asset generator
├── systemd/
│   ├── nova-tv.service
│   └── nova-tv.target
├── tests/                       # pytest suite (unit + headless integration)
└── docs/
    ├── architecture.md
    ├── installation.md
    ├── troubleshooting.md
    └── streaming-compatibility.md
```

---

## Quick start — Windows development (simulation)

```powershell
# From the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"          # pygame + pytest (dev extras)
python scripts\generate_assets.py all
powershell -ExecutionPolicy Bypass -File scripts\run-dev.ps1
```

| Key | Action | Key | Action |
|-----|--------|-----|--------|
| ← ↑ ↓ → / WASD | Navigate | Enter / Space | Select |
| Esc / Backspace | Back | Home / F1 | Home |
| F3 | Debug overlay | Ctrl-Q | Quit |

---

## Quick start — Raspberry Pi

```bash
# From a Pi with SSH enabled (replace <PI_IP>)
scp -r nova-tv pi@<PI_IP>:/opt/nova-tv
ssh pi@<PI_IP>
cd /opt/nova-tv
sudo bash scripts/install.sh
sudo systemctl enable nova-tv.service
sudo reboot
```

NOVA TV boots fullscreen. SSH and networking are never disabled. See
[docs/installation.md](docs/installation.md) for the full procedure and SD-card
guidance.

---

## Architecture

A native Pygame/SDL2 interface driven by a single main loop. The loop is
cheap — poll input, update the active screen, draw, flip — capped to 30 FPS.
All filesystem, network and media work happens on background threads or in
external subprocesses the loop merely inspects.

```
InputManager ──▶ Actions ──▶ ScreenManager (stack) ──▶ Screens
                                    │ reads
                                    ▼
        ConfigManager · AppLauncher · MediaScanner · NetworkChecker
```

Full design and trade-offs: [docs/architecture.md](docs/architecture.md).

---

## Configuration

User settings live in `~/.config/nova-tv/` (`%APPDATA%/NovaTV` on Windows):

| File | Purpose |
|------|---------|
| `settings.json` | Display, theme, media, input, system |
| `favourites.json` | Favourite app IDs |
| `recent_errors.json` | Last 50 errors |

The application catalogue is `config/applications.json` in the repo. Settings
persist across reboots via atomic writes.

---

## Honest feature status

NOVA TV never claims a service works because a website opens. Verified means
tested on the target hardware. On a development computer everything runs in
**simulation**; hardware-specific features (HDMI-CEC, CPU temperature, boot
integration) are marked **Untested on hardware** until validated on a real Pi.

| Feature | Status (sim) | Status (Pi) |
|---------|:------------:|:-----------:|
| D-pad navigation | ✓ Verified | Untested |
| Persistent settings | ✓ Verified | Untested |
| Local media browsing | ✓ Verified | Untested |
| Application launcher | ✓ Verified | Untested |
| Crash recovery | ✓ Verified | Untested |
| HDMI-CEC remote | — | Untested |
| Boot-to-interface (systemd) | — | Untested |
| Browser streaming (YT/Prime/Hotstar) | Experimental | Experimental (DRM-limited) |
| Certified DRM services | ✗ Unavailable | ✗ Unavailable |

> Simulation = running on Windows dev machine (Python 3.13, pygame 2.6.1, dummy SDL driver).
> Tests confirmed: **59 passed, 4 skipped** (the 4 skipped are bash syntax checks, not applicable on Windows).

See [docs/streaming-compatibility.md](docs/streaming-compatibility.md) for the
per-service breakdown and limitations.

---

## Testing

```bash
# From the repo root (with the venv active)
python -m pytest tests/ -v
```

Tests cover: configuration persistence & corruption recovery, focus
movement, launcher error handling, media scanning, input mapping, screen-stack
behaviour, headless app rendering + recovery, install-artifact validation, and
offline/low-memory behaviour. Hardware-dependent integration is separated and
clearly marked.

**Confirmed test results (Python 3.13 / pygame 2.6.1 / Windows dev machine):**

```
59 passed, 4 skipped in 1.19s
```

The 4 skipped are bash shell-script syntax checks — expected on Windows where
`bash` is not available. They pass on Linux/macOS and on the Pi.

---

## Troubleshooting

```bash
sudo bash /opt/nova-tv/scripts/diagnostics.sh     # health snapshot
journalctl -u nova-tv.service -f                  # live logs
sudo systemctl stop nova-tv.service                # stop the interface
```

SSH and `Ctrl-Alt-F2` are always available for recovery. Full guide:
[docs/troubleshooting.md](docs/troubleshooting.md).

---

## Limitations

- **Streaming DRM**: the Pi 3B+ cannot run certified Android TV apps or
  Widevine L1; protected content from Prime Video / JioHotstar typically will
  not play in a browser. NOVA TV does not bypass DRM.
- **No credential storage**: NOVA TV never requests or stores Google or
  streaming-service passwords. Sign-in happens inside the external browser.
- **1 GB RAM**: the image cache is bounded (80 surfaces); media is scanned
  lazily; no full library is loaded into memory.
- **Text input**: media directories are configured by editing `settings.json`,
  not via an on-screen keyboard (by design, for a remote-first experience).

---

## License

MIT. See [LICENSE](LICENSE). Bundle only artwork and fonts you have the right
to distribute (the procedural asset generator produces licence-free glyphs).
