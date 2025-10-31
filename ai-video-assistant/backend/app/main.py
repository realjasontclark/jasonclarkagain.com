"""FastAPI application entrypoint for the AI Video Assistant."""

from __future__ import annotations

import json
from datetime import datetime
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
    ScriptHistoryItem,
    ScriptRequest,
    ScriptResponse,
    ScriptStyle,
    TimelineRequest,
    TimelineResponse,
    VideoAnalysisStatus,
    VideoUploadResponse,
    VoiceProfile,
    VoiceSummary,
    VoiceSynthesisRequest,
)
from sqlmodel import select

from .database import init_db, session_scope
from .models import ScriptRecord, VideoRecord, VoiceRecord
from .services import audio_generation, metadata, script_generation, timeline, transcription, video_analysis, voice_clone
from .utils.file_utils import generate_id, save_upload, secure_filename


app = FastAPI(title="AI Video Content Assistant", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

config.ensure_directories()
init_db()

ANALYSIS_CACHE: Dict[str, VideoAnalysisStatus] = {}

app.mount("/assets", StaticFiles(directory=config.DATA_DIR), name="assets")


def _status_from_record(record: VideoRecord) -> VideoAnalysisStatus:
    result = json.loads(record.result_json) if record.result_json else None
    result_model = AnalysisResult(**result) if result else None
    return VideoAnalysisStatus(
        video_id=record.video_id,
        status=OperationStatus(record.status),
        message=record.message,
        filename=record.filename,
        result=result_model,
    )


def _update_status(video_id: str, status: OperationStatus, message: str | None = None, result: dict | None = None) -> None:
    record: VideoRecord
    with session_scope() as session:
        record = session.get(VideoRecord, video_id)
        if record is None:
            record = VideoRecord(video_id=video_id, filename="", status=status.value)
        record.status = status.value
        record.message = message
        record.result_json = json.dumps(result) if result else None
        record.updated_at = datetime.utcnow()
        session.add(record)

    ANALYSIS_CACHE[video_id] = _status_from_record(record)


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

    with session_scope() as session:
        record = session.get(VideoRecord, video_id)
        if record is None:
            record = VideoRecord(video_id=video_id, filename=filename)
        record.filename = filename
        record.updated_at = datetime.utcnow()
        session.add(record)

    ANALYSIS_CACHE[video_id] = _status_from_record(record)

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
        with session_scope() as session:
            record = session.get(VideoRecord, video_id)
            if not record or record.status == OperationStatus.pending.value and not record.result_json:
                raise HTTPException(status_code=404, detail="No analysis data available")
            status = _status_from_record(record)
            ANALYSIS_CACHE[video_id] = status
    return status


@app.get("/api/videos", response_model=list[VideoAnalysisStatus])
async def list_videos() -> list[VideoAnalysisStatus]:
    statuses: list[VideoAnalysisStatus] = []
    with session_scope() as session:
        statement = select(VideoRecord).order_by(VideoRecord.updated_at.desc())
        records = session.exec(statement).all()
        for record in records:
            try:
                statuses.append(_status_from_record(record))
            except ValueError:
                statuses.append(
                    VideoAnalysisStatus(video_id=record.video_id, status=OperationStatus.pending, message=record.message)
                )
    return statuses


@app.post("/api/scripts", response_model=ScriptResponse)
async def create_script(request: ScriptRequest) -> ScriptResponse:
    status = ANALYSIS_CACHE.get(request.video_id)
    if not status or status.status != OperationStatus.completed:
        raise HTTPException(status_code=400, detail="Analysis must be completed before script generation")

    transcript_text = status.result.transcript if status.result else None
    if not transcript_text:
        raise HTTPException(status_code=500, detail="Transcript missing from analysis result")

    script = script_generation.generate_script(request, transcript_text)
    token_count, est_duration = metadata.estimate_timing(script.script)
    script = script.model_copy(update={"token_count": token_count, "duration_seconds": est_duration})

    with session_scope() as session:
        record = ScriptRecord(
            video_id=request.video_id,
            style=request.style.value,
            script_text=script.script,
            token_count=token_count,
            duration_seconds=est_duration,
            summary=script.summary,
        )
        session.add(record)
        session.flush()
        created_at = record.created_at

    return script.model_copy(update={"created_at": created_at})


@app.get("/api/videos/{video_id}/scripts", response_model=list[ScriptHistoryItem])
async def list_scripts(video_id: str) -> list[ScriptHistoryItem]:
    scripts: list[ScriptHistoryItem] = []
    with session_scope() as session:
        statement = select(ScriptRecord).where(ScriptRecord.video_id == video_id).order_by(ScriptRecord.created_at.desc())
        records = session.exec(statement).all()
        for record in records:
            scripts.append(
                ScriptHistoryItem(
                    video_id=record.video_id,
                    style=ScriptStyle(record.style),
                    script=record.script_text,
                    created_at=record.created_at,
                    token_count=record.token_count,
                    duration_seconds=record.duration_seconds,
                    summary=record.summary,
                )
            )
    return scripts


@app.post("/api/voices", response_model=VoiceProfile)
async def register_voice(
    display_name: str = Form(...),
    sample: UploadFile = File(...),
) -> VoiceProfile:
    temp_path = config.VOICE_PROFILE_DIR / f"tmp_{generate_id('sample')}"
    with temp_path.open("wb") as buffer:
        buffer.write(await sample.read())

    profile = voice_clone.create_voice_profile(display_name, temp_path)
    with session_scope() as session:
        record = session.get(VoiceRecord, profile.voice_id)
        if record is None:
            record = VoiceRecord(
                voice_id=profile.voice_id,
                display_name=display_name,
                sample_path=profile.sample_path,
            )
        else:
            record.display_name = display_name
            record.sample_path = profile.sample_path
        session.add(record)
    return profile


@app.get("/api/voices", response_model=list[VoiceSummary])
async def list_voices() -> list[VoiceSummary]:
    raw_profiles = voice_clone.list_voice_profiles()
    summaries: list[VoiceSummary] = []
    with session_scope() as session:
        for voice_id, data in raw_profiles.items():
            record = session.get(VoiceRecord, voice_id)
            if record is None:
                record = VoiceRecord(
                    voice_id=voice_id,
                    display_name=data.get("display_name", voice_id),
                    sample_path=data.get("sample_path", ""),
                )
                session.add(record)
                session.flush()
            summaries.append(
                VoiceSummary(
                    voice_id=voice_id,
                    display_name=record.display_name,
                    sample_path=record.sample_path,
                    created_at=record.created_at,
                    last_used_at=record.last_used_at,
                    synth_count=record.synth_count,
                )
            )
    return summaries


@app.post("/api/voices/synthesize")
async def synthesize_voice_endpoint(request: VoiceSynthesisRequest) -> Dict[str, str]:
    output_path = voice_clone.synthesize_voice(request.voice_id, request.text, request.speed)
    with session_scope() as session:
        record = session.get(VoiceRecord, request.voice_id)
        if record is None:
            profiles = voice_clone.list_voice_profiles()
            profile_data = profiles.get(request.voice_id, {})
            record = VoiceRecord(
                voice_id=request.voice_id,
                display_name=profile_data.get("display_name", request.voice_id),
                sample_path=profile_data.get("sample_path", ""),
            )
        record.last_used_at = datetime.utcnow()
        record.synth_count = (record.synth_count or 0) + 1
        session.add(record)
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

