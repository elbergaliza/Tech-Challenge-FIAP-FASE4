"""Testes TDD para os adapters de módulos."""

import json
from pathlib import Path

import pandas as pd
import pytest


def _alerta_df(alerts: list[dict]) -> pd.DataFrame:
    """Helper para criar DataFrame mínimo de alertas clínicos."""
    padrao = {
        "sample_id": "",
        "modulo": "anomalias_clinicas_uti",
        "tipo_anomalia": "sinais_vitais",
        "score_risco": 0.5,
        "descricao": "desc",
        "recomendacao": "recom",
    }
    for alerta in alerts:
        for chave, valor in padrao.items():
            alerta.setdefault(chave, valor)
    return pd.DataFrame(alerts)


def test_clinical_adapter_normaliza_sample_id_para_module_id():
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    adapter = ClinicalAdapter()
    df = _alerta_df([{"sample_id": "141765"}])

    normalizado = adapter._normalizar_alertas(df)

    assert normalizado[0].module_id == "141765"


def test_clinical_adapter_filtra_por_patient_id():
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    adapter = ClinicalAdapter(patient_id="141765")
    df = _alerta_df([
        {"sample_id": "141765", "score_risco": 0.9, "modulo": "anomalias_clinicas_uti"},
        {"sample_id": "999999", "score_risco": 0.8, "modulo": "anomalias_clinicas_uti"},
    ])

    filtrados = adapter._filtrar_alertas(df)

    assert len(filtrados) == 1
    assert filtrados.iloc[0]["sample_id"] == "141765"


def test_clinical_adapter_patient_id_inexistente_retorna_vazio():
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    adapter = ClinicalAdapter(patient_id="nao_existe")
    df = _alerta_df([
        {"sample_id": "141765", "score_risco": 0.9, "modulo": "anomalias_clinicas_uti"},
    ])

    filtrados = adapter._filtrar_alertas(df)

    assert len(filtrados) == 0


def test_video_adapter_normaliza_patient_id_para_module_id(tmp_path):
    from fusion.adapters.video.adapter import VideoAdapter

    adapter = VideoAdapter(video_path=str(tmp_path / "fake.mp4"), patient_id="paciente_001")
    alerta_video = {
        "patient_id": "paciente_001",
        "modulo": "video_fisioterapia",
        "tipo_anomalia": "movimento",
        "score_risco": 0.42,
        "nivel_risco": "moderado",
        "descricao": "Assimetria",
        "recomendacao": "Revisar",
    }

    normalizado = adapter._normalizar_alerta(alerta_video)

    assert normalizado.module_id == "paciente_001"
    assert normalizado.modulo == "video_fisioterapia"


def test_video_adapter_arquivo_nao_encontrado(tmp_path):
    from fusion.adapters.video.adapter import VideoAdapter

    adapter = VideoAdapter(video_path=str(tmp_path / "inexistente.mp4"))

    with pytest.raises(FileNotFoundError):
        adapter._validar_video()


def test_audio_adapter_stub_retorna_vazio():
    from fusion.adapters.audio.adapter import AudioAdapter

    adapter = AudioAdapter()

    assert adapter.run() == []


def test_module_adapter_interface():
    from fusion.adapters.base import ModuleAdapter
    from fusion.core.schema import AlertaNormalizado

    class DummyAdapter(ModuleAdapter):
        def run(self, **kwargs):
            return [AlertaNormalizado("1", "dummy", "teste", 0.5, "moderado", "d", "r")]

    assert len(DummyAdapter().run()) == 1
