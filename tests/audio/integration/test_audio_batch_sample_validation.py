"""Validação por amostragem para SC-006 (baixo falso alarme)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import (
    AcousticFeatures,
    AudioProcessingRequest,
    RiskLevel,
    TranscriptionResult,
    TranscriptionStatus,
)
from tests.audio.conftest import create_wav_file


def test_batch_known_non_risk_samples_are_mostly_low(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Amostra sintética de 10 arquivos sem queixas textuais e sem sinal acústico de risco.
    sample_dir = tmp_path / "batch"
    reports_dir = tmp_path / "reports"
    processed_dir = tmp_path / "processed"
    sample_dir.mkdir(parents=True, exist_ok=True)

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
        lambda *args, **kwargs: AcousticFeatures(score_acustico=0.0),
    )

    low_and_none_count = 0
    total = 10
    for index in range(total):
        wav_path = create_wav_file(
            sample_dir / f"healthy_{index:02d}.wav",
            duration_seconds=1.0,
            amplitude=0.2,
        )
        request = AudioProcessingRequest(
            patient_id=f"healthy_{index:02d}",
            audio_path=wav_path,
            timeout_seconds=30,
        )
        alert = process_audio_recording(
            request,
            output_dir=reports_dir,
            processed_dir=processed_dir,
        )
        if alert.nivel_risco == RiskLevel.BAIXO and alert.tipo_anomalia == "nenhuma":
            low_and_none_count += 1

    ratio = low_and_none_count / total
    assert ratio >= 0.9
