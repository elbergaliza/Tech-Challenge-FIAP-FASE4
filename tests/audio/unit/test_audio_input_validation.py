"""Testes de rejeicao de entrada invalida (FR-015)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import AudioPipelineError, AudioProcessingRequest, ErrorCode
from tests.audio.conftest import create_wav_file


def _reports_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(list(path.glob("*.json")))


def test_rejects_corrupted_audio_file(tmp_path: Path) -> None:
    corrupted_file = tmp_path / "corrupted.wav"
    corrupted_file.write_bytes(b"\x00\xFF\x00\xFFinvalid")

    request = AudioProcessingRequest(
        patient_id="sample_001",
        audio_path=corrupted_file,
    )
    reports_dir = tmp_path / "reports"
    processed_dir = tmp_path / "processed"

    with pytest.raises(AudioPipelineError) as captured:
        process_audio_recording(request, output_dir=reports_dir, processed_dir=processed_dir)

    assert captured.value.error_code == ErrorCode.CORRUPTED_AUDIO.value
    assert _reports_count(reports_dir) == 0


def test_rejects_file_too_large(audio_tmp_dir: Path, tmp_path: Path) -> None:
    large_wav = create_wav_file(
        audio_tmp_dir / "large.wav",
        duration_seconds=12.0,
        sample_rate=48_000,
        amplitude=0.2,
    )
    request = AudioProcessingRequest(
        patient_id="sample_002",
        audio_path=large_wav,
        max_size_mb=1,
    )
    reports_dir = tmp_path / "reports"
    processed_dir = tmp_path / "processed"

    with pytest.raises(AudioPipelineError) as captured:
        process_audio_recording(request, output_dir=reports_dir, processed_dir=processed_dir)

    assert captured.value.error_code == ErrorCode.FILE_TOO_LARGE.value
    assert _reports_count(reports_dir) == 0


def test_rejects_duration_too_long(audio_tmp_dir: Path, tmp_path: Path) -> None:
    long_wav = create_wav_file(
        audio_tmp_dir / "too_long.wav",
        duration_seconds=2.2,
        sample_rate=16_000,
        amplitude=0.2,
    )
    request = AudioProcessingRequest(
        patient_id="sample_003",
        audio_path=long_wav,
        max_duration_seconds=1,
    )
    reports_dir = tmp_path / "reports"
    processed_dir = tmp_path / "processed"

    with pytest.raises(AudioPipelineError) as captured:
        process_audio_recording(request, output_dir=reports_dir, processed_dir=processed_dir)

    assert captured.value.error_code == ErrorCode.DURATION_TOO_LONG.value
    assert _reports_count(reports_dir) == 0
