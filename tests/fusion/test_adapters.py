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


def test_clinical_adapter_split_features_por_patient_id():
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2", "3"],
        "heartrate_max": [100, 120, 90],
    })

    train_df, predict_df = ClinicalAdapter._split_leave_one_out(features, "2")

    assert train_df["patientunitstayid"].tolist() == ["1", "3"]
    assert predict_df["patientunitstayid"].tolist() == ["2"]


def test_clinical_adapter_patient_id_inexistente_leave_one_out_levanta_erro(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "true")

    adapter = ClinicalAdapter()
    features = pd.DataFrame({
        "patientunitstayid": ["141765"],
        "heartrate_max": [120],
    })

    with pytest.raises(ValueError, match="Paciente .* não encontrado"):
        adapter._get_train_predict_features(features, "nao_existe")


def test_clinical_adapter_leave_one_out_treino_vazio_levanta_erro(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "true")

    adapter = ClinicalAdapter()
    features = pd.DataFrame({
        "patientunitstayid": ["1"],
        "heartrate_max": [100],
    })

    with pytest.raises(ValueError, match="Conjunto de treino vazio"):
        adapter._get_train_predict_features(features, "1")


def test_clinical_adapter_env_var_truthy_variations(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2"],
        "heartrate_max": [100, 120],
    })

    adapter = ClinicalAdapter()

    for valor in ("1", "true", "True", "yes", "YES"):
        monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", valor)
        train_df, _ = adapter._get_train_predict_features(features, "2")
        assert len(train_df) == 1
        assert train_df.iloc[0]["patientunitstayid"] == "1"


def test_clinical_adapter_env_var_falsy_variations(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2"],
        "heartrate_max": [100, 120],
    })

    adapter = ClinicalAdapter()

    for valor in ("0", "false", "False", "no", "", None):
        if valor is None:
            monkeypatch.delenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", raising=False)
        else:
            monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", valor)

        train_df, _ = adapter._get_train_predict_features(features, "2")
        assert len(train_df) == 2


def test_clinical_adapter_patient_id_inexistente_retorna_vazio():
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    adapter = ClinicalAdapter(patient_id="nao_existe")
    df = _alerta_df([
        {"sample_id": "141765", "score_risco": 0.9, "modulo": "anomalias_clinicas_uti"},
    ])

    filtrados = adapter._filtrar_alertas(df)

    assert len(filtrados) == 0


def test_clinical_adapter_env_desligado_mantem_batch(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.delenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", raising=False)

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2", "3"],
        "heartrate_max": [100, 120, 90],
    })

    adapter = ClinicalAdapter()
    train_df, predict_df = adapter._get_train_predict_features(features, "2")

    assert train_df["patientunitstayid"].tolist() == ["1", "2", "3"]
    assert predict_df["patientunitstayid"].tolist() == ["1", "2", "3"]


def test_clinical_adapter_env_ligado_ativa_leave_one_out(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "1")

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2", "3"],
        "heartrate_max": [100, 120, 90],
    })

    adapter = ClinicalAdapter()
    train_df, predict_df = adapter._get_train_predict_features(features, "2")

    assert train_df["patientunitstayid"].tolist() == ["1", "3"]
    assert predict_df["patientunitstayid"].tolist() == ["2"]


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


def test_clinical_adapter_run_usa_leave_one_out_quando_env_ativado(monkeypatch, tmp_path):
    from unittest.mock import patch
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "1")

    adapter = ClinicalAdapter(
        data_dir=str(tmp_path),
        patient_id="paciente_2",
    )

    for nome in ["vitalPeriodic.csv.gz", "lab.csv.gz", "medication.csv.gz"]:
        (tmp_path / nome).write_text(
            "patientunitstayid,heartrate\npaciente_1,70\npaciente_2,120\n"
        )

    with patch("fusion.adapters.clinical.adapter.EICUDataLoader") as MockLoader, \
         patch("fusion.adapters.clinical.adapter.ClinicalFeatureBuilder") as MockBuilder, \
         patch("fusion.adapters.clinical.adapter.ClinicalAnomalyDetector") as MockDetector, \
         patch("fusion.adapters.clinical.adapter.AlertGenerator") as MockAlertGenerator:

        MockLoader.return_value.load_vital_periodic.return_value = pd.DataFrame({
            "patientunitstayid": ["paciente_1", "paciente_2"],
            "heartrate": [70, 120],
        })
        MockLoader.return_value.load_labs.return_value = pd.DataFrame()
        MockLoader.return_value.load_medications.return_value = pd.DataFrame()

        MockBuilder.return_value.build_vital_features.return_value = pd.DataFrame({
            "patientunitstayid": ["paciente_1", "paciente_2"],
            "heartrate_max": [70, 120],
        })

        MockDetector.return_value.predict.return_value = pd.DataFrame({
            "patientunitstayid": ["paciente_2"],
            "is_anomaly": [True],
            "risk_score": [0.9],
            "risk_level": ["alto"],
        })

        MockAlertGenerator.return_value.generate_alerts.return_value = pd.DataFrame({
            "sample_id": ["paciente_2"],
            "modulo": ["anomalias_clinicas_uti"],
            "tipo_anomalia": ["sinais_vitais"],
            "score_risco": [0.9],
            "nivel_risco": ["alto"],
            "descricao": ["test"],
            "recomendacao": ["test"],
        })

        alertas = adapter.run()

    assert len(alertas) == 1
    assert alertas[0].module_id == "paciente_2"


def test_module_adapter_interface():
    from fusion.adapters.base import ModuleAdapter
    from fusion.core.schema import AlertaNormalizado

    class DummyAdapter(ModuleAdapter):
        def run(self, **kwargs):
            return [AlertaNormalizado("1", "dummy", "teste", 0.5, "moderado", "d", "r")]

    assert len(DummyAdapter().run()) == 1
