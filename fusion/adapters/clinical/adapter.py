"""
Adapter para o módulo clínico (`eicu_anomaly_detection`).

Executa o pipeline clínico em lote (carregamento de dados, criação de
features, treinamento, predição e geração de alertas) e normaliza os alertas
para o schema ``AlertaNormalizado``.

Opcionalmente filtra por um único ``patient_id`` após a predição.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import eicu_anomaly_detection.config as config
from eicu_anomaly_detection.alert_generator import AlertGenerator
from eicu_anomaly_detection.anomaly_detector import ClinicalAnomalyDetector
from eicu_anomaly_detection.data_loader import EICUDataLoader
from eicu_anomaly_detection.feature_builder import ClinicalFeatureBuilder

from fusion.adapters.base import ModuleAdapter
from fusion.core.schema import AlertaNormalizado, classificar_nivel


class ClinicalAdapter(ModuleAdapter):
    """Adapter para o módulo ``eicu_anomaly_detection``."""

    DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "eicu_anomaly_detection" / "data" / "raw"

    def __init__(
        self,
        data_dir: str | Path | None = None,
        patient_id: str | None = None,
    ):
        self.data_dir = Path(data_dir) if data_dir else self.DEFAULT_DATA_DIR
        self.patient_id = patient_id

    def _validar_dados(self) -> None:
        """Verifica se os arquivos CSV do eICU existem no data_dir."""
        arquivos_necessarios = [
            "vitalPeriodic.csv.gz",
            "lab.csv.gz",
            "medication.csv.gz",
        ]
        faltando = [
            str(self.data_dir / nome)
            for nome in arquivos_necessarios
            if not (self.data_dir / nome).exists()
        ]
        if faltando:
            raise FileNotFoundError(
                "Dados do eICU Demo não encontrados em:\n"
                f"  {self.data_dir}\n\n"
                "Arquivos esperados:\n"
                "  - vitalPeriodic.csv.gz\n"
                "  - lab.csv.gz\n"
                "  - medication.csv.gz\n\n"
                "Opções:\n"
                "  1. Baixe o dataset real do PhysioNet e coloque os arquivos acima no diretório indicado\n"
                "  2. Use o mock para testes: python tests/fixtures/generate_fixtures.py"
            )

    @staticmethod
    def _split_leave_one_out(
        features: Any,
        patient_id: str,
        id_col: str = "patientunitstayid",
    ) -> tuple[Any, Any]:
        """Separa features em treino (todos menos o alvo) e predição (alvo)."""
        target_mask = features[id_col].astype(str) == str(patient_id)
        if not target_mask.any():
            raise ValueError(f"Paciente {patient_id} não encontrado nos dados.")

        train_features = features[~target_mask].copy()
        predict_features = features[target_mask].copy()

        if train_features.empty:
            raise ValueError("Conjunto de treino vazio após leave-one-out.")

        return train_features, predict_features

    def _use_leave_one_out(self) -> bool:
        """Retorna True se a variável de ambiente ativar leave-one-out."""
        return os.environ.get("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "").lower() in ("1", "true", "yes")

    def _get_train_predict_features(self, features: Any, patient_id: str | None) -> tuple[Any, Any]:
        """Retorna (treino, predição) de acordo com a configuração de env."""
        if self._use_leave_one_out() and patient_id is not None:
            return self._split_leave_one_out(features, patient_id)
        return features.copy(), features.copy()

    def _filtrar_alertas(self, alertas_df: Any, patient_id: str | None = None) -> Any:
        """Filtra alertas por patient_id quando especificado."""
        target = patient_id if patient_id is not None else self.patient_id
        if target is None or alertas_df.empty:
            return alertas_df
        filtro = alertas_df["sample_id"] == str(target)
        return alertas_df[filtro]

    def _normalizar_alertas(self, alertas_df: Any) -> list[AlertaNormalizado]:
        """Converte DataFrame de alertas clínicos em lista de AlertaNormalizado."""
        normalizados: list[AlertaNormalizado] = []
        for _, row in alertas_df.iterrows():
            score = float(row["score_risco"])
            normalizados.append(
                AlertaNormalizado(
                    module_id=str(row["sample_id"]),
                    modulo=str(row["modulo"]),
                    tipo_anomalia=str(row["tipo_anomalia"]),
                    score_risco=score,
                    nivel_risco=classificar_nivel(score),
                    descricao=str(row["descricao"]),
                    recomendacao=str(row["recomendacao"]),
                )
            )
        return normalizados

    def run(self, **kwargs: Any) -> list[AlertaNormalizado]:
        """
        Executa o pipeline clínico e retorna alertas normalizados.

        Args:
            **kwargs: ignorado — parâmetros relevantes são passados no __init__.
        """
        print(f"[clinical] data_dir={self.data_dir}, patient_id={self.patient_id}")
        self._validar_dados()

        config.DATA_RAW_DIR = self.data_dir
        config.VITAL_PERIODIC_FILE = self.data_dir / "vitalPeriodic.csv.gz"
        config.LAB_FILE = self.data_dir / "lab.csv.gz"
        config.MEDICATION_FILE = self.data_dir / "medication.csv.gz"
        config.DATA_PROCESSED_DIR = (
            Path(__file__).resolve().parents[2]
            / "eicu_anomaly_detection"
            / "data"
            / "processed"
        )
        config.OUTPUTS_DIR = (
            Path(__file__).resolve().parents[2]
            / "eicu_anomaly_detection"
            / "outputs"
        )

        loader = EICUDataLoader()
        vital_df = loader.load_vital_periodic()
        print(f"[clinical] vitalPeriodic carregado: {vital_df.shape[0]} linhas, {vital_df.shape[1]} colunas")

        builder = ClinicalFeatureBuilder()
        features = builder.build_vital_features(vital_df)
        print(f"[clinical] features criadas: {features.shape[0]} pacientes, {features.shape[1]} colunas")

        train_features, predict_features = self._get_train_predict_features(
            features, self.patient_id
        )
        modo = "leave-one-out" if self._use_leave_one_out() and self.patient_id else "batch"
        print(f"[clinical] modo={modo}, train={len(train_features)}, predict={len(predict_features)}")

        detector = ClinicalAnomalyDetector()
        detector.train(train_features)
        predictions = detector.predict(predict_features)
        print(f"[clinical] predicoes: {len(predictions)} linhas, anomalias={predictions['is_anomaly'].sum()}")

        alert_generator = AlertGenerator()
        alerts_df = alert_generator.generate_alerts(predictions, predict_features)
        alerts_df = self._filtrar_alertas(alerts_df, self.patient_id)
        print(f"[clinical] alertas gerados: {len(alerts_df)}")

        return self._normalizar_alertas(alerts_df)
