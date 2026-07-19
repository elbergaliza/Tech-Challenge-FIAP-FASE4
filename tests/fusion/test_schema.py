"""Testes TDD para schema unificado e faixas de risco."""

import pytest


def test_alert_normalizado_basico():
    """Deve criar um AlertaNormalizado a partir do schema unificado."""
    from fusion.core.schema import AlertaNormalizado

    alerta = AlertaNormalizado(
        module_id="123",
        modulo="anomalias_clinicas_uti",
        tipo_anomalia="sinais_vitais",
        score_risco=0.91,
        nivel_risco="alto",
        descricao="Teste",
        recomendacao="Reavaliar",
    )

    assert alerta.module_id == "123"
    assert alerta.score_risco == 0.91
    assert alerta.to_dict()["module_id"] == "123"


def test_classificar_nivel_baixo():
    from fusion.core.schema import classificar_nivel

    assert classificar_nivel(0.0) == "baixo"
    assert classificar_nivel(0.39) == "baixo"


def test_classificar_nivel_moderado():
    from fusion.core.schema import classificar_nivel

    assert classificar_nivel(0.40) == "moderado"
    assert classificar_nivel(0.69) == "moderado"


def test_classificar_nivel_alto():
    from fusion.core.schema import classificar_nivel

    assert classificar_nivel(0.70) == "alto"
    assert classificar_nivel(1.0) == "alto"


def test_recomendacao_por_nivel():
    from fusion.core.schema import recomendacao_por_nivel

    assert "reavaliação imediata" in recomendacao_por_nivel("alto").lower()
    assert "observação" in recomendacao_por_nivel("moderado").lower()
    assert "monitoramento preventivo" in recomendacao_por_nivel("baixo").lower()
