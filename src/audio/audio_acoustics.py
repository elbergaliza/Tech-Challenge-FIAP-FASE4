"""Analise acustica minima para tosse, respiracao e pausas."""

from __future__ import annotations

import math
from pathlib import Path

import librosa
import numpy as np
from pydub import AudioSegment, silence

from src.audio.audio_schemas import AcousticFeatures, AcousticIndicator
from src.audio.audio_scoring import clamp01


def _load_audiosegment(audio_path: Path) -> AudioSegment:
    suffix = audio_path.suffix.lower()
    if suffix == ".wav":
        return AudioSegment.from_wav(audio_path)
    if suffix == ".mp3":
        return AudioSegment.from_mp3(audio_path)
    return AudioSegment.from_file(audio_path)


def _to_mono_float(audio: AudioSegment) -> tuple[np.ndarray, int]:
    samples = np.array(audio.get_array_of_samples(), dtype=np.float64)
    if audio.channels > 1:
        samples = samples.reshape((-1, audio.channels)).mean(axis=1)
    sample_width_bits = audio.sample_width * 8
    max_possible = float((2 ** (sample_width_bits - 1)) - 1)
    if max_possible <= 0:
        return samples, audio.frame_rate
    normalized = samples / max_possible
    return normalized, audio.frame_rate


def _burst_count(signal: np.ndarray, frame_rate: int, frame_ms: int = 200) -> int:
    if signal.size == 0:
        return 0
    frame_size = max(1, int(frame_rate * frame_ms / 1000))
    bursts = 0
    for start in range(0, signal.size, frame_size):
        frame = signal[start : start + frame_size]
        if frame.size == 0:
            continue
        energy = float(np.mean(np.abs(frame)))
        if energy >= 0.2:
            bursts += 1
    return bursts


def analyze_acoustic_features(audio_path: str | Path) -> AcousticFeatures:
    """Extrai sinais acusticos basicos e score heuristico em [0,1]."""

    path = Path(audio_path)
    segment = _load_audiosegment(path)
    signal, frame_rate = _to_mono_float(segment)

    if signal.size == 0:
        return AcousticFeatures(signals=["empty_signal"])

    peak_amplitude = clamp01(float(np.max(np.abs(signal))))
    # librosa.feature.rms espera shape (n,) ou (1, n); aqui usamos shape (1,n) para estabilidade.
    librosa_rms = librosa.feature.rms(y=signal.astype(np.float32))[0]
    rms = float(np.mean(librosa_rms)) if librosa_rms.size else 0.0

    silence_threshold = -40 if math.isinf(segment.dBFS) else segment.dBFS - 16
    silence_ranges = silence.detect_silence(
        segment,
        min_silence_len=500,
        silence_thresh=int(silence_threshold),
    )
    total_silence_ms = sum(end - start for start, end in silence_ranges)
    duration_ms = max(1, len(segment))
    silence_ratio = clamp01(total_silence_ms / duration_ms)
    long_pause_count = sum(1 for start, end in silence_ranges if (end - start) > 1500)

    burst_count = _burst_count(signal, frame_rate)
    if burst_count >= 6:
        indicator = AcousticIndicator.STRONG
    elif burst_count >= 3:
        indicator = AcousticIndicator.POSSIBLE
    else:
        indicator = AcousticIndicator.NONE

    signals: list[str] = []
    score = 0.0
    if silence_ratio > 0.35:
        signals.append("high_silence_ratio")
        score += 0.2
    if long_pause_count >= 3:
        signals.append("long_pauses")
        score += 0.25
    elif long_pause_count > 0:
        signals.append("some_long_pauses")
        score += 0.1
    if indicator == AcousticIndicator.STRONG:
        signals.append("strong_breathing_pattern")
        score += 0.6
    elif indicator == AcousticIndicator.POSSIBLE:
        signals.append("possible_breathing_pattern")
        score += 0.3
    if rms < 0.05:
        signals.append("low_rms")
        score += 0.05

    return AcousticFeatures(
        rms=max(0.0, rms),
        peak_amplitude=peak_amplitude,
        silence_ratio=silence_ratio,
        long_pause_count=long_pause_count,
        cough_or_breathing_indicator=indicator,
        score_acustico=clamp01(score),
        signals=signals,
    )
