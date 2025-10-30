"""FastAPI application entrypoint for the AI Video Assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .schemas import (
    AmbientGenerationRequest,
    AudioMood,
    AnalysisResult,
    MusicGenerationRequest,
    OperationStatus,
    ScriptRequest,
    ScriptResponse,
    TimelineRequest,
    TimelineResponse,
    VideoAnalysisStatus,
    VideoUploadResponse,
    VoiceProfile,
    VoiceSynthesisRequest,
)
from .services import audio_generation, script_generation, timeline, transcription, video_analysis, voice_clone
from .utils.file_utils import generate_id, save_upload, secure_filename


app = FastAPI(title="AI Video Content Assistant", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

config.ensure_directories()

ANALYSIS_CACHE: Dict[str, VideoAnalysisStatus] = {}

app.mount("/assets", StaticFiles(directory=config.DATA_DIR), name="assets")


def _update_status(video_id: str, status: OperationStatus, message: str | None = None, result: dict | None = None) -> None:
    result_model = AnalysisResult(**result) if result else None
    ANALYSIS_CACHE[video_id] = VideoAnalysisStatus(video_id=video_id, status=status, message=message, result=result_model)


def _run_analysis(video_id: str) -> None:
    try:
        _update_status(video_id, OperationStatus.processing, "Analyzing video")
        analysis_payload = video_analysis.analyze_video(video_id)

        transcript_text, transcript_meta = transcription.transcribe(Path(analysis_payload["audio_path"]))
        transcript_path = transcription.save_transcription(analysis_payload["analysis_id"], transcript_text, transcript_meta)

        keywords = sorted({word.lower() for word in transcript_text.split() if len(word) > 5})[:20]
        try:
            summary = script_generation.summarize_transcript(transcript_text)
        except Exception:  # pragma: no cover - summarizer failure should not abort pipeline
            summary = None
        result = {
            "analysis_id": analysis_payload["analysis_id"],
            "metadata": analysis_payload["metadata"],
            "audio_path": analysis_payload["audio_path"],
            "transcript_path": str(transcript_path),
            "scenes": analysis_payload["scenes"],
            "transcript": transcript_text,
            "transcript_meta": transcript_meta,
            "keywords": keywords,
            "summary": summary,
        }

        _update_status(video_id, OperationStatus.completed, result=result)
    except Exception as exc:  # pylint: disable=broad-except
        _update_status(video_id, OperationStatus.failed, message=str(exc))


@app.post("/api/videos", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)) -> VideoUploadResponse:
    filename = secure_filename(file.filename or "upload.mp4")
    video_id = generate_id("video")
    suffix = Path(filename).suffix or ".mp4"
    destination = config.VIDEO_DIR / f"{video_id}{suffix}"

    temp_path = config.VIDEO_DIR / f"tmp_{video_id}"
    with temp_path.open("wb") as buffer:
        content = await file.read()
        buffer.write(content)

    save_upload(temp_path, destination)

    _update_status(video_id, OperationStatus.pending, "Uploaded and awaiting analysis")
    return VideoUploadResponse(video_id=video_id, filename=filename)


@app.post("/api/videos/{video_id}/analyze", response_model=VideoAnalysisStatus)
async def analyze_video_endpoint(video_id: str, background_tasks: BackgroundTasks) -> VideoAnalysisStatus:
    if video_id not in ANALYSIS_CACHE:
        raise HTTPException(status_code=404, detail="Video not found. Upload first.")

    background_tasks.add_task(_run_analysis, video_id)
    return ANALYSIS_CACHE[video_id]


@app.get("/api/videos/{video_id}/analysis", response_model=VideoAnalysisStatus)
async def get_analysis_status(video_id: str) -> VideoAnalysisStatus:
    status = ANALYSIS_CACHE.get(video_id)
    if not status:
        raise HTTPException(status_code=404, detail="No analysis data available")
    return status


@app.post("/api/scripts", response_model=ScriptResponse)
async def create_script(request: ScriptRequest) -> ScriptResponse:
    status = ANALYSIS_CACHE.get(request.video_id)
    if not status or status.status != OperationStatus.completed:
        raise HTTPException(status_code=400, detail="Analysis must be completed before script generation")

    transcript_text = status.result.transcript if status.result else None
    if not transcript_text:
        raise HTTPException(status_code=500, detail="Transcript missing from analysis result")

    script = script_generation.generate_script(request, transcript_text)
    return script


@app.post("/api/voices", response_model=VoiceProfile)
async def register_voice(
    display_name: str = Form(...),
    sample: UploadFile = File(...),
) -> VoiceProfile:
    temp_path = config.VOICE_PROFILE_DIR / f"tmp_{generate_id('sample')}"
    with temp_path.open("wb") as buffer:
        buffer.write(await sample.read())

    profile = voice_clone.create_voice_profile(display_name, temp_path)
    return profile


@app.get("/api/voices")
async def list_voices() -> Dict[str, Dict]:
    return voice_clone.list_voice_profiles()


@app.post("/api/voices/synthesize")
async def synthesize_voice_endpoint(request: VoiceSynthesisRequest) -> Dict[str, str]:
    output_path = voice_clone.synthesize_voice(request.voice_id, request.text, request.speed)
    return {"path": str(output_path)}


@app.post("/api/audio/music")
async def generate_music_endpoint(request: MusicGenerationRequest) -> Dict[str, str]:
    output_path = audio_generation.generate_music(request)
    return {"path": str(output_path)}


@app.post("/api/audio/ambient")
async def generate_ambient_endpoint(request: AmbientGenerationRequest) -> Dict[str, str]:
    output_path = audio_generation.generate_ambient(request)
    return {"path": str(output_path)}


@app.post("/api/timeline", response_model=TimelineResponse)
async def build_timeline_endpoint(request: TimelineRequest) -> TimelineResponse:
    return timeline.build_timeline(request)


@app.get("/api/files")
async def download_file(path: str) -> FileResponse:
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(resolved)

