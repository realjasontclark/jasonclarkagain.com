"""Pydantic data models for API inputs and outputs."""

from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OperationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VideoUploadResponse(BaseModel):
    video_id: str = Field(..., description="Identifier for the uploaded video")
    filename: str = Field(..., description="Original filename")


class AnalysisResult(BaseModel):
    analysis_id: Optional[str] = None
    metadata: Optional[dict] = None
    audio_path: Optional[str] = None
    transcript_path: Optional[str] = Field(None, description="Path to transcript file")
    transcript: Optional[str] = None
    transcript_meta: Optional[dict] = None
    scenes: List[dict] = Field(default_factory=list, description="Scene boundary information")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    summary: Optional[str] = Field(None, description="High-level summary of the video")


class VideoAnalysisStatus(BaseModel):
    video_id: str
    status: OperationStatus
    message: Optional[str] = None
    filename: Optional[str] = None
    result: Optional[AnalysisResult] = None


class ScriptStyle(str, Enum):
    dry = "dry"
    dark_sarcastic = "dark_sarcastic"
    laid_back = "laid_back"
    southern_chill = "southern_chill"
    energetic = "energetic"
    inspirational = "inspirational"


class ScriptRequest(BaseModel):
    video_id: str = Field(..., description="Video to generate script for")
    style: ScriptStyle = Field(ScriptStyle.dry, description="Delivery style")
    duration_seconds: Optional[int] = Field(120, description="Target script duration")
    extra_notes: Optional[str] = Field(None, description="Additional guidance")


class ScriptResponse(BaseModel):
    video_id: str
    style: ScriptStyle
    script: str
    created_at: datetime
    token_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    summary: Optional[str] = None


class ScriptHistoryItem(BaseModel):
    video_id: str
    style: ScriptStyle
    script: str
    created_at: datetime
    token_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    summary: Optional[str] = None


class VoiceProfile(BaseModel):
    voice_id: str
    display_name: str
    sample_path: str


class VoiceCloneRequest(BaseModel):
    display_name: str = Field(..., description="Human-friendly name for the voice")


class VoiceSynthesisRequest(BaseModel):
    voice_id: str
    text: str
    speed: float = Field(1.0, ge=0.5, le=1.5)


class AudioMood(str, Enum):
    calm = "calm"
    uplifting = "uplifting"
    suspense = "suspense"
    energetic = "energetic"
    ambient = "ambient"


class MusicGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of desired track")
    mood: AudioMood = AudioMood.calm
    duration_seconds: int = Field(30, ge=5, le=300)


class AmbientType(str, Enum):
    wind = "wind"
    car = "car"
    plane = "plane"
    footsteps = "footsteps"
    train = "train"
    rain = "rain"


class AmbientGenerationRequest(BaseModel):
    ambient_type: AmbientType
    intensity: float = Field(0.7, ge=0.1, le=1.0)
    duration_seconds: int = Field(20, ge=5, le=300)


class TimelineItem(BaseModel):
    asset_type: str
    path: str
    start: float
    duration: float
    metadata: dict = Field(default_factory=dict)


class TimelineRequest(BaseModel):
    video_id: str
    narration_path: str
    music_path: Optional[str] = None
    ambient_paths: List[str] = Field(default_factory=list)
    beat_alignment: bool = Field(True, description="Align narration beats to detected scene changes")
    bundle_assets: bool = Field(False, description="If true, export a zip bundle with timeline + audio assets")


class TimelineResponse(BaseModel):
    video_id: str
    items: List[TimelineItem]
    export_path: str
    bundle_path: Optional[str] = None

