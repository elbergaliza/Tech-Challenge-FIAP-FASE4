"""
Adapter para o módulo clínico (eicu-anomaly-detection).

Executa o pipeline clínico em lote (carregamento de dados, criação de
features, treinamento, predição e geração de alertas) e normaliza os alertas
para o schema ``AlertaNormalizado``.

Opcionalmente filtra por um único ``patient_id`` após a predição.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from adapters.base import (
    ModuleAdapter,
    expose_as_src,
    load_module_from_path,
    load_package_from_path,
    restore_src_modules,
)
from fusion.core.schema import AlertaNormalizado, classificar_nivel


class ClinicalAdapter(ModuleAdapter):
    """Adapter para o módulo ``eicu-anomaly-detection``."""

    MODULE_PATH = Path(__file__).resolve().parents[2] / "eicu-anomaly-detection"
    SRC_PATH = MODULE_PATH / "src"
    DEFAULT_DATA_DIR = MODULE_PATH / "modulo_anomalias" / "data" / "raw"

    def __init__(
        self,
        data_dir: str | Path | None = None,
        patient_id: str | None = None,
    ):
        self.data_dir = Path(data_dir) if data_dir else self.DEFAULT_DATA_DIR
        self.patient_id = patient_id
        self._src_pkg: ModuleType | None = None

    def _load_clinical_package(self) -> ModuleType:
        """Carrega o pacote 'src' do eicu-anomaly-detection como 'clinical_src'."""
        if self._src_pkg is not None:
            return self._src_pkg

        pkg = load_package_from_path("clinical_src", self.SRC_PATH)
        original_src = sys.modules.get("src")
        sys.modules["src"] = pkg

        try:
            # Carrega config primeiro porque os demais módulos dependem dele.
            config_module = load_module_from_path(
                self.SRC_PATH / "config.py", package="clinical_src"
            )
            sys.modules["src.config"] = config_module

            module_files = [
                "data_loader.py",
                "feature_builder.py",
                "anomaly_detector.py",
                "alert_generator.py",
            ]
            for filename in module_files:
                py_file = self.SRC_PATH / filename
                if py_file.exists():
                    mod = load_module_from_path(py_file, package="clinical_src")
                    sys.modules[f"src.{py_file.stem}"] = mod
        finally:
            if original_src is None:
                sys.modules.pop("src", None)
            else:
                sys.modules["src"] = original_src

        self._src_pkg = pkg
        return pkg

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

    def _configurar_paths(self, config: Any) -> None:
        """Sobrescreve paths do config para apontar para o data_dir informado."""
        config.DATA_RAW_DIR = self.data_dir
        config.VITAL_PERIODIC_FILE = self.data_dir / "vitalPeriodic.csv.gz"
        config.LAB_FILE = self.data_dir / "lab.csv.gz"
        config.MEDICATION_FILE = self.data_dir / "medication.csv.gz"
        config.DATA_PROCESSED_DIR = (
            self.MODULE_PATH / "modulo_anomalias" / "data" / "processed"
        )
        config.OUTPUTS_DIR = self.MODULE_PATH / "modulo_anomalias" / "outputs"

    def run(self, **kwargs: Any) -> list[AlertaNormalizado]:
        """
        Executa o pipeline clínico e retorna alertas normalizados.

        Args:
            **kwargs: ignorado — parâmetros relevantes são passados no __init__.
        """
        self._validar_dados()

        pkg = self._load_clinical_package()
        original_modules = expose_as_src("clinical_src", pkg)

        try:
            EICUDataLoader = sys.modules["src.data_loader"].EICUDataLoader
            ClinicalFeatureBuilder = sys.modules["src.feature_builder"].ClinicalFeatureBuilder
            ClinicalAnomalyDetector = sys.modules["src.anomaly_detector"].ClinicalAnomalyDetector
            AlertGenerator = sys.modules["src.alert_generator"].AlertGenerator
            config = sys.modules["src.config"]

            self._configurar_paths(config)

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
        finally:
            restore_src_modules(original_modules)

        return self._normalizar_alertas(alerts_df)
