"""Regras de score e construcao do alerta final."""

from __future__ import annotations

from src.audio.audio_schemas import (
    AcousticFeatures,
    AudioAlert,
    AudioEvidences,
    RiskLevel,
    RiskSource,
    SentimentLabel,
    TextFindings,
    TranscriptionResult,
    TranscriptionStatus,
)

# Limitação conhecida da versão atual:
# frases com negação como "não sinto falta de ar" ainda contam como termo crítico.
CRITICAL_TERMS: tuple[str, ...] = (
    "falta de ar",
    "dor no peito",
    "cansaço",
    "tontura",
    "piora",
    "dificuldade para respirar",
)


def clamp01(value: float) -> float:
    """Restringe valores numéricos ao intervalo [0.0, 1.0]."""

    return max(0.0, min(1.0, value))


def find_critical_terms(text: str) -> list[str]:
    """Retorna termos críticos distintos encontrados no texto."""

    lowered = text.lower()
    found: list[str] = []
    for term in CRITICAL_TERMS:
        if term in lowered and term not in found:
            found.append(term)
    return found


def score_textual_from_findings(critical_terms: list[str], sentiment: SentimentLabel) -> float:
    """Gera score textual base antes da ponderacao por confianca."""

    if not critical_terms and sentiment in {SentimentLabel.NEUTRAL, SentimentLabel.POSITIVE}:
        return 0.0

    terms_score = min(0.8, len(critical_terms) * 0.3)
    sentiment_boost = {
        SentimentLabel.NEGATIVE: 0.2,
        SentimentLabel.MIXED: 0.2,
        SentimentLabel.NEUTRAL: 0.0,
        SentimentLabel.POSITIVE: 0.0,
        SentimentLabel.UNKNOWN: 0.0,
    }[sentiment]
    return clamp01(terms_score + sentiment_boost)


def apply_textual_effective_score(
    text_findings: TextFindings,
    transcription_confidence: float,
) -> TextFindings:
    """Aplica FR-003 com piso quando há ao menos um termo crítico."""

    confidence = clamp01(transcription_confidence)
    base = clamp01(text_findings.score_textual)
    if text_findings.critical_terms:
        effective = max(base * confidence, 0.4)
    else:
        effective = base * confidence
    return text_findings.model_copy(
        update={"score_textual": base, "score_textual_efetivo": clamp01(effective)},
    )


def classify_risk(score_risco: float) -> RiskLevel:
    """Classifica o nível de risco com os limiares da spec."""

    if score_risco >= 0.7:
        return RiskLevel.ALTO
    if score_risco >= 0.4:
        return RiskLevel.MODERADO
    return RiskLevel.BAIXO


def _sources(
    acoustic_score: float,
    textual_effective_score: float,
    transcription_status: TranscriptionStatus,
) -> list[RiskSource]:
    output: list[RiskSource] = []
    if acoustic_score > 0.0:
        output.append(RiskSource.ACUSTICO)
    if textual_effective_score > 0.0:
        output.append(RiskSource.TEXTO)
    if transcription_status == TranscriptionStatus.LOW_CONFIDENCE:
        output.append(RiskSource.TRANSCRICAO_BAIXA_CONFIANCA)
    return output


def _tipo_anomalia(
    acoustic_score: float,
    textual_effective_score: float,
    transcription_status: TranscriptionStatus,
) -> str:
    if acoustic_score == 0.0 and textual_effective_score == 0.0:
        return "nenhuma"
    if acoustic_score > 0.0 and textual_effective_score > 0.0:
        return "alteracao_respiratoria_vocal"
    if textual_effective_score > 0.0:
        return "termos_criticos"
    if acoustic_score > 0.0:
        return "sinais_acusticos"
    if transcription_status == TranscriptionStatus.LOW_CONFIDENCE:
        return "baixa_confianca_transcricao"
    return "nenhuma"


def _descricao(
    acoustic_score: float,
    textual_effective_score: float,
    transcription_status: TranscriptionStatus,
    nivel: RiskLevel,
) -> str:
    if acoustic_score == 0.0 and textual_effective_score == 0.0:
        return "Sem sinais relevantes no audio e no texto transcrito."

    if acoustic_score >= textual_effective_score:
        source_description = "sinais acusticos"
    else:
        source_description = "termos/sentimento do texto transcrito"

    if transcription_status == TranscriptionStatus.LOW_CONFIDENCE:
        source_description += " com baixa confianca de transcricao"

    return f"Risco {nivel.value} definido principalmente por {source_description}."


def _recomendacao(nivel: RiskLevel) -> str:
    if nivel == RiskLevel.ALTO:
        return "Encaminhar para avaliacao respiratoria imediata."
    if nivel == RiskLevel.MODERADO:
        return "Reavaliar paciente e manter monitoramento clinico."
    return "Manter acompanhamento e repetir coleta se necessario."


def build_audio_alert(
    *,
    patient_id: str,
    acoustic_features: AcousticFeatures,
    text_findings: TextFindings,
    transcription_result: TranscriptionResult,
    processing_duration_ms: float,
    timeout_seconds: int,
) -> AudioAlert:
    """Combina sinais de risco e monta o contrato final do alerta."""

    score_acustico = clamp01(acoustic_features.score_acustico)
    score_textual = clamp01(text_findings.score_textual)
    score_textual_efetivo = clamp01(text_findings.score_textual_efetivo)
    score_risco = clamp01(max(score_acustico, score_textual_efetivo))
    nivel = classify_risk(score_risco)
    sources = _sources(score_acustico, score_textual_efetivo, transcription_result.status)

    evidencias = AudioEvidences(
        score_acustico=score_acustico,
        score_textual=score_textual,
        score_textual_efetivo=score_textual_efetivo,
        confianca_transcricao=clamp01(transcription_result.confidence),
        fontes_risco=sources,
        status_transcricao=transcription_result.status,
        duracao_processamento_ms=max(0.0, processing_duration_ms),
        excedeu_limite_latencia=processing_duration_ms > timeout_seconds * 1000,
    )

    return AudioAlert(
        patient_id=patient_id,
        tipo_anomalia=_tipo_anomalia(
            score_acustico,
            score_textual_efetivo,
            transcription_result.status,
        ),
        score_risco=score_risco,
        nivel_risco=nivel,
        descricao=_descricao(
            score_acustico,
            score_textual_efetivo,
            transcription_result.status,
            nivel,
        ),
        recomendacao=_recomendacao(nivel),
        evidencias=evidencias,
    )
