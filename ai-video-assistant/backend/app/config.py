"""Application configuration constants and helpers."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VIDEO_DIR = DATA_DIR / "videos"
ANALYSIS_DIR = DATA_DIR / "analysis"
VOICE_PROFILE_DIR = DATA_DIR / "voices"
GENERATED_AUDIO_DIR = DATA_DIR / "generated_audio"
DB_PATH = DATA_DIR / "app.db"


def ensure_directories() -> None:
    """Ensure all runtime directories exist."""

    for directory in [DATA_DIR, VIDEO_DIR, ANALYSIS_DIR, VOICE_PROFILE_DIR, GENERATED_AUDIO_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

