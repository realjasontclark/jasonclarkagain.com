"""Audio transcription using open-source Whisper models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from functools import lru_cache

from ..config import ANALYSIS_DIR


@lru_cache(maxsize=1)
def _load_model(model_size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is required for transcription") from exc

    return WhisperModel(model_size, device="auto", compute_type="int8_float16")


def transcribe(audio_path: Path, model_size: str = "base") -> Tuple[str, Dict]:
    """Transcribe audio using Faster-Whisper.

    Returns transcript text and metadata dict.
    """

    model = _load_model(model_size)

    segments, info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)

    transcript_lines = []
    structured_segments = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        transcript_lines.append(text)
        structured_segments.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": text,
            }
        )

    transcript_text = " ".join(transcript_lines)
    metadata = {
        "language": info.language,
        "duration": info.duration,
        "segments": structured_segments,
    }

    return transcript_text, metadata


def save_transcription(analysis_id: str, transcript_text: str, metadata: Dict) -> Path:
    """Persist transcription to disk and return path."""

    analysis_dir = ANALYSIS_DIR / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = analysis_dir / "transcript.txt"
    with transcript_path.open("w", encoding="utf-8") as f:
        f.write(transcript_text)

    json_path = analysis_dir / "transcript.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return transcript_path

