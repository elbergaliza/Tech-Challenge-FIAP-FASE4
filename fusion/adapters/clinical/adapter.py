"""
Adapter para o módulo clínico (eicu-anomaly-detection).

Executa o pipeline clínico em lote (carregamento de dados, criação de
features, treinamento, predição e geração de alertas) e normaliza os alertas
para o schema ``AlertaNormalizado``.

Opcionalmente filtra por um único ``patient_id`` após a predição.
"""

from __future__ import annotations

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
    """Adapter para o módulo ``eicu-anomaly-detection``."""

    DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "eicu-anomaly-detection" / "modulo_anomalias" / "data" / "raw"

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

    def _filtrar_alertas(self, alertas_df: Any, patient_id: str | None = None) -> Any:
        """Filtra alertas por patient_id quando especificado."""
        target = patient_id if patient_id is not None else self.patient_id
        if target is None:
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
        self._validar_dados()

        config.DATA_RAW_DIR = self.data_dir
        config.VITAL_PERIODIC_FILE = self.data_dir / "vitalPeriodic.csv.gz"
        config.LAB_FILE = self.data_dir / "lab.csv.gz"
        config.MEDICATION_FILE = self.data_dir / "medication.csv.gz"
        config.DATA_PROCESSED_DIR = (
            Path(__file__).resolve().parents[2]
            / "eicu-anomaly-detection"
            / "modulo_anomalias"
            / "data"
            / "processed"
        )
        config.OUTPUTS_DIR = (
            Path(__file__).resolve().parents[2]
            / "eicu-anomaly-detection"
            / "modulo_anomalias"
            / "outputs"
        )

        loader = EICUDataLoader()
        vital_df = loader.load_vital_periodic()

        builder = ClinicalFeatureBuilder()
        features = builder.build_vital_features(vital_df)

        detector = ClinicalAnomalyDetector()
        detector.train(features)
        predictions = detector.predict(features)

        alert_generator = AlertGenerator()
        alerts_df = alert_generator.generate_alerts(predictions, features)
        alerts_df = self._filtrar_alertas(alerts_df, self.patient_id)

        return self._normalizar_alertas(alerts_df)
