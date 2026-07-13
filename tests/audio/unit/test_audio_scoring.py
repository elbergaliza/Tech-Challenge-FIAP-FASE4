"""Testes das regras de score e classificação de risco."""

from __future__ import annotations

from src.audio.audio_schemas import (
    AcousticFeatures,
    RiskLevel,
    SentimentLabel,
    TextFindings,
    TranscriptionResult,
    TranscriptionStatus,
)
from src.audio.audio_scoring import apply_textual_effective_score, build_audio_alert


def test_score_textual_floor_with_critical_terms() -> None:
    findings = TextFindings(
        critical_terms=["falta de ar"],
        sentiment=SentimentLabel.NEGATIVE,
        score_textual=0.2,
    )
    updated = apply_textual_effective_score(findings, transcription_confidence=0.1)
    assert updated.score_textual_efetivo == 0.4


def test_conflicting_sources_use_max_rule() -> None:
    findings = TextFindings(sentiment=SentimentLabel.NEUTRAL, score_textual=0.0)
    findings = apply_textual_effective_score(findings, transcription_confidence=1.0)
    alert = build_audio_alert(
        patient_id="sample_001",
        acoustic_features=AcousticFeatures(score_acustico=0.9),
        text_findings=findings,
        transcription_result=TranscriptionResult(status=TranscriptionStatus.NO_SPEECH),
        processing_duration_ms=1200,
        timeout_seconds=60,
    )
    assert alert.score_risco == 0.9
    assert alert.evidencias is not None
    assert alert.evidencias.fontes_risco == ["acustico"]


def test_risk_boundaries_are_deterministic() -> None:
    common = dict(
        patient_id="sample_001",
        acoustic_features=AcousticFeatures(score_acustico=0.0),
        transcription_result=TranscriptionResult(
            status=TranscriptionStatus.SUCCESS,
            confidence=1.0,
        ),
        processing_duration_ms=900,
        timeout_seconds=60,
    )

    low = build_audio_alert(
        text_findings=TextFindings(sentiment=SentimentLabel.NEUTRAL, score_textual=0.0),
        **common,
    )
    moderate = build_audio_alert(
        text_findings=TextFindings(
            critical_terms=["falta de ar"],
            sentiment=SentimentLabel.NEGATIVE,
            score_textual=0.4,
            score_textual_efetivo=0.4,
        ),
        **common,
    )
    high = build_audio_alert(
        text_findings=TextFindings(
            critical_terms=["falta de ar", "dor no peito"],
            sentiment=SentimentLabel.NEGATIVE,
            score_textual=0.8,
            score_textual_efetivo=0.7,
        ),
        **common,
    )

    assert low.nivel_risco == RiskLevel.BAIXO
    assert moderate.nivel_risco == RiskLevel.MODERADO
    assert high.nivel_risco == RiskLevel.ALTO


def test_no_signal_results_in_none_anomaly_and_low_risk() -> None:
    findings = TextFindings(
        sentiment=SentimentLabel.NEUTRAL,
        score_textual=0.0,
        score_textual_efetivo=0.0,
    )
    alert = build_audio_alert(
        patient_id="sample_001",
        acoustic_features=AcousticFeatures(score_acustico=0.0),
        text_findings=findings,
        transcription_result=TranscriptionResult(status=TranscriptionStatus.NO_SPEECH),
        processing_duration_ms=1000,
        timeout_seconds=60,
    )
    assert alert.tipo_anomalia == "nenhuma"
    assert alert.nivel_risco == RiskLevel.BAIXO
