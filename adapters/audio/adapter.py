"""
Adapter placeholder para o futuro módulo de áudio/texto.

Quando a branch ``001-audio-texto-pipeline`` estiver integrada, este adapter
será substituído pela chamada real ao pipeline de áudio. Até lá, ele retorna
lista vazia para não quebrar a fusão multimodal.
"""

from __future__ import annotations

from typing import Any

from adapters.base import ModuleAdapter
from fusion.core.schema import AlertaNormalizado


class AudioAdapter(ModuleAdapter):
    """Stub para o módulo de áudio/texto."""

    def __init__(self, audio_path: str | None = None, patient_id: str = "audio_001"):
        self.audio_path = audio_path
        self.patient_id = patient_id

    def run(self, **kwargs: Any) -> list[AlertaNormalizado]:
        return []
