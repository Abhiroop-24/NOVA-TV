# NOVA TV — Complete Installation Guide

This guide takes you from a blank SD card to a booting NOVA TV OS.
Your SD card (E:) is currently blank/FAT32. Follow every step in order.

---

## Step 1 — Flash Raspberry Pi OS to the SD card

You need to write the Raspberry Pi OS image to the SD card.
**This cannot be done from inside NOVA TV or from a script — you do it yourself.**

### Option A — Raspberry Pi Imager (recommended, 5 minutes)

1. Download **Raspberry Pi Imager** from:
   **https://www.raspberrypi.com/software/**

2. Insert your SD card (currently E: on your machine).

3. Open Raspberry Pi Imager.

4. Click **Choose OS** → **Raspberry Pi OS (other)** →
   **Raspberry Pi OS Lite (32-bit)** ← important, NOT the full desktop version.

5. Click **Choose Storage** → select your SD card (E: — 29.7 GB).

6. Click the **gear icon** (Advanced settings) and configure:
   - **Hostname:** `nova-tv`
   - **Enable SSH:** checked
   - **Username:** `pi`  Password: (your choice)
   - **Configure Wi-Fi:** enter your SSID and password
   - **Locale:** set your timezone and keyboard

7. Click **Write**. This takes about 5 minutes.

8. When done, **do not eject yet** — add the file in Step 2.

---

## Step 2 — Add NOVA TV to the SD card

After flashing, the SD card will have two partitions:
- **E: (BOOT)** — FAT32, small, contains bootloader files
- A second ext4 Linux partition — Windows cannot see this directly

**You cannot write NOVA TV source files to the BOOT partition.**
The source code goes to the Linux filesystem.

### Method A — Copy over Wi-Fi/SSH after first boot (easiest)

1. Insert the SD card into the Pi. Boot it.
2. Find the Pi's IP address — check your router, or use:
   ```
   ping nova-tv.local
   ```
3. On your Windows machine, open PowerShell:
   ```powershell
   # Copy the NOVA TV project to the Pi
   scp -r "c:\Users\abhiroop\Documents\NOVA TV\nova-tv" pi@<PI_IP>:/home/pi/nova-tv

   # SSH into the Pi
   ssh pi@<PI_IP>

   # Run the installer
   cd /home/pi/nova-tv
   sudo bash scripts/install.sh
   ```
4. Reboot:
   ```bash
   sudo reboot
   ```
   NOVA TV will start automatically on next boot.

### Method B — Pre-copy with WSL2 (advanced, Windows 11)

If you have WSL2 and Windows 11 (21H2+), you can mount the ext4 partition:

```powershell
# Find the disk number for the SD card
GET-Disk | Where-Object BusType -eq "USB"

# Mount partition 2 (the Linux rootfs) in WSL2
wsl --mount \\.\PhysicalDrive<N> --partition 2

# Then copy from WSL2
cp -r "/mnt/c/Users/abhiroop/Documents/NOVA TV/nova-tv" /mnt/wsl/...
```

This is non-trivial. Method A (SSH after first boot) is much simpler.

---

## Step 3 — What the installer does

`sudo bash scripts/install.sh` handles everything:

```
1. Installs OS packages:
   - mpv (video player, supports hw decode on Pi)
   - cec-utils (HDMI-CEC remote support)
   - X11/xinit (minimal display server)
   - SDL2 libraries (for pygame)

2. Creates Python virtualenv at /opt/nova-tv/venv

3. Installs Python packages:
   - pygame  — the UI framework
   - yt-dlp  — YouTube stream extraction

4. Generates icons and artwork

5. Updates yt-dlp to latest (YouTube changes frequently)

6. Installs systemd service (auto-start on boot, restart on crash)
```

---

## Step 4 — Verify it works

```bash
# On the Pi via SSH

# Check service status
systemctl status nova-tv.service

# Watch live logs
journalctl -u nova-tv.service -f

# Run diagnostics
sudo bash /opt/nova-tv/scripts/diagnostics.sh

# Test YouTube manually
yt-dlp --dump-json "ytsearch1:test" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('title'))"
```

---

## Step 5 — Remote control

| Input | Works |
|-------|-------|
| USB keyboard | Always (Arrow keys + Enter + Escape) |
| HDMI-CEC TV remote | If your TV supports CEC — enable in TV settings |
| USB HID remote | Plug in, works as keyboard |
| Bluetooth remote | Pair via `bluetoothctl` first |

Test from a keyboard first. CEC requires your TV to have it enabled
(Samsung: Anynet+, LG: Simplink, Sony: Bravia Sync).

---

## YouTube — how it works

```
User presses SELECT on "YouTube"
    → YouTubeScreen opens
    → User types a search query, presses Enter
    → yt-dlp searches YouTube (background thread, no blocking)
    → Results appear (title, channel, duration, views)
    → User navigates DOWN to a video, presses SELECT
    → yt-dlp resolves the direct stream URL (720p H.264 + AAC)
    → mpv launches fullscreen with hardware decode
    → Video plays natively — no browser, no web
    → User presses Q in mpv to return to NOVA TV
```

Requires internet. yt-dlp must be updated occasionally as YouTube changes
its internal API. Run `yt-dlp -U` to update, or re-run `install.sh`.

---

## Recovery

If NOVA TV fails to start:

```bash
# SSH is always available
ssh pi@<IP>

# Stop the service
sudo systemctl stop nova-tv.service

# Test manually (shows errors in terminal)
cd /opt/nova-tv
sudo /opt/nova-tv/venv/bin/python -m nova.main --dev --log-level DEBUG

# Reset settings
sudo /opt/nova-tv/venv/bin/python -c \
    "from nova.settings.config import ConfigManager; c=ConfigManager(); c.load(); c.reset_to_defaults()"
```

NOVA TV never disables SSH. systemd restarts it on crash (max 5 times per 2
minutes before stopping — prevents boot loops). Ctrl-Alt-F2 opens a rescue TTY.

---

## Updating NOVA TV

```bash
ssh pi@<IP>
sudo systemctl stop nova-tv.service
cd /opt/nova-tv
git pull   # or re-copy from your Windows machine
sudo bash scripts/install.sh   # re-runs safely
sudo systemctl start nova-tv.service
```

---

## File locations on the Pi

| Path | Contents |
|------|----------|
| `/opt/nova-tv/` | NOVA TV source + venv + assets |
| `/opt/nova-tv/config/applications.json` | App catalogue |
| `~/.config/nova-tv/settings.json` | User settings |
| `~/.config/nova-tv/favourites.json` | Favourites |
| `~/.config/nova-tv/recent_errors.json` | Error log |
| `/etc/systemd/system/nova-tv.service` | systemd unit |
