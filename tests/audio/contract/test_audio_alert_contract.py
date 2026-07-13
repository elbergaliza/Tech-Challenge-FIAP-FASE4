"""Testes de contrato para AudioAlert."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from src.audio.audio_schemas import AudioAlert, AudioEvidences, RiskLevel, TranscriptionStatus

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-audio-texto-pipeline"
    / "contracts"
    / "audio-alert.schema.json"
)


def _schema() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _base_payload() -> dict[str, object]:
    return {
        "patient_id": "sample_ptbr_001",
        "modulo": "audio_texto",
        "tipo_anomalia": "alteracao_respiratoria_vocal",
        "score_risco": 0.81,
        "nivel_risco": "alto",
        "descricao": "Paciente apresenta sinais de risco respiratorio.",
        "recomendacao": "Encaminhar para avaliacao respiratoria.",
        "evidencias": {
            "score_acustico": 0.3,
            "score_textual": 0.9,
            "score_textual_efetivo": 0.81,
            "confianca_transcricao": 0.9,
            "fontes_risco": ["texto"],
            "status_transcricao": "success",
            "duracao_processamento_ms": 4200,
            "excedeu_limite_latencia": False,
        },
    }


def test_audio_alert_contract_accepts_valid_payload() -> None:
    payload = _base_payload()
    jsonschema.validate(instance=payload, schema=_schema())
    model = AudioAlert.model_validate(payload)
    assert model.modulo == "audio_texto"


@pytest.mark.parametrize(
    ("score_risco", "nivel"),
    [
        (0.39, "baixo"),
        (0.40, "moderado"),
        (0.70, "alto"),
    ],
)
def test_audio_alert_contract_boundary_levels(score_risco: float, nivel: str) -> None:
    payload = _base_payload()
    payload["score_risco"] = score_risco
    payload["nivel_risco"] = nivel
    jsonschema.validate(instance=payload, schema=_schema())
    model = AudioAlert.model_validate(payload)
    assert model.nivel_risco.value == nivel


def test_audio_alert_contract_rejects_missing_required_fields() -> None:
    payload = _base_payload()
    del payload["descricao"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_audio_alert_schema_model_uses_all_required_fields() -> None:
    alert = AudioAlert(
        patient_id="sample_001",
        tipo_anomalia="nenhuma",
        score_risco=0.0,
        nivel_risco=RiskLevel.BAIXO,
        descricao="Sem sinais de risco.",
        recomendacao="Manter acompanhamento.",
        evidencias=AudioEvidences(
            score_acustico=0.0,
            score_textual=0.0,
            score_textual_efetivo=0.0,
            confianca_transcricao=0.0,
            fontes_risco=[],
            status_transcricao=TranscriptionStatus.NO_SPEECH,
            duracao_processamento_ms=1000,
            excedeu_limite_latencia=False,
        ),
    )
    payload = alert.model_dump(mode="json")
    jsonschema.validate(instance=payload, schema=_schema())
    assert payload["modulo"] == "audio_texto"
    assert payload["evidencias"]["fontes_risco"] == []
