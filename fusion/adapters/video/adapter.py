"""
Adapter para o módulo de vídeo (modulo_video).

Processa um vídeo MP4 usando MediaPipe Pose (+ YOLOv8 opcional) e normaliza o
alerta retornado para o schema ``AlertaNormalizado``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from modulo_video.pipeline import processar_video

from fusion.adapters.base import ModuleAdapter
from fusion.core.schema import AlertaNormalizado, classificar_nivel


class VideoAdapter(ModuleAdapter):
    """Adapter para o módulo ``modulo_video``."""

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

        alerta = processar_video(
            caminho_video=str(self.video_path),
            patient_id=self.patient_id,
            usar_objetos=not self.sem_objetos,
            verbose=not self.silencioso,
        )

        return [self._normalizar_alerta(alerta)]
