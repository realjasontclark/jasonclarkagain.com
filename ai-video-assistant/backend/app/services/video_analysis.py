"""Video analysis services: metadata, audio extraction, scene detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..config import ANALYSIS_DIR, VIDEO_DIR
from ..utils.file_utils import generate_id


def extract_metadata(video_path: Path) -> Dict:
    """Extract basic metadata from a video using MoviePy."""

    try:
        from moviepy.editor import VideoFileClip
    except ImportError as exc:
        raise RuntimeError("moviepy is required for metadata extraction") from exc

    with VideoFileClip(str(video_path)) as clip:
        return {
            "duration": clip.duration,
            "fps": clip.fps,
            "width": clip.size[0],
            "height": clip.size[1],
            "audio": clip.audio is not None,
        }


def extract_audio(video_path: Path, destination: Path) -> Path:
    """Extract the audio track as WAV."""

    try:
        from moviepy.editor import VideoFileClip
    except ImportError as exc:
        raise RuntimeError("moviepy is required for audio extraction") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    with VideoFileClip(str(video_path)) as clip:
        if clip.audio is None:
            raise ValueError("Video does not contain an audio track")
        clip.audio.write_audiofile(str(destination), fps=16000, nbytes=2, codec="pcm_s16le")

    return destination


def detect_scenes(video_path: Path, threshold: float = 27.0) -> List[dict]:
    """Detect scene boundaries using PySceneDetect."""

    try:
        from scenedetect import SceneManager
        from scenedetect.detectors import ContentDetector
        from scenedetect.backends.opencv import VideoCapture
    except ImportError as exc:
        raise RuntimeError("PySceneDetect is required for scene detection") from exc

    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))

    capture = VideoCapture(str(video_path))
    manager.detect_scenes(frame_source=capture)
    scene_list = manager.get_scene_list()

    scenes: List[dict] = []
    for idx, (start, end) in enumerate(scene_list, start=1):
        scenes.append(
            {
                "scene_id": idx,
                "start_time": start.get_seconds(),
                "end_time": end.get_seconds(),
                "duration": end.get_seconds() - start.get_seconds(),
            }
        )

    return scenes


def analyze_video(video_id: str) -> Dict:
    """Run end-to-end analysis for a stored video."""

    video_path = VIDEO_DIR / f"{video_id}.mp4"
    if not video_path.exists():
        # fall back to any extension
        matches = list(VIDEO_DIR.glob(f"{video_id}.*"))
        if not matches:
            raise FileNotFoundError(f"Video {video_id} not found")
        video_path = matches[0]

    analysis_id = generate_id("analysis")
    output_dir = ANALYSIS_DIR / analysis_id
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = extract_metadata(video_path)
    audio_path = output_dir / "audio.wav"
    extract_audio(video_path, audio_path)
    scenes = detect_scenes(video_path)

    # Persist metadata for reuse by other services
    metadata_path = output_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "video_id": video_id,
                "video_path": str(video_path),
                "metadata": metadata,
                "audio_path": str(audio_path),
                "scenes": scenes,
            },
            f,
            indent=2,
        )

    return {
        "analysis_id": analysis_id,
        "video_path": str(video_path),
        "metadata": metadata,
        "audio_path": str(audio_path),
        "scenes": scenes,
    }

