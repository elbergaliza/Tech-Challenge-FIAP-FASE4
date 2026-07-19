"""
Interface base para todos os adapters de módulos.

Todo adapter deve implementar ``run(**kwargs)`` e retornar uma lista de
``AlertaNormalizado`` para participar da fusão multimodal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fusion.core.schema import AlertaNormalizado


class ModuleAdapter(ABC):
    """Contrato que todo módulo deve cumprir para participar da fusão."""

    @abstractmethod
    def run(self, **kwargs: Any) -> list[AlertaNormalizado]:
        """Executa o módulo e retorna alertas no schema unificado."""
        raise NotImplementedError
