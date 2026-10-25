# NOVA TV — Service compatibility

This is the honest, evidence-based status of each streaming and web service
on the Raspberry Pi 3 Model B+. NOVA TV does not claim a service works merely
because a website opens. The in-app **Service Compatibility** screen reads this
status live from the launcher; this document is the long-form reference.

## Status legend

| Status | Meaning |
|--------|---------|
| **Verified** | Tested and working on the target hardware. |
| **Experimental** | A reasonable fallback that works partially or with caveats. |
| **Unavailable** | Known not to work on this hardware. |
| **Untested** | Not yet validated on real hardware; treat as unknown. |

> The Raspberry Pi 3B+ does not run the certified Android TV apps or certified
> Widevine DRM builds that official streaming services require. Browser
> fallbacks exist but protected content frequently fails. This is a hardware
> and licensing limitation, not a NOVA TV bug.

## Service-by-service status

### Local media — Verified (conditional)
- Method: `internal` → opens the Media screen; playback via `mpv`.
- Codec support depends on the mpv build and Pi GPU acceleration. Verify the
  specific codecs you need before relying on it.
- Limitations: H.265/HEVC may not decode smoothly at 1080p on the 3B+.

### System settings — Verified
- Method: `internal` → built-in Settings screen. Persists across reboots.

### YouTube — Experimental
- Method: `browser` → `https://www.youtube.com/tv` in chromium-browser.
- Sign-in happens inside the browser; NOVA TV never stores Google credentials.
- Limitations: the TV-optimised site is D-pad friendly in some browsers; 1080p
  playback may stutter on the 3B+. AV1/VP9 decoding is software-only here.

### Prime Video — Experimental
- Method: `browser` → `https://www.primevideo.com/`.
- Limitations: Widevine L1 is not available in Raspberry Pi OS browsers; most
  protected Prime Video content will not play. Free/ad-supported content may
  work. No official Android TV app exists for this hardware.

### JioHotstar — Experimental
- Method: `browser` → `https://www.jiohotstar.com/`.
- Limitations: region restrictions and DRM may block playback in a browser.
  No native app on Pi 3B+.

### Google Search — Experimental
- Method: `browser` → `https://www.google.com/`.
- Works as a website; not designed for D-pad navigation.

### Google Account — Experimental
- Method: `browser` → `https://myaccount.google.com/`.
- Account management in the browser only. NOVA TV never requests or stores
  Google passwords. Sign-in state lives in the browser's profile, not in NOVA
  TV config.

### Google Play Store — Unavailable
- Requires a certified Android TV build. Raspberry Pi OS cannot install or run
  it. Use the browser-based services above instead. This entry is shown in the
  launcher greyed out with a reason, never silently replaced.

## How NOVA TV stays honest

- Each app entry in `config/applications.json` declares a `compat_status`.
- The launcher refuses to launch `unavailable` entries and reports the reason.
- The in-app compatibility screen shows the live status, method, notes and last
  error for every entry.
- NOVA TV does not bypass DRM, device certification, authentication, or
  regional restrictions, and does not silently substitute third-party apps for
  official services.

## Adding or editing services

Edit `config/applications.json`. Each entry:

```json
{
  "id": "my_service",
  "name": "My Service",
  "description": "Short description",
  "launch_method": "browser",
  "url": "https://example.com/",
  "compat_status": "experimental",
  "compat_notes": "What works and what doesn't on the Pi 3B+.",
  "category": "streaming",
  "is_pinned": true
}
```

`launch_method` is one of `internal`, `browser`, `native`, `unavailable`.
`compat_status` is one of `verified`, `experimental`, `unavailable`, `untested`.

Only claim `verified` after you have actually tested the service on a Pi 3B+
with the content you intend to watch. Until then, use `untested`.
