"""
NOVA TV — YouTube integration via yt-dlp + mpv.

No browser. No web scraping. yt-dlp extracts the direct stream URL,
mpv plays it natively. This works on Raspberry Pi 3B+.

Architecture:
  - YouTubeSearch: runs yt-dlp --dump-json in a background thread.
    Returns a list of VideoResult dataclasses.
  - YouTubePlayer: resolves the best stream URL and launches mpv.
  - All network and subprocess work is async — the UI never blocks.

Prerequisites (installed by install.sh on the Pi):
    pip install yt-dlp
    sudo apt install mpv

yt-dlp quality selection for Pi 3B+:
  - Prefer 720p or lower — 1080p is too heavy for software decode.
  - Format selector: bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/
                     best[height<=720][ext=mp4]/best[height<=720]/best
  - On Pi 4 you can raise to 1080p.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional

log = logging.getLogger(__name__)

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class VideoResult:
    """One search result from yt-dlp."""
    id: str
    title: str
    channel: str = ""
    duration_str: str = ""
    duration_secs: int = 0
    view_count: int = 0
    thumbnail_url: str = ""
    url: str = ""           # full YouTube URL
    description: str = ""

    @property
    def display_duration(self) -> str:
        if self.duration_secs <= 0:
            return ""
        m, s = divmod(self.duration_secs, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    @property
    def display_views(self) -> str:
        if self.view_count <= 0:
            return ""
        if self.view_count >= 1_000_000:
            return f"{self.view_count / 1_000_000:.1f}M views"
        if self.view_count >= 1_000:
            return f"{self.view_count // 1_000}K views"
        return f"{self.view_count} views"


# ── yt-dlp availability ───────────────────────────────────────────────────────

def ytdlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def ytdlp_version() -> str:
    if not ytdlp_available():
        return "not installed"
    try:
        r = subprocess.run(["yt-dlp", "--version"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception:
        return "unknown"


# ── Format selector ────────────────────────────────────────────────────────────

# Prefer H.264 + AAC at 720p or lower for Pi 3B+ hardware compatibility.
# mpv with hardware decode (--hwdec=v4l2m2m) can handle 720p H.264 well.
_FORMAT_SELECTOR = (
    "bestvideo[height<=720][vcodec^=avc]+bestaudio[acodec=mp4a]"
    "/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]"
    "/best[height<=720][ext=mp4]"
    "/best[height<=720]"
    "/best"
)


# ── Search ────────────────────────────────────────────────────────────────────

class YouTubeSearch:
    """
    Asynchronous YouTube search using yt-dlp.

    Searches run on a background thread. The UI polls ``is_searching``
    and reads ``results`` when done.
    """

    def __init__(self, max_results: int = 20):
        self._max = max_results
        self._results: List[VideoResult] = []
        self._searching = False
        self._error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._on_done: Optional[Callable] = None
        self._last_query: str = ""

    @property
    def results(self) -> List[VideoResult]:
        return list(self._results)

    @property
    def is_searching(self) -> bool:
        return self._searching

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def last_query(self) -> str:
        return self._last_query

    def search(self, query: str, on_done: Optional[Callable] = None) -> None:
        """Start an async search. Safe to call while another is running (cancels it)."""
        if not query.strip():
            return
        if self._searching:
            log.debug("Cancelling previous search")
        self._last_query = query
        self._error = None
        self._results = []
        self._on_done = on_done
        self._searching = True
        self._thread = threading.Thread(
            target=self._worker, args=(query,), daemon=True, name="yt-search"
        )
        self._thread.start()

    def _worker(self, query: str) -> None:
        try:
            if not ytdlp_available():
                self._error = "yt-dlp not installed. Run: pip install yt-dlp"
                return

            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-playlist",
                "--flat-playlist",
                f"ytsearch{self._max}:{query}",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                self._error = f"yt-dlp error: {proc.stderr.strip()[:200]}"
                return

            results: List[VideoResult] = []
            for line in proc.stdout.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    vid_id = d.get("id", "")
                    if not vid_id:
                        continue
                    results.append(VideoResult(
                        id=vid_id,
                        title=d.get("title", "Unknown"),
                        channel=d.get("channel") or d.get("uploader") or "",
                        duration_secs=int(d.get("duration") or 0),
                        view_count=int(d.get("view_count") or 0),
                        thumbnail_url=d.get("thumbnail") or "",
                        url=d.get("url") or d.get("webpage_url")
                            or f"https://www.youtube.com/watch?v={vid_id}",
                        description=(d.get("description") or "")[:200],
                    ))
                except (json.JSONDecodeError, ValueError):
                    continue

            self._results = results
            log.info("YouTube search '%s': %d results", query, len(results))

        except subprocess.TimeoutExpired:
            self._error = "Search timed out. Check internet connection."
        except Exception as exc:
            self._error = str(exc)
            log.exception("YouTube search failed")
        finally:
            self._searching = False
            if self._on_done:
                try:
                    self._on_done()
                except Exception:
                    pass


# ── Player ───────────────────────────────────────────────────────────────────

class YouTubePlayer:
    """
    Resolve and play a YouTube video with mpv.

    Uses yt-dlp to get the direct stream URL then passes it to mpv.
    mpv is run with flags appropriate for Pi 3B+ hardware.
    """

    # mpv flags for Raspberry Pi 3B+ (adjust in settings if needed)
    _MPV_FLAGS_PI = [
        "--fullscreen",
        "--no-terminal",
        "--no-osc",
        "--hwdec=v4l2m2m",    # Pi hardware decode
        "--gpu-context=drm",   # direct rendering (no X needed in prod)
        "--ytdl=no",           # we pass the URL directly, don't re-invoke yt-dlp
    ]

    # mpv flags for development (no hardware decode)
    _MPV_FLAGS_DEV = [
        "--fullscreen",
        "--no-terminal",
        "--ytdl=no",
    ]

    def __init__(self, dev_mode: bool = False):
        self._dev = dev_mode
        self._proc: Optional[subprocess.Popen] = None
        self._current_url: str = ""
        self._resolving = False
        self._resolve_thread: Optional[threading.Thread] = None
        self._error: Optional[str] = None
        self._on_exit: Optional[Callable] = None

    @property
    def is_playing(self) -> bool:
        if self._proc is None:
            return False
        if self._proc.poll() is not None:
            log.info("mpv exited (code %d)", self._proc.returncode)
            self._proc = None
            self._current_url = ""
            if self._on_exit:
                try:
                    self._on_exit()
                except Exception:
                    pass
            return False
        return True

    @property
    def is_resolving(self) -> bool:
        return self._resolving

    @property
    def error(self) -> Optional[str]:
        return self._error

    def play(self, video: VideoResult, on_exit: Optional[Callable] = None) -> None:
        """
        Resolve the stream URL and start mpv asynchronously.
        """
        if self.is_playing:
            self.stop()
        self._error = None
        self._on_exit = on_exit
        self._resolving = True
        t = threading.Thread(
            target=self._resolve_and_play,
            args=(video.url,),
            daemon=True, name="yt-resolve"
        )
        t.start()

    def _resolve_and_play(self, url: str) -> None:
        try:
            if not ytdlp_available():
                self._error = "yt-dlp not installed"
                return
            if not shutil.which("mpv"):
                self._error = "mpv not installed"
                return

            # Get the direct stream URL
            cmd = [
                "yt-dlp",
                "--get-url",
                "--format", _FORMAT_SELECTOR,
                url,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if proc.returncode != 0:
                self._error = f"Could not resolve video: {proc.stderr.strip()[:200]}"
                return

            stream_urls = [u for u in proc.stdout.strip().splitlines() if u.strip()]
            if not stream_urls:
                self._error = "No playable stream found"
                return

            flags = self._MPV_FLAGS_DEV if self._dev else self._MPV_FLAGS_PI
            # For merged video+audio we get two URLs; pass both to mpv
            if len(stream_urls) == 2:
                video_url, audio_url = stream_urls
                cmd_mpv = ["mpv"] + flags + [
                    video_url,
                    f"--audio-file={audio_url}",
                ]
            else:
                cmd_mpv = ["mpv"] + flags + [stream_urls[0]]

            log.info("Launching mpv for %s", url)
            self._proc = subprocess.Popen(
                cmd_mpv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._current_url = url

        except subprocess.TimeoutExpired:
            self._error = "Timed out resolving stream URL"
        except Exception as exc:
            self._error = str(exc)
            log.exception("YouTube play failed")
        finally:
            self._resolving = False

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self._current_url = ""

    def mpv_available(self) -> bool:
        return shutil.which("mpv") is not None
