"""
NOVA TV — Media scanner tests.

Creates a temp directory with known files and verifies the async scanner
finds them, ignores unsupported files, sets video/audio flags, and locates
sidecar thumbnails.  Uses a short poll loop because scanning is threaded.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from nova.media.scanner import MediaScanner, MediaFile, MediaPlayer


def _wait_for_scan(scanner, timeout=5.0):
    deadline = time.monotonic() + timeout
    while scanner.is_scanning and time.monotonic() < deadline:
        time.sleep(0.01)
    return not scanner.is_scanning


def test_scan_finds_media(tmp_path):
    # Create files of assorted types
    (tmp_path / "movie1.mp4").write_bytes(b"x")
    (tmp_path / "song.mp3").write_bytes(b"x")
    (tmp_path / "clip.mkv").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")  # ignored
    (tmp_path / "image.png").write_bytes(b"x")  # ignored

    scanner = MediaScanner(directories=[str(tmp_path)])
    scanner.scan_async()
    assert _wait_for_scan(scanner)
    files = scanner.files
    names = {f.filename for f in files}
    assert names == {"movie1.mp4", "song.mp3", "clip.mkv"}
    assert scanner.scan_error is None


def test_video_vs_audio_flag(tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"x")
    (tmp_path / "a.flac").write_bytes(b"x")
    scanner = MediaScanner(directories=[str(tmp_path)])
    scanner.scan_async()
    _wait_for_scan(scanner)
    by_name = {f.filename: f for f in scanner.files}
    assert by_name["v.mp4"].is_video is True
    assert by_name["a.flac"].is_video is False


def test_sidecar_thumbnail_detected(tmp_path):
    (tmp_path / "vid.mp4").write_bytes(b"x")
    (tmp_path / "vid.jpg").write_bytes(b"x")
    scanner = MediaScanner(directories=[str(tmp_path)])
    scanner.scan_async()
    _wait_for_scan(scanner)
    f = next(f for f in scanner.files if f.filename == "vid.mp4")
    assert f.thumbnail_path is not None
    assert f.thumbnail_path.endswith("vid.jpg")


def test_missing_directory_skipped(tmp_path):
    scanner = MediaScanner(directories=[str(tmp_path / "nope")])
    scanner.scan_async()
    _wait_for_scan(scanner)
    assert scanner.files == []
    assert scanner.scan_error is None  # missing dir is not a hard error


def test_size_display():
    f = MediaFile(path="x", filename="x", extension=".mp4", size_bytes=1024 * 1024)
    assert "MB" in f.size_display
    f2 = MediaFile(path="y", filename="y", extension=".mp4", size_bytes=500)
    assert "B" in f2.size_display


def test_display_name_strips_extension():
    f = MediaFile(path="x", filename="My.Movie.2023.mp4", extension=".mp4")
    assert f.display_name == "My.Movie.2023"


def test_player_available_flag(tmp_path):
    # mpv may or may not be installed; just ensure the method is safe to call
    p = MediaPlayer(player_command="mpv")
    assert isinstance(p.player_available(), bool)
    # An obviously-missing command
    p2 = MediaPlayer(player_command="definitely_not_a_real_player_xyz")
    assert p2.player_available() is False


def test_player_missing_file_fails(tmp_path):
    p = MediaPlayer(player_command="mpv")
    ok, err = p.play(str(tmp_path / "ghost.mp4"))
    assert ok is False
    assert "not found" in err.lower()
