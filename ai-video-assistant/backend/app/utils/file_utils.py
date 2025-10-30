"""Filesystem utility helpers."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Tuple


def generate_id(prefix: str) -> str:
    """Generate a short UUID with a prefix."""

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def secure_filename(filename: str) -> str:
    """Return a filesystem-safe filename."""

    safe = "".join(char for char in filename if char.isalnum() or char in {".", "_", "-"})
    return safe or uuid.uuid4().hex


def save_upload(temp_path: Path, destination: Path) -> None:
    """Move uploaded file to destination, creating directories as needed."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(temp_path), str(destination))


def ensure_wave_format(path: Path) -> Tuple[Path, bool]:
    """Convert audio file to WAV 16kHz mono if necessary.

    Returns tuple of (converted_path, created_new_file).
    """

    path = path.resolve()
    if path.suffix.lower() == ".wav":
        return path, False

    try:
        import soundfile as sf
        import librosa
    except ImportError as exc:
        raise RuntimeError("librosa and soundfile are required for audio conversion") from exc

    audio, sr = librosa.load(path, sr=16000, mono=True)
    wav_path = path.with_suffix(".wav")
    sf.write(wav_path, audio, sr)
    return wav_path, True

