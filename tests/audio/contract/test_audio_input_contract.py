"""Testes de contrato para AudioProcessingRequest."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from src.audio.audio_schemas import AudioProcessingRequest

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-audio-texto-pipeline"
    / "contracts"
    / "audio-input.schema.json"
)


def _schema() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_audio_input_contract_accepts_valid_payload() -> None:
    payload = {
        "patient_id": "sample_ptbr_001",
        "audio_path": "data/raw/pt-br/sample_ptbr_001.wav",
        "language": "pt-BR",
        "source": "pt_br_demo",
        "max_duration_seconds": 600,
        "max_size_mb": 50,
        "timeout_seconds": 60,
    }

    jsonschema.validate(instance=payload, schema=_schema())
    model = AudioProcessingRequest.model_validate(payload)
    assert model.patient_id == payload["patient_id"]


def test_audio_input_contract_requires_patient_id() -> None:
    payload = {"audio_path": "data/raw/pt-br/sample_ptbr_001.wav"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_audio_input_contract_rejects_duration_above_limit() -> None:
    payload = {
        "patient_id": "sample_ptbr_001",
        "audio_path": "data/raw/pt-br/sample_ptbr_001.wav",
        "max_duration_seconds": 601,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_audio_input_contract_rejects_size_above_limit() -> None:
    payload = {
        "patient_id": "sample_ptbr_001",
        "audio_path": "data/raw/pt-br/sample_ptbr_001.wav",
        "max_size_mb": 51,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())
