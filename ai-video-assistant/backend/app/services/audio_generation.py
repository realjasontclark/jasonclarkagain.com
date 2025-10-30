"""Procedural ambient sound and music generation."""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np

from ..config import GENERATED_AUDIO_DIR
from ..schemas import AmbientGenerationRequest, AmbientType, AudioMood, MusicGenerationRequest
from ..utils.file_utils import generate_id

SAMPLE_RATE = 44100


def _normalize(audio: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(audio))
    if peak < 1e-6:
        return audio
    return 0.95 * audio / peak


def _write_wave(path: Path, audio: np.ndarray) -> None:
    import soundfile as sf

    sf.write(path, audio, SAMPLE_RATE)


def generate_music(request: MusicGenerationRequest) -> Path:
    """Generate a synthetic music bed using simple additive synthesis."""

    duration = request.duration_seconds
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)

    # base tempo and chord progression based on mood
    mood_settings = {
        AudioMood.calm: {
            "tempo": 70,
            "chords": [(261.63, 329.63, 392.00), (293.66, 369.99, 440.00)],
            "wave": "sine",
            "pad": 0.6,
        },
        AudioMood.uplifting: {
            "tempo": 100,
            "chords": [(329.63, 415.30, 493.88), (349.23, 440.00, 523.25)],
            "wave": "saw",
            "pad": 0.7,
        },
        AudioMood.suspense: {
            "tempo": 60,
            "chords": [(196.00, 233.08, 311.13), (207.65, 261.63, 311.13)],
            "wave": "triangle",
            "pad": 0.5,
        },
        AudioMood.energetic: {
            "tempo": 120,
            "chords": [(261.63, 329.63, 392.00), (329.63, 392.00, 493.88)],
            "wave": "saw",
            "pad": 0.8,
        },
        AudioMood.ambient: {
            "tempo": 50,
            "chords": [(174.61, 261.63, 329.63), (196.00, 246.94, 329.63)],
            "wave": "sine",
            "pad": 0.9,
        },
    }

    settings = mood_settings[request.mood]
    beat_duration = 60 / settings["tempo"]
    chord_length = int(4 * beat_duration * SAMPLE_RATE)

    waveform = np.zeros_like(t)
    envelope = np.linspace(0, 1, int(1.5 * SAMPLE_RATE))
    tail = np.linspace(1, 0.2, int(2 * SAMPLE_RATE))

    for idx, chord in enumerate(settings["chords"]):
        start = idx * chord_length
        end = start + chord_length
        if end > len(t):
            end = len(t)
        chord_t = t[start:end]
        base_env = np.ones_like(chord_t)
        base_env[: len(envelope[: len(chord_t)])] *= envelope[: len(chord_t)]
        if len(chord_t) > len(tail):
            base_env[-len(tail) :] *= tail
        else:
            base_env *= np.linspace(1, 0.3, len(chord_t))

        chord_wave = np.zeros_like(chord_t)
        for freq in chord:
            if settings["wave"] == "sine":
                partial = np.sin(2 * np.pi * freq * chord_t)
            elif settings["wave"] == "saw":
                partial = 2 * (chord_t * freq - np.floor(0.5 + chord_t * freq))
            else:  # triangle approximation
                partial = 2 * np.abs(2 * (chord_t * freq - np.floor(chord_t * freq + 0.5))) - 1
            chord_wave += partial
        chord_wave /= len(chord)
        chord_wave *= base_env
        waveform[start:end] += chord_wave

    pad_noise = np.convolve(
        np.random.normal(0, settings["pad"], len(t)),
        np.hanning(2048),
        mode="same",
    )

    result = _normalize(waveform + pad_noise * 0.3)

    output_dir = GENERATED_AUDIO_DIR / "music"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"music_{generate_id('track')}.wav"
    _write_wave(output_path, result)

    return output_path


def _ambient_waveform(request: AmbientGenerationRequest) -> np.ndarray:
    duration = request.duration_seconds
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    intensity = request.intensity

    if request.ambient_type == AmbientType.wind:
        noise = np.random.normal(0, 1, len(t))
        wind = np.convolve(noise, np.hanning(4096), mode="same")
        return wind * intensity * 0.5

    if request.ambient_type == AmbientType.car:
        base = np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 90 * t)
        modulation = 1 + 0.1 * np.sin(2 * np.pi * 1.2 * t)
        return base * modulation * intensity * 0.4

    if request.ambient_type == AmbientType.plane:
        base = np.sin(2 * np.pi * 30 * t) + 0.2 * np.sin(2 * np.pi * 60 * t)
        sweep = np.sin(2 * np.pi * (0.05 * t ** 1.5))
        return (base + sweep) * intensity * 0.5

    if request.ambient_type == AmbientType.footsteps:
        audio = np.zeros_like(t)
        step_interval = max(0.4, 1.2 - intensity)
        current = 0.0
        while current < duration:
            idx = int(current * SAMPLE_RATE)
            burst = np.random.normal(0, 0.6, 1024) * np.hanning(1024)
            end = min(len(audio), idx + len(burst))
            audio[idx:end] += burst[: end - idx]
            current += step_interval
        return audio * 0.5

    if request.ambient_type == AmbientType.train:
        rumble = np.sin(2 * np.pi * 20 * t) + 0.5 * np.sin(2 * np.pi * 40 * t)
        clack = np.zeros_like(t)
        spacing = 0.6
        for offset in np.arange(0, duration, spacing):
            idx = int(offset * SAMPLE_RATE)
            burst = np.random.normal(0, 0.5, 4096) * np.hanning(4096)
            end = min(len(t), idx + len(burst))
            clack[idx:end] += burst[: end - idx]
        return (rumble * 0.3 + clack * 0.7) * intensity * 0.6

    # rain default
    droplets = np.random.exponential(scale=0.4, size=len(t)) - 1
    filtered = np.convolve(droplets, np.hanning(1024), mode="same")
    return filtered * intensity * 0.6


def generate_ambient(request: AmbientGenerationRequest) -> Path:
    waveform = _ambient_waveform(request)
    waveform = _normalize(waveform)

    output_dir = GENERATED_AUDIO_DIR / "ambient"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"ambient_{request.ambient_type.value}_{generate_id('layer')}.wav"
    _write_wave(output_path, waveform)
    return output_path

