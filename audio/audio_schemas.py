"""Schemas e contratos do modulo de audio_texto."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ErrorCode(StrEnum):
    """Codigos estaveis de erro do pipeline."""

    INVALID_PATIENT_ID = "invalid_patient_id"
    UNSUPPORTED_FORMAT = "unsupported_format"
    FILE_NOT_FOUND = "file_not_found"
    FILE_TOO_LARGE = "file_too_large"
    DURATION_TOO_LONG = "duration_too_long"
    CORRUPTED_AUDIO = "corrupted_audio"
    MISSING_AZURE_CONFIGURATION = "missing_azure_configuration"


class AudioPipelineError(Exception):
    """Erro de dominio com codigo estavel para CLI e testes."""

    def __init__(self, error_code: ErrorCode | str, message: str) -> None:
        self.error_code = str(error_code)
        super().__init__(message)


class AudioSource(StrEnum):
    """Fonte da amostra processada."""

    PT_BR_DEMO = "pt_br_demo"
    COSWARA = "coswara"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class TranscriptionStatus(StrEnum):
    """Status da transcricao da Camada A."""

    SUCCESS = "success"
    NO_SPEECH = "no_speech"
    LOW_CONFIDENCE = "low_confidence"
    FAILED = "failed"


class AcousticIndicator(StrEnum):
    """Indicador heuristico para tosse/respiracao."""

    NONE = "none"
    POSSIBLE = "possible"
    STRONG = "strong"


class SentimentLabel(StrEnum):
    """Sentimento retornado pelo provedor de texto."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    """Faixa final de risco do alerta."""

    BAIXO = "baixo"
    MODERADO = "moderado"
    ALTO = "alto"


class RiskSource(StrEnum):
    """Fonte que contribuiu para o score final."""

    ACUSTICO = "acustico"
    TEXTO = "texto"
    TRANSCRICAO_BAIXA_CONFIANCA = "transcricao_baixa_confianca"


class AudioProcessingRequest(BaseModel):
    """Entrada validada para processar uma gravacao."""

    model_config = ConfigDict(extra="forbid")

    patient_id: str = Field(min_length=1)
    audio_path: Path
    language: Literal["pt-BR", "en-US", "en-GB"] = "pt-BR"
    source: AudioSource = AudioSource.UNKNOWN
    max_duration_seconds: int = Field(default=600, gt=0, le=600)
    max_size_mb: int = Field(default=50, gt=0, le=50)
    timeout_seconds: int = Field(default=60, gt=0)

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise AudioPipelineError(ErrorCode.INVALID_PATIENT_ID, "patient_id nao pode ser vazio.")
        return cleaned


class AudioMetadata(BaseModel):
    """Metadados tecnicos da gravacao."""

    model_config = ConfigDict(extra="forbid")

    duration_seconds: float = Field(gt=0)
    size_mb: float = Field(gt=0)
    format: Literal["wav", "mp3"]
    sample_rate_hz: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, ge=1)


class TranscriptionResult(BaseModel):
    """Resultado de transcricao do Azure Speech."""

    model_config = ConfigDict(extra="forbid")

    text: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    language: str = "pt-BR"
    provider: str = "azure_speech_to_text"
    status: TranscriptionStatus = TranscriptionStatus.NO_SPEECH


class AcousticFeatures(BaseModel):
    """Features acusticas minimas para sinais nao textuais."""

    model_config = ConfigDict(extra="forbid")

    rms: float | None = Field(default=None, ge=0.0)
    peak_amplitude: float | None = Field(default=None, ge=0.0, le=1.0)
    silence_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    long_pause_count: int = Field(ge=0, default=0)
    cough_or_breathing_indicator: AcousticIndicator = AcousticIndicator.NONE
    score_acustico: float = Field(ge=0.0, le=1.0, default=0.0)
    signals: list[str] = Field(default_factory=list)


class TextFindings(BaseModel):
    """Achados textuais derivados da transcricao."""

    model_config = ConfigDict(extra="forbid")

    critical_terms: list[str] = Field(default_factory=list)
    sentiment: SentimentLabel = SentimentLabel.UNKNOWN
    sentiment_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    score_textual: float = Field(ge=0.0, le=1.0, default=0.0)
    score_textual_efetivo: float = Field(ge=0.0, le=1.0, default=0.0)


class AudioEvidences(BaseModel):
    """Objeto de evidencias para rastreabilidade."""

    model_config = ConfigDict(extra="forbid")

    score_acustico: float | None = Field(default=None, ge=0.0, le=1.0)
    score_textual: float | None = Field(default=None, ge=0.0, le=1.0)
    score_textual_efetivo: float | None = Field(default=None, ge=0.0, le=1.0)
    confianca_transcricao: float | None = Field(default=None, ge=0.0, le=1.0)
    fontes_risco: list[RiskSource] = Field(default_factory=list)
    status_transcricao: TranscriptionStatus | None = None
    duracao_processamento_ms: float | None = Field(default=None, ge=0.0)
    excedeu_limite_latencia: bool | None = None


class AudioAlert(BaseModel):
    """Contrato publico final do modulo `audio_texto`."""

    model_config = ConfigDict(extra="forbid")

    patient_id: str = Field(min_length=1)
    modulo: Literal["audio_texto"] = "audio_texto"
    tipo_anomalia: str = Field(min_length=1)
    score_risco: float = Field(ge=0.0, le=1.0)
    nivel_risco: RiskLevel
    descricao: str = Field(min_length=1)
    recomendacao: str = Field(min_length=1)
    evidencias: AudioEvidences | None = None

    @model_validator(mode="after")
    def validate_risk_level(self) -> AudioAlert:
        if self.score_risco < 0.4 and self.nivel_risco != RiskLevel.BAIXO:
            raise ValueError("nivel_risco deve ser 'baixo' quando score_risco < 0.4")
        if 0.4 <= self.score_risco < 0.7 and self.nivel_risco != RiskLevel.MODERADO:
            raise ValueError("nivel_risco deve ser 'moderado' quando 0.4 <= score_risco < 0.7")
        if self.score_risco >= 0.7 and self.nivel_risco != RiskLevel.ALTO:
            raise ValueError("nivel_risco deve ser 'alto' quando score_risco >= 0.7")
        return self
