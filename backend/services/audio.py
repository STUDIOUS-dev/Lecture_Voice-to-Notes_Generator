"""
Audio helpers built on the ffmpeg / ffprobe command-line tools.

Used to read durations and to shrink uploads before sending them to a hosted
transcription API (which typically caps files at ~25 MB). Speech survives
16 kHz mono 32 kbps MP3 with no meaningful loss in recognition accuracy,
so a 1-hour lecture becomes ~14 MB.
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Windows convenience: allow a bundled ffmpeg.exe in the project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if (_PROJECT_ROOT / "ffmpeg.exe").is_file():
    os.environ["PATH"] = str(_PROJECT_ROOT) + os.pathsep + os.environ.get("PATH", "")


class AudioError(RuntimeError):
    """Raised when an audio file cannot be decoded."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=1800)
    except FileNotFoundError as exc:
        raise AudioError("ffmpeg is not installed on the server.") from exc
    except subprocess.CalledProcessError as exc:
        logger.error("ffmpeg failed: %s", exc.stderr[-2000:] if exc.stderr else exc)
        raise AudioError("The audio file could not be decoded. Is it a valid audio file?") from exc


def get_duration(path: Path) -> float | None:
    """Return the audio duration in seconds, or None if unknown."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = _run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(path),
        ]).stdout
        return round(float(json.loads(out)["format"]["duration"]), 2)
    except (AudioError, KeyError, ValueError, TypeError):
        return None


def compress_for_speech(src: Path, dest: Path) -> Path:
    """Re-encode to 16 kHz mono 32 kbps MP3 (small, speech-friendly)."""
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k", str(dest),
    ])
    return dest


def split_audio(src: Path, out_dir: Path, segment_seconds: int) -> list[Path]:
    """Split audio into consecutive chunks of `segment_seconds` each."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "chunk_%03d.mp3"
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
        "-f", "segment", "-segment_time", str(segment_seconds), "-c", "copy", str(pattern),
    ])
    return sorted(out_dir.glob("chunk_*.mp3"))
