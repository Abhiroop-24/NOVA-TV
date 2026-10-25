# NOVA TV — Troubleshooting

## Quick diagnostic

Run the all-in-one health check on the Pi:

```bash
sudo bash /opt/nova-tv/scripts/diagnostics.sh
```

It prints CPU temperature, memory, storage, network, CEC availability, mpv
and browser presence, and the latest NOVA TV logs.

---

## Recovery access

NOVA TV always leaves two recovery channels open:

- **SSH** stays enabled. The systemd unit never touches `sshd`. If the display
  is unresponsive, SSH in and stop the service:
  ```bash
  sudo systemctl stop nova-tv.service
  ```
- **TTY**: press `Ctrl-Alt-F2` to open a login shell on tty2. Use `Ctrl-Alt-F1`
  to return to NOVA TV on tty1.

If the service crashes repeatedly, systemd caps restarts at 5 failures per 120
seconds and then stops, leaving the device on a normal login prompt.

---

## Black screen on boot

| Likely cause | Fix |
|--------------|-----|
| HDMI not detected | Confirm `config.txt` has `hdmi_force_hotplug=1` (Pi boot config, not NOVA TV). |
| Wrong video driver | Run `sudo /opt/nova-tv/venv/bin/python -m nova.main --dev` from a TTY to see console errors. |
| X failed to start | Check `journalctl -u nova-tv.service`; ensure `xserver-xorg` is installed. |
| Service crashed | `journalctl -u nova-tv.service -n 50` shows the traceback. |

---

## Remote/CEC not working

1. Confirm `cec-utils` is installed: `apt install cec-utils`.
2. Your TV must support HDMI-CEC (Samsung Anynet+, LG Simplink, Sony Bravia Sync,
   Panasonic Viera Link). Enable it in the TV's own settings menu.
3. Run the diagnostics screen in NOVA TV (Settings → Diagnostics) or the
   `scripts/diagnostics.sh` script; it reports whether the CEC listener started.
4. CEC is disabled in `--dev` mode by design. Use a USB keyboard to test there.
5. If CEC is unavailable, NOVA TV still works with any USB HID remote or keyboard.

---

## Application launch fails

- A browser service shows "Launch Error": install or repair `chromium-browser`.
- A native app shows "Executable not found": the configured binary isn't on
  `PATH`. Edit `config/applications.json` and set the correct path.
- The status dot is grey ("Untested"): the service hasn't been verified on this
  hardware. It may still work; see `streaming-compatibility.md`.

NOVA TV never silently replaces an official service with a third-party one and
never bypasses DRM. Browser streaming is a fallback, not a guaranteed feature.

---

## No media files appear

1. Settings → Media → "Rescan media now", or restart the screen.
2. Confirm the directory exists and is readable: `ls -l /media`.
3. Add directories by editing `settings.json` under `media.directories`, then
   restart NOVA TV. (Text entry isn't implemented in the UI by design.)
4. Confirm `mpv` is installed: `mpv --version`.

---

## Settings didn't persist

- NOVA TV writes atomically; a power loss mid-save keeps the previous file.
- If `settings.json` is corrupt, it is backed up as `settings.json.corrupt` and
  defaults are restored. Favourites and the error log are kept.
- Check `~/.config/nova-tv/` for the files.

---

## Performance

- Target: 30 FPS where hardware permits. The Diagnostics screen shows the
  live FPS history sparkline.
- If FPS is low: lower the frame-rate target (Settings → Frame rate target →
  24), and avoid running other heavy services.
- Memory is the main constraint on the Pi 3B+. The image cache is bounded
  (80 surfaces); `free -h` should show most of 1 GB free at idle.

---

## Configuration file locations

| File | Purpose |
|------|---------|
| `~/.config/nova-tv/settings.json` | User settings (atomic writes) |
| `~/.config/nova-tv/favourites.json` | Favourite app IDs |
| `~/.config/nova-tv/recent_errors.json` | Last 50 errors |
| `config/applications.json` (repo) | Application catalogue |
| `assets/` (repo) | Icons, artwork, fonts |

---

## Service management

```bash
sudo systemctl start nova-tv.service     # start now
sudo systemctl stop nova-tv.service      # stop
sudo systemctl restart nova-tv.service   # restart after config edits
sudo systemctl status nova-tv.service     # status
journalctl -u nova-tv.service -f          # follow logs
```
