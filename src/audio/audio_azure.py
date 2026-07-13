"""Adaptadores da Camada A com Azure Speech e Text Analytics."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

from src.audio.audio_schemas import (
    AudioPipelineError,
    ErrorCode,
    SentimentLabel,
    TextFindings,
    TranscriptionResult,
    TranscriptionStatus,
)
from src.audio.audio_scoring import clamp01, find_critical_terms, score_textual_from_findings

LOGGER = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise AudioPipelineError(
            ErrorCode.MISSING_AZURE_CONFIGURATION,
            f"Variavel de ambiente obrigatoria ausente: {name}",
        )
    return value


def _normalize_confidence(raw_value: float | int | None) -> float:
    if raw_value is None:
        return 0.0
    value = float(raw_value)
    if value > 1.0:
        value = value / 100.0
    return clamp01(value)


def _extract_confidence_from_payload(payload: str | None) -> float:
    if not payload:
        return 0.0
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return 0.0
    nbest = decoded.get("NBest", [])
    if not nbest:
        return 0.0
    return _normalize_confidence(nbest[0].get("Confidence"))


def transcribe_audio(
    audio_path: str | Path,
    *,
    language: str = "pt-BR",
    confidence_threshold: float = 0.45,
) -> TranscriptionResult:
    """Transcreve um arquivo usando Azure Speech to Text."""

    load_dotenv()
    speech_key = _require_env("AZURE_SPEECH_KEY")
    speech_region = _require_env("AZURE_SPEECH_REGION")

    import azure.cognitiveservices.speech as speechsdk

    try:
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        speech_config.speech_recognition_language = language
        speech_config.output_format = speechsdk.OutputFormat.Detailed

        audio_config = speechsdk.audio.AudioConfig(filename=str(audio_path))
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )
        result = recognizer.recognize_once()
    except AudioPipelineError:
        raise
    except Exception:
        LOGGER.exception("audio_azure_speech_failed_to_execute")
        return TranscriptionResult(status=TranscriptionStatus.FAILED)

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        confidence = _extract_confidence_from_payload(
            result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        )
        status = (
            TranscriptionStatus.SUCCESS
            if confidence >= confidence_threshold
            else TranscriptionStatus.LOW_CONFIDENCE
        )
        transcription = TranscriptionResult(
            text=result.text or "",
            confidence=confidence,
            language=language,
            status=status,
        )
    elif result.reason == speechsdk.ResultReason.NoMatch:
        transcription = TranscriptionResult(
            text="",
            confidence=0.0,
            language=language,
            status=TranscriptionStatus.NO_SPEECH,
        )
    else:
        transcription = TranscriptionResult(
            text="",
            confidence=0.0,
            language=language,
            status=TranscriptionStatus.FAILED,
        )

    LOGGER.info(
        "audio_azure_transcription_done",
        extra={
            "status": transcription.status.value,
            "confidence": transcription.confidence,
        },
    )
    return transcription


def _text_client() -> TextAnalyticsClient:
    load_dotenv()
    endpoint = _require_env("AZURE_TEXT_ANALYTICS_ENDPOINT")
    key = _require_env("AZURE_TEXT_ANALYTICS_KEY")
    return TextAnalyticsClient(endpoint=endpoint, credential=AzureKeyCredential(key))


def _sentiment_label(value: str | None) -> SentimentLabel:
    if value == "positive":
        return SentimentLabel.POSITIVE
    if value == "neutral":
        return SentimentLabel.NEUTRAL
    if value == "negative":
        return SentimentLabel.NEGATIVE
    if value == "mixed":
        return SentimentLabel.MIXED
    return SentimentLabel.UNKNOWN


def _sentiment_confidence(document: Any, sentiment: SentimentLabel) -> float | None:
    confidence_scores = getattr(document, "confidence_scores", None)
    if confidence_scores is None:
        return None
    if sentiment == SentimentLabel.POSITIVE:
        return _normalize_confidence(getattr(confidence_scores, "positive", None))
    if sentiment == SentimentLabel.NEUTRAL:
        return _normalize_confidence(getattr(confidence_scores, "neutral", None))
    if sentiment in {SentimentLabel.NEGATIVE, SentimentLabel.MIXED}:
        return _normalize_confidence(getattr(confidence_scores, "negative", None))
    return None


def analyze_text_findings(
    text: str,
    *,
    language: str = "pt-BR",
    client: TextAnalyticsClient | None = None,
) -> TextFindings:
    """Extrai termos criticos e sentimento a partir da transcricao."""

    clean_text = text.strip()
    if not clean_text:
        return TextFindings(sentiment=SentimentLabel.UNKNOWN)

    text_client = client or _text_client()
    try:
        sentiment_result = text_client.analyze_sentiment([clean_text], language=language)[0]
        sentiment_label = _sentiment_label(getattr(sentiment_result, "sentiment", None))
        sentiment_confidence = _sentiment_confidence(sentiment_result, sentiment_label)

        key_phrases_result = text_client.extract_key_phrases([clean_text], language=language)[0]
        key_phrases = getattr(key_phrases_result, "key_phrases", []) or []

        searchable_text = " ".join([clean_text, *key_phrases])
        critical_terms = find_critical_terms(searchable_text)
        score_textual = score_textual_from_findings(critical_terms, sentiment_label)
    except AudioPipelineError:
        raise
    except Exception:
        LOGGER.exception("audio_azure_text_analytics_failed")
        return TextFindings(sentiment=SentimentLabel.UNKNOWN)

    result = TextFindings(
        critical_terms=critical_terms,
        sentiment=sentiment_label,
        sentiment_confidence=sentiment_confidence,
        score_textual=score_textual,
        score_textual_efetivo=0.0,
    )
    LOGGER.info(
        "audio_azure_text_findings_done",
        extra={
            "critical_terms_count": len(result.critical_terms),
            "sentiment": result.sentiment.value,
            "score_textual": result.score_textual,
        },
    )
    return result
