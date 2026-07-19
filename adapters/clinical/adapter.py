"""
Adapter para o módulo clínico (eicu-anomaly-detection).

Executa o pipeline clínico em lote (carregamento de dados, criação de
features, treinamento, predição e geração de alertas) e normaliza os alertas
para o schema ``AlertaNormalizado``.

Opcionalmente filtra por um único ``patient_id`` após a predição.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from adapters.base import ModuleAdapter
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

    def _load_module(self, module_path: Path, package: str = "clinical_src") -> ModuleType:
        """Carrega um módulo Python pelo caminho absoluto sem depender de sys.path."""
        module_name = f"{package}.{module_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Não foi possível carregar {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _load_clinical_package(self) -> ModuleType:
        """Carrega o pacote 'src' do eicu-anomaly-detection como 'clinical_src'."""
        if self._src_pkg is not None:
            return self._src_pkg

        package_name = "clinical_src"
        pkg_path = self.SRC_PATH

        pkg_spec = importlib.util.spec_from_file_location(
            package_name, pkg_path / "__init__.py", submodule_search_locations=[str(pkg_path)]
        )
        if pkg_spec is None or pkg_spec.loader is None:
            raise ImportError(f"Não foi possível carregar pacote {pkg_path}")
        pkg = importlib.util.module_from_spec(pkg_spec)
        sys.modules[package_name] = pkg
        pkg_spec.loader.exec_module(pkg)

        # Expoe o pacote tambem como 'src' durante o carregamento, pois os
        # modulos internos fazem importacoes do tipo `from src import config`.
        original_src = sys.modules.get("src")
        sys.modules["src"] = pkg

        try:
            # Carrega config primeiro porque os demais modulos dependem dele.
            config_module = self._load_module(pkg_path / "config.py", package=package_name)
            sys.modules["src.config"] = config_module

            # Carrega os demais modulos usados pelo pipeline.
            module_files = [
                "data_loader.py",
                "feature_builder.py",
                "anomaly_detector.py",
                "alert_generator.py",
                "train.py",
                "test_output.py",
            ]
            for filename in module_files:
                py_file = pkg_path / filename
                if py_file.exists():
                    mod = self._load_module(py_file, package=package_name)
                    sys.modules[f"src.{py_file.stem}"] = mod
        finally:
            # Restaura 'src' para nao poluir o cache durante carregamento,
            # a execucao do run() fara o monkey-patch novamente de forma controlada.
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
                "  1. Baixe o dataset real: python scripts/download_eicu_demo.py\n"
                "  2. Use o mock para testes: python tests/fixtures/generate_fixtures.py"
            )

    def _filtrar_alertas(
        self, alertas_df: Any, patient_id: str | None = None
    ) -> Any:
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

        pkg = self._load_clinical_package()

        # Expoe o pacote carregado tambem como 'src' para que as importacoes
        # relativas internas (ex.: `from src import config`) funcionem.
        original_modules: dict[str, Any] = {}
        for mod_name in list(sys.modules.keys()):
            if mod_name == "src" or mod_name.startswith("src."):
                original_modules[mod_name] = sys.modules.pop(mod_name)

        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("clinical_src."):
                src_name = "src." + mod_name.split(".", 1)[1]
                sys.modules[src_name] = sys.modules[mod_name]
        sys.modules["src"] = pkg

        EICUDataLoader = sys.modules["src.data_loader"].EICUDataLoader
        ClinicalFeatureBuilder = sys.modules["src.feature_builder"].ClinicalFeatureBuilder
        ClinicalAnomalyDetector = sys.modules["src.anomaly_detector"].ClinicalAnomalyDetector
        AlertGenerator = sys.modules["src.alert_generator"].AlertGenerator
        config = sys.modules["src.config"]

        # Sobrescreve paths do config para apontar para o data_dir informado
        config.DATA_RAW_DIR = self.data_dir
        config.PATIENT_FILE = self.data_dir / "patient.csv.gz"
        config.VITAL_PERIODIC_FILE = self.data_dir / "vitalPeriodic.csv.gz"
        config.VITAL_APERIODIC_FILE = self.data_dir / "vitalAperiodic.csv.gz"
        config.LAB_FILE = self.data_dir / "lab.csv.gz"
        config.MEDICATION_FILE = self.data_dir / "medication.csv.gz"
        config.DATA_PROCESSED_DIR = (
            self.MODULE_PATH / "modulo_anomalias" / "data" / "processed"
        )
        config.OUTPUTS_DIR = self.MODULE_PATH / "modulo_anomalias" / "outputs"

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

        # Restaura o 'src' original para nao afetar outros adapters.
        for mod_name in list(sys.modules.keys()):
            if mod_name == "src" or mod_name.startswith("src."):
                sys.modules.pop(mod_name, None)
        for mod_name, mod in original_modules.items():
            sys.modules[mod_name] = mod

        return self._normalizar_alertas(alerts_df)
