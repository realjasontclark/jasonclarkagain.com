# Creator Forge · AI Video Companion

Prototype web app fueled by open-source AI tooling to accelerate social-video production. Upload raw footage, run on-device analysis, spin up styled scripts, clone voices for narration, synthesize background beds, and export alignment metadata for editors like YouCut.

## Stack

- **Backend**: FastAPI, MoviePy, PySceneDetect, Faster-Whisper, HuggingFace Transformers, Coqui TTS, procedural audio synthesis, SQLModel (SQLite persistence).
- **Frontend**: Vite + React + TypeScript.
- **Storage**: Local filesystem under `backend/app/data/` (videos, analyses, voices, generated audio).

## Getting Started

```bash
# backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend (new shell)
cd frontend
npm install
npm run dev
```

Frontend dev server proxies API calls to `http://localhost:8000`.

## Core Pipeline

1. **Upload** video saved into `data/videos/`.
2. **Analyze** via MoviePy metadata, PySceneDetect scene cuts, Faster-Whisper transcription, keyword extraction, summary.
3. **Script Studio** builds tone-aware scripts (dry, dark sarcastic, laid back, southern chill, energetic, inspirational) with optional notes, estimated runtime, and token counts.
4. **Script Archive** keeps every generated draft in SQLite with timestamps for quick recall/reuse from the UI.
5. **Voice Forge** registers custom voices using Coqui TTS embeddings; synthesizes narration from scripts.
6. **Audio Atmospherics** crafts procedural background music and ambience layers (wind, car, plane, footsteps, train, rain).
7. **Timeline Export** bundles a JSON timeline referencing assets for manual import to YouCut (drag assets, align per metadata) with optional zip package of narration/music/ambient layers and persists job history in SQLite.

## Open-Source Models & Assets

- **Speech-to-text**: `faster-whisper` (`base` model by default).
- **Summarization**: `sshleifer/distilbart-cnn-12-6`.
- **Voice cloning / TTS**: `tts_models/multilingual/multi-dataset/your_tts`.
- **Procedural audio**: deterministic synthesis in `audio_generation.py` (no external API).

### Optional Commercial Upgrades

Swap modules in `services/` layer to tap into premium APIs:

| Capability | Budget-Friendly Upgrade | Notes |
|------------|--------------------------|-------|
| Script Writing | OpenAI GPT-4o mini, Anthropic Claude Haiku | Higher coherence + style depth |
| Voice Cloning | ElevenLabs VoiceLab, Resemble AI | Fast training, studio quality |
| Music/SFX | Stable Audio, Soundful, Aiva | Diverse tracks, loop controls |
| Transcription | Deepgram Nova-2, AssemblyAI | Streaming + diarization |

Configuration hints live alongside each service for clear swap points.

## Project Structure

```text
backend/
  app/
    config.py           # runtime paths
    main.py             # FastAPI routes
    schemas.py          # pydantic models
    services/
      video_analysis.py
      transcription.py
      script_generation.py
      voice_clone.py
      audio_generation.py
      timeline.py
    utils/
      file_utils.py
frontend/
  src/
    App.tsx             # main UI workflow
    hooks/useApi.ts     # axios client
    components/Card.tsx
    styles/global.css
```

## Roadmap Ideas

- Background task queue for heavy jobs (Celery + Redis).
- Persistent DB for analyses & presets (SQLite/SQLModel).
- Inline waveform preview and scrubbing.
- Fine-grained script editor with scene anchors.
- Automated YouCut project archive (pending API exposure).

## License

Prototype delivered for private evaluation. Review licensing of bundled OSS models before commercial rollout.
