"""Testes de latencia e observabilidade de timeout de performance."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import (
    AcousticFeatures,
    AudioProcessingRequest,
    SentimentLabel,
    TextFindings,
    TranscriptionResult,
    TranscriptionStatus,
)
from tests.audio.conftest import create_wav_file


def _stub_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.audio.audio_pipeline.transcribe_audio",
        lambda *args, **kwargs: TranscriptionResult(
            text="sem queixas",
            confidence=0.9,
            status=TranscriptionStatus.SUCCESS,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_text_findings",
        lambda *args, **kwargs: TextFindings(
            sentiment=SentimentLabel.NEUTRAL,
            score_textual=0.0,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_acoustic_features",
        lambda *args, **kwargs: AcousticFeatures(score_acustico=0.0),
    )


def test_latency_within_timeout(
    monkeypatch: pytest.MonkeyPatch,
    audio_tmp_dir: Path,
    tmp_path: Path,
    caplog,
) -> None:
    _stub_dependencies(monkeypatch)
    wav_path = create_wav_file(audio_tmp_dir / "fast.wav")
    request = AudioProcessingRequest(
        patient_id="sample_001",
        audio_path=wav_path,
        timeout_seconds=60,
    )
    times = iter([0.0, 0.2])  # 200 ms
    monkeypatch.setattr("src.audio.audio_pipeline.perf_counter", lambda: next(times))

    caplog.set_level(logging.INFO)
    alert = process_audio_recording(
        request,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
    )

    assert alert.evidencias is not None
    assert alert.evidencias.excedeu_limite_latencia is False
    assert all(
        getattr(record, "status", "") != "performance_timeout" for record in caplog.records
    )


def test_latency_above_timeout_keeps_alert_and_logs_failure(
    monkeypatch: pytest.MonkeyPatch,
    audio_tmp_dir: Path,
    tmp_path: Path,
    caplog,
) -> None:
    _stub_dependencies(monkeypatch)
    wav_path = create_wav_file(audio_tmp_dir / "slow.wav")
    request = AudioProcessingRequest(
        patient_id="sample_002",
        audio_path=wav_path,
        timeout_seconds=1,
    )
    times = iter([0.0, 2.5])  # 2500 ms
    monkeypatch.setattr("src.audio.audio_pipeline.perf_counter", lambda: next(times))

    caplog.set_level(logging.INFO)
    alert = process_audio_recording(
        request,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
    )

    assert alert.evidencias is not None
    assert alert.evidencias.excedeu_limite_latencia is True
    assert any(getattr(record, "status", "") == "performance_timeout" for record in caplog.records)


def test_latency_changes_with_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
    audio_tmp_dir: Path,
    tmp_path: Path,
) -> None:
    _stub_dependencies(monkeypatch)
    wav_path = create_wav_file(audio_tmp_dir / "custom_timeout.wav")
    request = AudioProcessingRequest(
        patient_id="sample_003",
        audio_path=wav_path,
        timeout_seconds=5,
    )
    times = iter([0.0, 3.0])  # 3000 ms
    monkeypatch.setattr("src.audio.audio_pipeline.perf_counter", lambda: next(times))

    alert = process_audio_recording(
        request,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
    )
    assert alert.evidencias is not None
    assert alert.evidencias.excedeu_limite_latencia is False
