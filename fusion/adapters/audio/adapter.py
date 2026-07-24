"""
Adapter para o módulo de áudio/texto (001-audio-texto-pipeline).

Processa um arquivo de áudio ou vídeo usando o pipeline ``src.audio`` e
normaliza o ``AudioAlert`` retornado para o schema ``AlertaNormalizado``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fusion.adapters.base import ModuleAdapter
from fusion.core.schema import AlertaNormalizado, classificar_nivel
from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import AudioAlert, AudioProcessingRequest, AudioSource


class AudioAdapter(ModuleAdapter):
    """Adapter para o módulo ``audio_texto``."""

    def __init__(
        self,
        audio_path: str,
        patient_id: str = "audio_001",
        language: str = "pt-BR",
        source: AudioSource = AudioSource.UNKNOWN,
    ):
        self.audio_path = Path(audio_path)
        self.patient_id = patient_id
        self.language = language
        self.source = source

    def _validar_audio(self) -> None:
        """Levanta erro claro se o arquivo não existe."""
        if not self.audio_path.exists():
            raise FileNotFoundError(
                f"Arquivo de áudio não encontrado: {self.audio_path}"
            )

    def _normalizar_alerta(self, alert: AudioAlert) -> AlertaNormalizado:
        """Converte AudioAlert para AlertaNormalizado."""
        score = float(alert.score_risco)
        return AlertaNormalizado(
            module_id=alert.patient_id,
            modulo=alert.modulo,
            tipo_anomalia=alert.tipo_anomalia,
            score_risco=score,
            nivel_risco=classificar_nivel(score),
            descricao=alert.descricao,
            recomendacao=alert.recomendacao,
        )

    def run(self, **kwargs: Any) -> list[AlertaNormalizado]:
        """Processa o áudio e retorna lista com um único alerta normalizado."""
        self._validar_audio()

        request = AudioProcessingRequest(
            patient_id=self.patient_id,
            audio_path=self.audio_path,
            language=self.language,  # type: ignore[arg-type]
            source=self.source,
        )

        alert = process_audio_recording(request)
        return [self._normalizar_alerta(alert)]
