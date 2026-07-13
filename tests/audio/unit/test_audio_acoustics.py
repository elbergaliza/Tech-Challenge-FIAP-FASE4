"""Testes da analise acustica minima."""

from __future__ import annotations

from pathlib import Path

from src.audio.audio_acoustics import analyze_acoustic_features
from src.audio.audio_schemas import AcousticIndicator
from tests.audio.conftest import create_wav_file


def test_acoustic_features_detect_strong_breathing_pattern(audio_tmp_dir: Path) -> None:
    wav_path = create_wav_file(
        audio_tmp_dir / "burst.wav",
        duration_seconds=2.0,
        amplitude=0.3,
        include_bursts=True,
    )
    features = analyze_acoustic_features(wav_path)
    assert features.cough_or_breathing_indicator == AcousticIndicator.STRONG
    assert features.score_acustico >= 0.5


def test_acoustic_features_detect_long_pauses(audio_tmp_dir: Path) -> None:
    wav_path = create_wav_file(
        audio_tmp_dir / "pauses.wav",
        duration_seconds=12.0,
        amplitude=0.2,
        include_long_pauses=True,
    )
    features = analyze_acoustic_features(wav_path)
    assert features.long_pause_count >= 3
    assert features.score_acustico > 0.0


def test_acoustic_features_clean_audio_returns_zero_score(audio_tmp_dir: Path) -> None:
    wav_path = create_wav_file(
        audio_tmp_dir / "clean.wav",
        duration_seconds=2.0,
        amplitude=0.2,
    )
    features = analyze_acoustic_features(wav_path)
    assert features.score_acustico == 0.0
    assert features.cough_or_breathing_indicator == AcousticIndicator.NONE


def test_acoustic_features_numeric_invariants(audio_tmp_dir: Path) -> None:
    wav_path = create_wav_file(
        audio_tmp_dir / "invariants.wav",
        duration_seconds=1.5,
        amplitude=0.4,
    )
    features = analyze_acoustic_features(wav_path)
    assert 0.0 <= features.score_acustico <= 1.0
    assert features.peak_amplitude is not None
    assert 0.0 <= features.peak_amplitude <= 1.0
    assert features.silence_ratio is not None
    assert 0.0 <= features.silence_ratio <= 1.0
