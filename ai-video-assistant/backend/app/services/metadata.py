"""Helpers for computing derived metadata such as token counts."""

from __future__ import annotations

from typing import Tuple


def estimate_timing(script: str, words_per_minute: int = 150) -> Tuple[int, int]:
    """Return estimated token count and duration in seconds."""

    words = script.split()
    word_count = len(words)
    token_estimate = int(word_count * 1.3)
    minutes = word_count / words_per_minute
    duration_seconds = max(30, int(minutes * 60)) if word_count else 0
    return token_estimate, duration_seconds
