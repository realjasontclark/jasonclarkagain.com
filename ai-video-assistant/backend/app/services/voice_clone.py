"""Voice cloning and speech synthesis using open-source TTS."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

import numpy as np

from ..config import GENERATED_AUDIO_DIR, VOICE_PROFILE_DIR
from ..schemas import VoiceProfile
from ..utils.file_utils import ensure_wave_format, generate_id


PROFILES_INDEX = VOICE_PROFILE_DIR / "profiles.json"


@lru_cache(maxsize=1)
def _load_tts_model():
    try:
        from TTS.api import TTS
    except ImportError as exc:
        raise RuntimeError("coqui-ai TTS library is required for voice cloning") from exc

    return TTS(model_name="tts_models/multilingual/multi-dataset/your_tts")


def _load_profiles() -> Dict[str, Dict]:
    if not PROFILES_INDEX.exists():
        return {}
    with PROFILES_INDEX.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def _save_profiles(profiles: Dict[str, Dict]) -> None:
    VOICE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with PROFILES_INDEX.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)


def create_voice_profile(display_name: str, sample_path: Path) -> VoiceProfile:
    """Create a voice profile from an uploaded audio sample."""

    wav_path, created = ensure_wave_format(sample_path)
    model = _load_tts_model()

    embedding = model.compute_embedding(str(wav_path))
    voice_id = generate_id("voice")

    embedding_path = VOICE_PROFILE_DIR / f"{voice_id}.npy"
    np.save(embedding_path, embedding)

    profiles = _load_profiles()
    profiles[voice_id] = {
        "voice_id": voice_id,
        "display_name": display_name,
        "sample_path": str(wav_path),
        "embedding_path": str(embedding_path),
    }
    _save_profiles(profiles)

    if created:
        sample_path.unlink(missing_ok=True)

    return VoiceProfile(voice_id=voice_id, display_name=display_name, sample_path=str(wav_path))


def list_voice_profiles() -> Dict[str, Dict]:
    return _load_profiles()


def synthesize_voice(voice_id: str, text: str, speed: float = 1.0) -> Path:
    """Generate speech audio using a stored voice embedding."""

    profiles = _load_profiles()
    if voice_id not in profiles:
        raise KeyError(f"Voice {voice_id} not found")

    profile = profiles[voice_id]
    embedding_path = Path(profile["embedding_path"])
    if not embedding_path.exists():
        raise FileNotFoundError("Voice embedding file is missing")

    embedding = np.load(embedding_path)

    model = _load_tts_model()
    output_dir = GENERATED_AUDIO_DIR / "narration"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{voice_id}_{generate_id('take')}.wav"

    model.tts_to_file(
        text=text,
        file_path=str(output_path),
        speaker_embeddings=embedding,
        speed=speed,
    )

    return output_path

