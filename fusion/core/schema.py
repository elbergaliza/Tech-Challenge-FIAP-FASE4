"""
Schema unificado e faixas de risco compartilhados entre todos os módulos.

A fusão multimodal espera que cada adapter entregue alertas no formato
``AlertaNormalizado``. As funções auxiliares garantem que a classificação de
risco e as recomendações sejam consistentes entre módulos clínico, vídeo,
áudio, etc.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AlertaNormalizado:
    """Alerta proveniente de qualquer módulo, já normalizado para fusão."""

    module_id: str
    modulo: str
    tipo_anomalia: str
    score_risco: float
    nivel_risco: str
    descricao: str
    recomendacao: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Faixas de risco unificadas entre módulos.
# baixo: [0.00, 0.40), moderado: [0.40, 0.70), alto: [0.70, 1.01)
FAIXAS_RISCO: list[tuple[str, float, float]] = [
    ("baixo", 0.0, 0.40),
    ("moderado", 0.40, 0.70),
    ("alto", 0.70, 1.01),
]


def classificar_nivel(score: float) -> str:
    """Classifica um score de risco (0.0 a 1.0) em nível unificado."""
    for nivel, minimo, maximo in FAIXAS_RISCO:
        if minimo <= score < maximo:
            return nivel
    return "alto" if score >= 1.0 else "baixo"


def recomendacao_por_nivel(nivel: str) -> str:
    """Recomendação padrão para cada nível de risco unificado."""
    if nivel == "alto":
        return "Acionar equipe médica para reavaliação imediata do paciente."
    if nivel == "moderado":
        return "Manter paciente em observação e repetir avaliação clínica."
    return "Continuar monitoramento preventivo."
