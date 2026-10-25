# NOVA TV — Architecture

NOVA TV is a lightweight, cinematic TV environment for the Raspberry Pi 3
Model B+. It boots directly into a fullscreen, D-pad-navigable interface and
degrades gracefully when hardware features are unavailable.

## Design principles

- Cinematic, dark, original visual design (not a clone of any product).
- D-pad first; no mouse or on-screen cursor required.
- Minimal resource usage on 1 GB RAM.
- Honest compatibility reporting — never fake a working streaming service.
- Modular, testable Python; no single monolithic file.
- The interface and system services are separate.

## Target hardware

- Raspberry Pi 3 Model B+ (Broadcom BCM2837B0, quad-core Cortex-A53, 1 GB RAM).
- ARMv7-compatible 32-bit userspace preferred.
- HDMI 1080p, Ethernet/Wi-Fi, USB, HDMI-CEC where the TV supports it.

## Stack

| Layer | Choice | Rationale |
|------|--------|-----------|
| Base OS | Raspberry Pi OS Lite 32-bit | Official, supported on Pi 3B+, minimal. |
| Graphics | X11 + xinit (no full DE) | Lightweight; kiosk starts its own X server. |
| UI renderer | Pygame / SDL2 | Native fullscreen, low overhead, cross-platform for dev. |
| Language | Python 3.9+ | Maintainable, fast enough for a 30 FPS TV UI. |
| Service manager | systemd | Boot ordering, restart on crash. |
| Media playback | mpv (external) | Hardware-accelerated where available; codec support verified on device. |
| Browser fallback | chromium-browser | For web streaming services, run as a separate process. |
| Remote input | Keyboard, USB HID, joystick, HDMI-CEC via cec-client | Abstraction hides the source from the UI. |

Electron, heavyweight desktops, Docker stacks, and an embedded full browser as
the permanent renderer are deliberately avoided to keep memory and CPU use
low on constrained hardware.

## Module map

```
nova/
├── main.py                  NovaApp orchestrator + main loop + supervisor
├── theme.py                 Design tokens (colours, fonts, spacing, animation)
├── assets.py                Font/image loading with bounded LRU cache
├── applications/
│   └── launcher.py          AppEntry, AppLauncher (async launch + tracking)
├── media/
│   └── scanner.py            MediaScanner (async), MediaFile, MediaPlayer (mpv)
├── navigation/
│   ├── focus.py              FocusGroup (2-D spatial D-pad model)
│   └── input_manager.py     Action enum; keyboard/joystick/CEC backends; repeat
├── settings/
│   └── config.py             ConfigManager (atomic writes, corruption recovery)
├── system/
│   └── diagnostics.py        SystemInfo, NetworkChecker, Pi detection
└── ui/
    ├── renderer.py           Drawing primitives (cards, focus rings, text…)
    ├── screen_manager.py     Stack-based ScreenManager (HOME/BACK routing)
    └── screens/
        ├── home_screen.py        Nav bar, featured, app + favourites rows
        ├── apps_screen.py        Full application browser
        ├── media_screen.py       Local media grid + playback
        ├── favourites_screen.py  Favourites list + remove
        ├── settings_screen.py    Persistent toggles + sub-screen navigation
        ├── network_screen.py     Network + input device status
        ├── about_screen.py       Version, hardware, honest feature status
        ├── diagnostics_screen.py System metrics + recent error log
        └── compatibility_screen.py Service compatibility report
```

## Data flow

```
                  ┌───────────────────────────────┐
   input devices  │  InputManager (keyboard/CEC/   │   semantic Actions
  ───────────────▶│  joystick)  ──poll()──▶        │──────────────┐
                  └───────────────────────────────┘              │
                                                                   ▼
   ┌───────────────────────────────┐    push/pop     ┌───────────────────────┐
   │  ScreenManager (stack)        │◀──────────────▶│  NovaApp main loop     │
   │  Home / Apps / Media / …       │                │  poll → update → draw  │
   └───────────────────────────────┘                └───────────────────────┘
            │ reads/writes                                       │ reads
            ▼                                                    ▼
   ┌──────────────────┐   ┌──────────────┐   ┌─────────────┐  ┌──────────────┐
   │ ConfigManager     │   │ AppLauncher  │   │ MediaScanner│  │ NetworkChecker│
   │ (atomic JSON)     │   │ (subprocess) │   │ (thread)    │  │ (thread)      │
   └──────────────────┘   └──────────────┘   └─────────────┘  └──────────────┘
```

The main loop is deliberately cheap: it polls input, updates the active
screen, draws, and flips — capped to `theme.FPS_TARGET` (30). No filesystem,
network, or media work runs in the loop; those happen on background threads or
in external subprocesses that the loop merely inspects.

## Rendering

All drawing happens in 1080p design space. `theme.py` defines the screen
geometry; `renderer.py` provides primitives (rounded rects, focus rings,
cards, text with truncation/wrapping, gradient overlays, message boxes).
Missing image assets degrade to procedural placeholders (coloured circles,
gradient rects) so the interface is never blank.

## Focus and navigation

`FocusGroup` is a 2-D grid keyed by `(row, col)`. LEFT/RIGHT move within a row
(with wrapping); UP/DOWN move between rows keeping a per-row column memory.
SELECT fires the focused item's callback; BACK pops the screen stack; HOME
returns to the root. Every screen uses this one system. There are no focus
traps — UP at the top row is delegated to the screen (typically no-op), DOWN at
the bottom is a no-op.

## Application launching

`AppLauncher` reads `config/applications.json`. Each entry declares a launch
method (`internal`, `browser`, `native`, `unavailable`) and an honest
compatibility status (`verified`, `experimental`, `unavailable`, `untested`).
External apps run as separate processes; the launcher tracks the active
process so the UI can detect when it exits and re-display NOVA TV. Browser
launches never embed credentials in NOVA TV — sign-in happens inside the
external browser only. See `streaming-compatibility.md`.

## Configuration and persistence

`ConfigManager` stores settings, favourites, and recent errors as separate
JSON files in a platform-appropriate directory (`~/.config/nova-tv` on Linux,
`%APPDATA%/NovaTV` on Windows). Writes are atomic (temp file + rename). On
corruption the loader backs up the bad file as `.corrupt` and restores safe
defaults without deleting favourites. No passwords or tokens are stored.

## Crash recovery

The `NovaApp` supervisor wraps each frame; if a screen raises, the failing
screen is dropped and a self-contained `RecoveryScreen` is shown on top of
Home, and the error is appended to the recent-errors log. systemd
(`Restart=on-failure`) restarts the whole process if it exits. A runaway
restart loop (5 failures / 120 s) stops retrying so the user can reach a
maintenance shell via Ctrl-Alt-F2 or SSH.

## Simulation vs. production

`--dev` runs windowed with CEC off for desktop testing. `--headless` uses the
SDL dummy video driver so unit tests can exercise the loop without a window.
Hardware-specific functions (CEC, CPU temp, Pi model) return safe stubs off
the Pi and are labelled "Untested on hardware" where applicable.
