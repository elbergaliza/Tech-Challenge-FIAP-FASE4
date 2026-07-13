"""Testes dos adaptadores Azure (Speech + Text Analytics)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from src.audio.audio_azure import analyze_text_findings, transcribe_audio
from src.audio.audio_schemas import SentimentLabel, TranscriptionStatus


@dataclass
class _FakeSpeechResult:
    reason: str
    text: str = ""
    properties: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.properties is None:
            self.properties = {}


def _install_fake_speech_sdk(monkeypatch: pytest.MonkeyPatch, result_or_error: Any) -> None:
    class ResultReason:
        RecognizedSpeech = "recognized"
        NoMatch = "no_match"
        Canceled = "canceled"

    class OutputFormat:
        Detailed = "detailed"

    class PropertyId:
        SpeechServiceResponse_JsonResult = "json_result"

    class SpeechConfig:
        def __init__(self, subscription: str, region: str) -> None:
            self.subscription = subscription
            self.region = region
            self.speech_recognition_language = "pt-BR"
            self.output_format = None

    class AudioConfig:
        def __init__(self, filename: str) -> None:
            self.filename = filename

    class SpeechRecognizer:
        def __init__(self, speech_config: Any, audio_config: Any) -> None:
            self.speech_config = speech_config
            self.audio_config = audio_config

        def recognize_once(self) -> _FakeSpeechResult:
            if isinstance(result_or_error, Exception):
                raise result_or_error
            return result_or_error

    fake_module = SimpleNamespace(
        ResultReason=ResultReason,
        OutputFormat=OutputFormat,
        PropertyId=PropertyId,
        SpeechConfig=SpeechConfig,
        SpeechRecognizer=SpeechRecognizer,
        audio=SimpleNamespace(AudioConfig=AudioConfig),
    )
    azure_module = ModuleType("azure")
    cognitive_module = ModuleType("azure.cognitiveservices")
    cognitive_module.speech = fake_module
    azure_module.cognitiveservices = cognitive_module

    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices", cognitive_module)
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices.speech", fake_module)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "brazilsouth")


def test_transcribe_audio_success_status(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    result = _FakeSpeechResult(
        reason="recognized",
        text="falta de ar",
        properties={"json_result": '{"NBest":[{"Confidence":0.91}]}'},
    )
    _install_fake_speech_sdk(monkeypatch, result)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake-audio")

    transcription = transcribe_audio(audio_path)
    assert transcription.status == TranscriptionStatus.SUCCESS
    assert transcription.confidence == 0.91


def test_transcribe_audio_low_confidence(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    result = _FakeSpeechResult(
        reason="recognized",
        text="fala pouco clara",
        properties={"json_result": '{"NBest":[{"Confidence":0.10}]}'},
    )
    _install_fake_speech_sdk(monkeypatch, result)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake-audio")

    transcription = transcribe_audio(audio_path)
    assert transcription.status == TranscriptionStatus.LOW_CONFIDENCE
    assert transcription.confidence == 0.10


def test_transcribe_audio_no_speech(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    result = _FakeSpeechResult(reason="no_match", text="", properties={})
    _install_fake_speech_sdk(monkeypatch, result)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake-audio")

    transcription = transcribe_audio(audio_path)
    assert transcription.status == TranscriptionStatus.NO_SPEECH
    assert transcription.confidence == 0.0


def test_transcribe_audio_service_failure(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _install_fake_speech_sdk(monkeypatch, RuntimeError("azure unavailable"))

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake-audio")

    transcription = transcribe_audio(audio_path)
    assert transcription.status == TranscriptionStatus.FAILED
    assert transcription.confidence == 0.0


def test_transcribe_audio_normalizes_alternative_scale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    result = _FakeSpeechResult(
        reason="recognized",
        text="fala teste",
        properties={"json_result": '{"NBest":[{"Confidence":82}]}'},
    )
    _install_fake_speech_sdk(monkeypatch, result)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake-audio")

    transcription = transcribe_audio(audio_path)
    assert transcription.confidence == 0.82


class _FakeSentimentDoc:
    def __init__(self, sentiment: str, negative_score: float = 0.9) -> None:
        self.sentiment = sentiment
        self.confidence_scores = SimpleNamespace(
            positive=0.05,
            neutral=0.05,
            negative=negative_score,
        )


class _FakeKeyPhrasesDoc:
    def __init__(self, key_phrases: list[str]) -> None:
        self.key_phrases = key_phrases


class _FakeTextAnalyticsClient:
    def __init__(self, sentiment: str, key_phrases: list[str]) -> None:
        self._sentiment = sentiment
        self._key_phrases = key_phrases

    def analyze_sentiment(
        self,
        texts: list[str],
        language: str = "pt-BR",
    ) -> list[_FakeSentimentDoc]:
        return [_FakeSentimentDoc(self._sentiment)]

    def extract_key_phrases(
        self,
        texts: list[str],
        language: str = "pt-BR",
    ) -> list[_FakeKeyPhrasesDoc]:
        return [_FakeKeyPhrasesDoc(self._key_phrases)]


def test_text_analytics_detects_critical_terms_and_positive_score() -> None:
    client = _FakeTextAnalyticsClient(
        sentiment="negative",
        key_phrases=["falta de ar", "dor no peito"],
    )
    findings = analyze_text_findings(
        "Paciente relata falta de ar e dor no peito",
        client=client,
    )
    assert len(findings.critical_terms) >= 2
    assert findings.score_textual > 0.0
    assert findings.sentiment == SentimentLabel.NEGATIVE


def test_text_analytics_neutral_text_has_zero_score() -> None:
    client = _FakeTextAnalyticsClient(
        sentiment="neutral",
        key_phrases=["sem queixas", "bem estar"],
    )
    findings = analyze_text_findings("Hoje me sinto bem e sem queixas", client=client)
    assert findings.critical_terms == []
    assert findings.score_textual == 0.0


def test_text_analytics_mixed_sentiment_counts_as_negative_for_scoring() -> None:
    client = _FakeTextAnalyticsClient(
        sentiment="mixed",
        key_phrases=["falta de ar"],
    )
    findings = analyze_text_findings("Estou melhor, mas ainda com falta de ar", client=client)
    assert findings.sentiment == SentimentLabel.MIXED
    assert findings.score_textual > 0.0
