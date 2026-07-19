"""
Motor de fusão multimodal.

Consolida alertas de múltiplos módulos em um relatório final unificado.
Regras:
    - score_medio: média dos scores_risco de todos os alertas.
    - nivel_mais_critico: nível do alerta com maior score_risco.
    - recomendacao_geral: baseada no nivel_mais_critico.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fusion.adapters.base import ModuleAdapter
from fusion.core.schema import AlertaNormalizado, classificar_nivel, recomendacao_por_nivel


class MultimodalFusion:
    """Consolida alertas de múltiplos módulos em um relatório final."""

    def __init__(self, adapters: list[ModuleAdapter] | None = None):
        self.adapters = adapters or []

    def register(self, adapter: ModuleAdapter) -> "MultimodalFusion":
        """Registra um adapter na cadeia de fusão."""
        self.adapters.append(adapter)
        return self

    def run_all(self, **kwargs: Any) -> list[AlertaNormalizado]:
        """Executa todos os adapters registrados e concatena alertas."""
        alertas: list[AlertaNormalizado] = []
        for adapter in self.adapters:
            alertas.extend(adapter.run(**kwargs))
        return alertas

    def fuse(self, alertas: list[AlertaNormalizado]) -> dict[str, Any]:
        """Gera o relatório final a partir de uma lista de alertas."""
        total_alertas = len(alertas)

        modulos_analisados = sorted({a.modulo for a in alertas})
        modulos_com_alerta = sorted({a.modulo for a in alertas})

        if total_alertas == 0:
            score_medio = 0.0
            nivel_mais_critico = "baixo"
        else:
            scores = [a.score_risco for a in alertas]
            score_medio = round(sum(scores) / len(scores), 3)
            alerta_max = max(alertas, key=lambda a: a.score_risco)
            nivel_mais_critico = classificar_nivel(alerta_max.score_risco)

        recomendacao_geral = recomendacao_por_nivel(nivel_mais_critico)

        return {
            "gerado_em": datetime.now().isoformat(),
            "resumo": {
                "total_alertas": total_alertas,
                "score_medio": score_medio,
                "nivel_mais_critico": nivel_mais_critico,
                "modulos_analisados": modulos_analisados,
                "modulos_com_alerta": modulos_com_alerta,
                "recomendacao_geral": recomendacao_geral,
            },
            "alertas": [a.to_dict() for a in alertas],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Conveniência: executa adapters e já gera o relatório final."""
        alertas = self.run_all(**kwargs)
        return self.fuse(alertas)
