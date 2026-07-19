"""
Adapter para o módulo de vídeo (modulo_video).

Processa um vídeo MP4 usando MediaPipe Pose (+ YOLOv8 opcional) e normaliza o
alerta retornado para o schema ``AlertaNormalizado``.
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
)
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

    def _load_video_package(self) -> ModuleType:
        """Carrega o pacote 'src' do modulo_video como 'video_src'."""
        if self._src_pkg is not None:
            return self._src_pkg

        pkg = load_package_from_path("video_src", self.SRC_PATH)
        original_src = sys.modules.get("src")
        original_config = sys.modules.get("config")
        sys.modules["src"] = pkg

        try:
            config_module = load_module_from_path(self.CONFIG_PATH, package="video_src")
            sys.modules["config"] = config_module
            sys.modules["src.config"] = config_module

            src_modules = [
                "pose_extractor.py",
                "biomechanics.py",
                "anomaly_detector.py",
                "risk_scoring.py",
                "report.py",
                "pipeline.py",
                "object_detector.py",
            ]
            for filename in src_modules:
                module_path = self.SRC_PATH / filename
                if module_path.exists():
                    mod = load_module_from_path(module_path, package="video_src")
                    sys.modules[f"src.{module_path.stem}"] = mod
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
        original_modules = expose_as_src("video_src", pkg)

        if "video_src.config" in sys.modules:
            sys.modules["config"] = sys.modules["video_src.config"]

        try:
            processar_video = sys.modules["src.pipeline"].processar_video
            alerta = processar_video(
                caminho_video=str(self.video_path),
                patient_id=self.patient_id,
                usar_objetos=not self.sem_objetos,
                verbose=not self.silencioso,
            )
        finally:
            from adapters.base import restore_src_modules
            restore_src_modules(original_modules)
            original_config = sys.modules.get("config")
            if original_config is not None and "config" not in original_modules:
                sys.modules["config"] = original_config

        return [self._normalizar_alerta(alerta)]
