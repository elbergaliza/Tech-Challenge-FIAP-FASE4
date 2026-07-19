"""
Adapter para o módulo de vídeo (modulo_video).

Processa um vídeo MP4 usando MediaPipe Pose (+ YOLOv8 opcional) e normaliza o
alerta retornado para o schema ``AlertaNormalizado``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from adapters.base import ModuleAdapter
from fusion.core.schema import AlertaNormalizado, classificar_nivel


class VideoAdapter(ModuleAdapter):
    """Adapter para o módulo ``modulo_video``."""

    MODULE_PATH = Path(__file__).resolve().parents[2] / "modulo_video"
    SRC_PATH = MODULE_PATH / "src"
    CONFIG_PATH = MODULE_PATH / "config.py"

    def __init__(
        self,
        video_path: str,
        patient_id: str = "video_001",
        sem_objetos: bool = False,
        silencioso: bool = False,
    ):
        self.video_path = Path(video_path)
        self.patient_id = patient_id
        self.sem_objetos = sem_objetos
        self.silencioso = silencioso
        self._src_pkg: ModuleType | None = None

    def _load_module(self, module_path: Path, package: str = "video_src") -> ModuleType:
        """Carrega um módulo Python pelo caminho absoluto sem depender de sys.path."""
        module_name = f"{package}.{module_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Não foi possível carregar {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _load_video_package(self) -> ModuleType:
        """Carrega o pacote 'src' do modulo_video como 'video_src'."""
        if self._src_pkg is not None:
            return self._src_pkg

        package_name = "video_src"
        pkg_path = self.SRC_PATH

        pkg_spec = importlib.util.spec_from_file_location(
            package_name,
            pkg_path / "__init__.py",
            submodule_search_locations=[str(pkg_path), str(self.MODULE_PATH)],
        )
        if pkg_spec is None or pkg_spec.loader is None:
            raise ImportError(f"Não foi possível carregar pacote {pkg_path}")
        pkg = importlib.util.module_from_spec(pkg_spec)
        sys.modules[package_name] = pkg
        pkg_spec.loader.exec_module(pkg)

        # Expoe o pacote tambem como 'src' e 'config' durante o carregamento,
        # pois os modulos internos usam tanto `from config import ...` quanto
        # `from src.xxx import ...`.
        original_src = sys.modules.get("src")
        original_config = sys.modules.get("config")
        sys.modules["src"] = pkg

        try:
            # config deve estar disponivel como 'config' e como 'src.config'.
            config_module = self._load_module(self.CONFIG_PATH, package=package_name)
            sys.modules["config"] = config_module
            sys.modules["src.config"] = config_module

            src_modules = [
                "pose_extractor.py",
                "biomechanics.py",
                "anomaly_detector.py",
                "risk_scoring.py",
                "report.py",
                "pipeline.py",
            ]
            for filename in src_modules:
                module_path = pkg_path / filename
                if module_path.exists():
                    mod = self._load_module(module_path, package=package_name)
                    sys.modules[f"src.{module_path.stem}"] = mod

            object_detector_path = pkg_path / "object_detector.py"
            if object_detector_path.exists():
                mod = self._load_module(object_detector_path, package=package_name)
                sys.modules["src.object_detector"] = mod
        finally:
            if original_src is None:
                sys.modules.pop("src", None)
            else:
                sys.modules["src"] = original_src
            if original_config is None:
                sys.modules.pop("config", None)
            else:
                sys.modules["config"] = original_config

        self._src_pkg = pkg
        return pkg

    def _validar_video(self) -> None:
        """Levanta erro claro se o vídeo não existe."""
        if not self.video_path.exists():
            raise FileNotFoundError(
                f"Arquivo de vídeo não encontrado: {self.video_path}"
            )

    def _normalizar_alerta(self, alerta: dict[str, Any]) -> AlertaNormalizado:
        """Converte o dict de saída do módulo de vídeo para AlertaNormalizado."""
        score = float(alerta["score_risco"])
        return AlertaNormalizado(
            module_id=str(alerta["patient_id"]),
            modulo=str(alerta["modulo"]),
            tipo_anomalia=str(alerta["tipo_anomalia"]),
            score_risco=score,
            nivel_risco=classificar_nivel(score),
            descricao=str(alerta["descricao"]),
            recomendacao=str(alerta["recomendacao"]),
        )

    def run(self, **kwargs: Any) -> list[AlertaNormalizado]:
        """Processa o vídeo e retorna lista com um único alerta normalizado."""
        self._validar_video()

        pkg = self._load_video_package()

        # Expoe o pacote carregado tambem como 'src' e 'config' para que as
        # importacoes relativas internas funcionem durante a execucao.
        original_src = sys.modules.get("src")
        original_config = sys.modules.get("config")
        sys.modules["src"] = pkg

        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("video_src."):
                src_name = "src." + mod_name.split(".", 1)[1]
                sys.modules[src_name] = sys.modules[mod_name]
        if "video_src.config" in sys.modules:
            sys.modules["config"] = sys.modules["video_src.config"]

        try:
            pipeline = self._load_module(self.SRC_PATH / "pipeline.py")
            processar_video = pipeline.processar_video

            alerta = processar_video(
                caminho_video=str(self.video_path),
                patient_id=self.patient_id,
                usar_objetos=not self.sem_objetos,
                verbose=not self.silencioso,
            )
        finally:
            # Restaura 'src' e 'config' originais.
            for mod_name in list(sys.modules.keys()):
                if mod_name == "src" or mod_name.startswith("src."):
                    sys.modules.pop(mod_name, None)
            if original_src is None:
                sys.modules.pop("src", None)
            else:
                sys.modules["src"] = original_src
            if original_config is None:
                sys.modules.pop("config", None)
            else:
                sys.modules["config"] = original_config

        return [self._normalizar_alerta(alerta)]
