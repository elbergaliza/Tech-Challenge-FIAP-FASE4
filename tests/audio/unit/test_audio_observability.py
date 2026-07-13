"""Testes de observabilidade e segurança de logs (NFR-002)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import (
    AcousticFeatures,
    AudioPipelineError,
    AudioProcessingRequest,
    SentimentLabel,
    TextFindings,
    TranscriptionResult,
    TranscriptionStatus,
)
from tests.audio.conftest import create_wav_file


def test_observability_logs_include_latency_and_risk(
    monkeypatch: pytest.MonkeyPatch,
    audio_tmp_dir: Path,
    tmp_path: Path,
    caplog,
) -> None:
    wav_path = create_wav_file(audio_tmp_dir / "obs.wav", duration_seconds=1.5, amplitude=0.3)
    monkeypatch.setattr(
        "src.audio.audio_pipeline.transcribe_audio",
        lambda *args, **kwargs: TranscriptionResult(
            text="falta de ar",
            confidence=0.8,
            status=TranscriptionStatus.SUCCESS,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_text_findings",
        lambda *args, **kwargs: TextFindings(
            critical_terms=["falta de ar"],
            sentiment=SentimentLabel.NEGATIVE,
            score_textual=0.7,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_acoustic_features",
        lambda *args, **kwargs: AcousticFeatures(score_acustico=0.3),
    )

    request = AudioProcessingRequest(patient_id="sample_001", audio_path=wav_path)
    caplog.set_level(logging.INFO)
    alert = process_audio_recording(
        request,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
    )

    assert alert.evidencias is not None
    assert alert.evidencias.duracao_processamento_ms is not None

    persisted_records = [r for r in caplog.records if getattr(r, "stage", "") == "persisted"]
    assert persisted_records, "Registro de persistencia nao encontrado."
    persisted = persisted_records[-1]
    assert hasattr(persisted, "duracao_processamento_ms")
    assert hasattr(persisted, "score_risco")

    log_dump = " ".join(
        str(item)
        for record in caplog.records
        for item in record.__dict__.values()
        if isinstance(item, str)
    ).lower()
    assert "falta de ar" not in log_dump
    assert "azure_speech_key" not in log_dump


def test_observability_rejection_is_visible_in_logs(tmp_path: Path, caplog) -> None:
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("invalid", encoding="utf-8")
    request = AudioProcessingRequest.model_construct(
        patient_id="sample_002",
        audio_path=invalid_file,
        language="pt-BR",
        source="unknown",
        max_duration_seconds=600,
        max_size_mb=50,
        timeout_seconds=60,
    )

    caplog.set_level(logging.INFO)
    with pytest.raises(AudioPipelineError):
        process_audio_recording(
            request,
            output_dir=tmp_path / "reports",
            processed_dir=tmp_path / "processed",
        )

    rejected_records = [r for r in caplog.records if getattr(r, "stage", "") == "rejected"]
    assert rejected_records, "Log de rejeicao nao encontrado."
    assert any(
        getattr(record, "error_code", "") == "unsupported_format"
        for record in rejected_records
    )
