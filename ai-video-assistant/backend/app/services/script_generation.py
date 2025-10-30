"""Script generation from transcripts with style controls."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Dict, List, Tuple

from ..schemas import ScriptRequest, ScriptResponse, ScriptStyle


@lru_cache(maxsize=1)
def _load_summarizer():
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError("transformers is required for summarization") from exc

    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")


STYLE_CONFIG: Dict[ScriptStyle, Dict[str, str]] = {
    ScriptStyle.dry: {
        "intro": "Straight to it: here's what matters.",
        "transition": "No fluff, just facts:",
        "outro": "That's the gist. On to the next one.",
    },
    ScriptStyle.dark_sarcastic: {
        "intro": "Alright, gather 'round for the cheerless truth.",
        "transition": "Let's waltz through the highlights, because joy is overrated:",
        "outro": "There you have it—optimism sold separately.",
    },
    ScriptStyle.laid_back: {
        "intro": "Hey there, let's kick back and dive in.",
        "transition": "Here's the good stuff, no pressure:",
        "outro": "Easy as that. Catch you on the next chill session.",
    },
    ScriptStyle.southern_chill: {
        "intro": "Well hey y'all, let's mosey through this together.",
        "transition": "Here's what caught my eye, nice and easy:",
        "outro": "That'll do it, sugar. Appreciate ya hangin' around.",
    },
    ScriptStyle.energetic: {
        "intro": "Let's go! Here's what's firing me up right now.",
        "transition": "Check these out—fast and furious:",
        "outro": "Boom! That's the energy. Smash that replay if you need it again!",
    },
    ScriptStyle.inspirational: {
        "intro": "Take a breath—this story's about to lift you up.",
        "transition": "Here are the sparks worth holding onto:",
        "outro": "Carry that light forward. Your next step starts now.",
    },
}


def _chunk_transcript(transcript: str, max_words: int = 400) -> List[str]:
    words = transcript.split()
    if len(words) <= max_words:
        return [transcript]

    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        chunks.append(chunk)
    return chunks


def _summarize_text(transcript: str) -> str:
    summarizer = _load_summarizer()
    chunks = _chunk_transcript(transcript)
    summaries = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]["summary_text"]
        summaries.append(summary)
    return " ".join(summaries)


def summarize_transcript(transcript: str) -> str:
    """Public helper to summarize transcript."""

    return _summarize_text(transcript)


def _extract_key_points(text: str, max_points: int) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [sentence.strip() for sentence in sentences if len(sentence.split()) > 4]
    if not sentences:
        return [text]

    return sentences[:max_points]


def _stylize_line(line: str, style: ScriptStyle) -> str:
    if style == ScriptStyle.dark_sarcastic:
        return f"Because of course: {line.lower().capitalize()}"
    if style == ScriptStyle.laid_back:
        return f"Just vibe with this: {line}"
    if style == ScriptStyle.southern_chill:
        return f"Bless your heart, consider this: {line}"
    if style == ScriptStyle.energetic:
        return f"Boom! {line}"
    if style == ScriptStyle.inspirational:
        return f"Let this land: {line}"
    return line


def generate_script(request: ScriptRequest, transcript_text: str) -> ScriptResponse:
    """Generate a styled script from transcript content."""

    minutes = max(request.duration_seconds or 120, 60) / 60
    target_points = max(3, min(8, math.ceil(minutes * 3)))

    try:
        summary = _summarize_text(transcript_text)
    except Exception:  # pragma: no cover - fallback in constrained environments
        summary = transcript_text
    key_points = _extract_key_points(summary, target_points)
    style_config = STYLE_CONFIG.get(request.style, STYLE_CONFIG[ScriptStyle.dry])

    stylized_points = [f"- {_stylize_line(point, request.style)}" for point in key_points]

    extra = f"\nNotes: {request.extra_notes.strip()}" if request.extra_notes else ""

    script_sections = [
        style_config["intro"],
        style_config["transition"],
        "\n".join(stylized_points),
        style_config["outro"],
    ]

    script_text = "\n\n".join(script_sections) + extra

    return ScriptResponse(video_id=request.video_id, style=request.style, script=script_text)

