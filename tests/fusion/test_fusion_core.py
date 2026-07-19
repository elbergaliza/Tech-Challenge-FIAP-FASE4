"""Testes TDD para o motor de fusão multimodal."""

import pytest

from fusion.core.schema import AlertaNormalizado


def _alerta(module_id: str, modulo: str, score: float) -> AlertaNormalizado:
    return AlertaNormalizado(
        module_id=module_id,
        modulo=modulo,
        tipo_anomalia="sinais_vitais",
        score_risco=score,
        nivel_risco="alto" if score >= 0.70 else ("moderado" if score >= 0.40 else "baixo"),
        descricao="desc",
        recomendacao="recom",
    )


def test_score_medio_eh_media():
    from fusion.core.fusion import MultimodalFusion

    fusion = MultimodalFusion()
    alertas = [
        _alerta("a", "anomalias_clinicas_uti", 0.91),
        _alerta("b", "video_fisioterapia", 0.10),
    ]

    relatorio = fusion.fuse(alertas)

    assert relatorio["resumo"]["score_medio"] == 0.505


def test_nivel_critico_preservado():
    from fusion.core.fusion import MultimodalFusion

    fusion = MultimodalFusion()
    alertas = [
        _alerta("a", "anomalias_clinicas_uti", 0.91),
        _alerta("b", "video_fisioterapia", 0.10),
    ]

    relatorio = fusion.fuse(alertas)

    assert relatorio["resumo"]["nivel_mais_critico"] == "alto"


def test_recomendacao_geral_baseada_no_pior():
    from fusion.core.fusion import MultimodalFusion

    fusion = MultimodalFusion()
    alertas = [
        _alerta("a", "anomalias_clinicas_uti", 0.91),
        _alerta("b", "video_fisioterapia", 0.10),
    ]

    relatorio = fusion.fuse(alertas)

    assert "reavaliação imediata" in relatorio["resumo"]["recomendacao_geral"].lower()


def test_sem_alertas_retorna_resumo_vazio_valido():
    from fusion.core.fusion import MultimodalFusion

    fusion = MultimodalFusion()
    relatorio = fusion.fuse([])

    assert relatorio["resumo"]["total_alertas"] == 0
    assert relatorio["resumo"]["score_medio"] == 0.0
    assert relatorio["resumo"]["nivel_mais_critico"] == "baixo"
    assert relatorio["resumo"]["modulos_analisados"] == []
    assert relatorio["alertas"] == []


def test_modulos_analisados_e_com_alerta():
    from fusion.core.fusion import MultimodalFusion

    fusion = MultimodalFusion()
    alertas = [
        _alerta("a", "anomalias_clinicas_uti", 0.91),
        _alerta("b", "video_fisioterapia", 0.42),
    ]

    relatorio = fusion.fuse(alertas)

    assert relatorio["resumo"]["modulos_analisados"] == ["anomalias_clinicas_uti", "video_fisioterapia"]
    assert relatorio["resumo"]["modulos_com_alerta"] == ["anomalias_clinicas_uti", "video_fisioterapia"]
