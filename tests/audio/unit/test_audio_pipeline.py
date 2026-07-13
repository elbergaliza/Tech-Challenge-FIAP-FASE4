"""Testes unitarios da orquestracao do pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import (
    AcousticFeatures,
    AudioPipelineError,
    AudioProcessingRequest,
    ErrorCode,
    RiskLevel,
    SentimentLabel,
    TextFindings,
    TranscriptionResult,
    TranscriptionStatus,
)
from tests.audio.conftest import create_wav_file


def _request_for(path: Path, **overrides: object) -> AudioProcessingRequest:
    payload = {
        "patient_id": "sample_001",
        "audio_path": str(path),
        "language": "pt-BR",
        "max_duration_seconds": 600,
        "max_size_mb": 50,
        "timeout_seconds": 60,
    }
    payload.update(overrides)
    return AudioProcessingRequest.model_validate(payload)


def test_pipeline_critical_terms_generates_high_alert(
    monkeypatch: pytest.MonkeyPatch,
    audio_tmp_dir: Path,
    tmp_path: Path,
) -> None:
    wav_path = create_wav_file(audio_tmp_dir / "critical.wav", duration_seconds=1.5, amplitude=0.3)
    monkeypatch.setattr(
        "src.audio.audio_pipeline.transcribe_audio",
        lambda *args, **kwargs: TranscriptionResult(
            text="falta de ar e dor no peito",
            confidence=0.95,
            status=TranscriptionStatus.SUCCESS,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_text_findings",
        lambda *args, **kwargs: TextFindings(
            critical_terms=["falta de ar", "dor no peito"],
            sentiment=SentimentLabel.NEGATIVE,
            score_textual=0.9,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_acoustic_features",
        lambda *args, **kwargs: AcousticFeatures(score_acustico=0.2),
    )

    request = _request_for(wav_path)
    alert = process_audio_recording(
        request,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
    )

    assert alert.nivel_risco == RiskLevel.ALTO
    assert alert.score_risco >= 0.7


def test_pipeline_no_speech_falls_back_to_acoustics(
    monkeypatch: pytest.MonkeyPatch,
    audio_tmp_dir: Path,
    tmp_path: Path,
) -> None:
    wav_path = create_wav_file(audio_tmp_dir / "no_speech.wav", duration_seconds=1.2, amplitude=0.2)
    monkeypatch.setattr(
        "src.audio.audio_pipeline.transcribe_audio",
        lambda *args, **kwargs: TranscriptionResult(
            text="",
            confidence=0.0,
            status=TranscriptionStatus.NO_SPEECH,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_acoustic_features",
        lambda *args, **kwargs: AcousticFeatures(score_acustico=0.65),
    )

    request = _request_for(wav_path)
    alert = process_audio_recording(
        request,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
    )

    assert alert.score_risco == 0.65
    assert alert.nivel_risco == RiskLevel.MODERADO
    assert alert.tipo_anomalia in {"sinais_acusticos", "alteracao_respiratoria_vocal"}


def test_pipeline_rejects_empty_patient_id(audio_tmp_dir: Path, tmp_path: Path) -> None:
    wav_path = create_wav_file(audio_tmp_dir / "empty_patient.wav")
    request = AudioProcessingRequest.model_construct(
        patient_id="   ",
        audio_path=wav_path,
        language="pt-BR",
        source="unknown",
        max_duration_seconds=600,
        max_size_mb=50,
        timeout_seconds=60,
    )

    with pytest.raises(AudioPipelineError) as captured:
        process_audio_recording(
            request,
            output_dir=tmp_path / "reports",
            processed_dir=tmp_path / "processed",
        )
    assert captured.value.error_code == ErrorCode.INVALID_PATIENT_ID.value


def test_pipeline_rejects_unsupported_format(tmp_path: Path) -> None:
    file_path = tmp_path / "invalid.txt"
    file_path.write_text("invalid", encoding="utf-8")
    request = AudioProcessingRequest.model_construct(
        patient_id="sample_001",
        audio_path=file_path,
        language="pt-BR",
        source="unknown",
        max_duration_seconds=600,
        max_size_mb=50,
        timeout_seconds=60,
    )

    with pytest.raises(AudioPipelineError) as captured:
        process_audio_recording(
            request,
            output_dir=tmp_path / "reports",
            processed_dir=tmp_path / "processed",
        )
    assert captured.value.error_code == ErrorCode.UNSUPPORTED_FORMAT.value


def test_pipeline_conflicting_signals_prioritizes_acoustic_source(
    monkeypatch: pytest.MonkeyPatch,
    audio_tmp_dir: Path,
    tmp_path: Path,
) -> None:
    wav_path = create_wav_file(audio_tmp_dir / "conflict.wav", duration_seconds=1.0, amplitude=0.3)
    monkeypatch.setattr(
        "src.audio.audio_pipeline.transcribe_audio",
        lambda *args, **kwargs: TranscriptionResult(
            text="",
            confidence=0.0,
            status=TranscriptionStatus.NO_SPEECH,
        ),
    )
    monkeypatch.setattr(
        "src.audio.audio_pipeline.analyze_acoustic_features",
        lambda *args, **kwargs: AcousticFeatures(score_acustico=0.9),
    )

    request = _request_for(wav_path)
    alert = process_audio_recording(
        request,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
    )

    assert alert.score_risco == 0.9
    assert "acusticos" in alert.descricao
