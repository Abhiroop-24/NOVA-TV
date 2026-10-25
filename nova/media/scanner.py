"""
NOVA TV — Local media scanner and player.

Scans configured directories for video and audio files asynchronously.
Launches playback through an external player (mpv by default).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


@dataclass
class MediaFile:
    """Represents a discovered media file."""
    path: str
    filename: str
    extension: str
    size_bytes: int = 0
    is_video: bool = True
    thumbnail_path: Optional[str] = None
    last_played: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Human-readable name without extension."""
        return os.path.splitext(self.filename)[0]

    @property
    def size_display(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.2f} GB"


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".flv"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".wav", ".aac", ".m4a", ".wma", ".opus"}


class MediaScanner:
    """
    Asynchronous media directory scanner.

    Scans happen on a background thread so the UI never blocks.
    The UI polls ``is_scanning`` and reads ``files`` when done.
    """

    def __init__(
        self,
        directories: Optional[List[str]] = None,
        extensions: Optional[List[str]] = None,
    ):
        self._directories = directories or []
        self._extensions = set(extensions or [])
        if not self._extensions:
            self._extensions = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

        self._files: List[MediaFile] = []
        self._scanning = False
        self._scan_thread: Optional[threading.Thread] = None
        self._scan_error: Optional[str] = None
        self._last_scan_time: float = 0

    @property
    def files(self) -> List[MediaFile]:
        return list(self._files)

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    @property
    def scan_error(self) -> Optional[str]:
        return self._scan_error

    @property
    def video_files(self) -> List[MediaFile]:
        return [f for f in self._files if f.is_video]

    @property
    def audio_files(self) -> List[MediaFile]:
        return [f for f in self._files if not f.is_video]

    def set_directories(self, dirs: List[str]) -> None:
        self._directories = dirs

    # ── Scanning ────────────────────────────────────────────────────────────

    def scan_async(self) -> None:
        """Start a background scan.  Safe to call multiple times."""
        if self._scanning:
            log.debug("Scan already in progress")
            return
        self._scan_error = None
        self._scanning = True
        self._scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self._scan_thread.start()

    def _scan_worker(self) -> None:
        found: List[MediaFile] = []
        try:
            for directory in self._directories:
                if not os.path.isdir(directory):
                    log.debug("Media dir not found: %s", directory)
                    continue
                for root, _dirs, filenames in os.walk(directory):
                    for fname in filenames:
                        ext = os.path.splitext(fname)[1].lower()
                        if ext not in self._extensions:
                            continue
                        full_path = os.path.join(root, fname)
                        try:
                            size = os.path.getsize(full_path)
                        except OSError:
                            size = 0

                        is_video = ext in VIDEO_EXTENSIONS
                        mf = MediaFile(
                            path=full_path,
                            filename=fname,
                            extension=ext,
                            size_bytes=size,
                            is_video=is_video,
                        )

                        # Look for thumbnail next to the file
                        for thumb_ext in (".jpg", ".png"):
                            thumb = os.path.splitext(full_path)[0] + thumb_ext
                            if os.path.isfile(thumb):
                                mf.thumbnail_path = thumb
                                break

                        found.append(mf)
                        # Yield CPU periodically
                        if len(found) % 100 == 0:
                            time.sleep(0.01)

            found.sort(key=lambda f: f.filename.lower())
            self._files = found
            self._last_scan_time = time.monotonic()
            log.info("Media scan complete: %d files found", len(found))

        except Exception as exc:
            self._scan_error = str(exc)
            log.error("Media scan failed: %s", exc)
        finally:
            self._scanning = False


class MediaPlayer:
    """
    Launches an external media player for a given file.

    Tracks the running player process so NOVA TV can detect when
    playback ends and re-display the interface.
    """

    def __init__(self, player_command: str = "mpv"):
        self._player_cmd = player_command
        self._proc: Optional[subprocess.Popen] = None
        self._current_file: Optional[str] = None

    @property
    def is_playing(self) -> bool:
        if self._proc is None:
            return False
        if self._proc.poll() is not None:
            self._proc = None
            self._current_file = None
            return False
        return True

    @property
    def current_file(self) -> Optional[str]:
        return self._current_file if self.is_playing else None

    def player_available(self) -> bool:
        """Check if the configured player is installed."""
        return shutil.which(self._player_cmd) is not None

    def play(self, file_path: str) -> Tuple[bool, str]:
        """
        Start playback of a file.

        Returns (success, error_message).
        """
        if not os.path.isfile(file_path):
            return False, f"File not found: {file_path}"

        if not self.player_available():
            return False, f"Player '{self._player_cmd}' not installed"

        if self.is_playing:
            self.stop()

        try:
            cmd = [self._player_cmd]
            if self._player_cmd in ("mpv",):
                cmd += ["--fullscreen", "--no-terminal"]
            cmd.append(file_path)

            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._current_file = file_path
            log.info("Playing: %s", file_path)
            return True, ""
        except Exception as exc:
            msg = f"Playback failed: {exc}"
            log.error(msg)
            return False, msg

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self._current_file = None

    def set_player(self, command: str) -> None:
        self._player_cmd = command
