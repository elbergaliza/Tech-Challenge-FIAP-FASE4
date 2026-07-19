"""
test_e2e_mock.py
----------------
Teste end-to-end usando fixtures mockadas.

Este teste gera dados eICU sintéticos e um vídeo MP4 leve, executa a fusão
multimodal via ``main.main()`` e valida que o relatório final é gerado
com a estrutura esperada.

É indicado para testes locais e CI quando não se deseja baixar o dataset
real do PhysioNet ou depender de vídeos externos.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Garante que os geradores de fixture possam ser importados.
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(FIXTURES_DIR))

from generate_fixtures import main as generate_fixtures_main  # noqa: E402


@pytest.fixture(scope="session")
def fixtures() -> dict[str, Path]:
    """Gera fixtures mockadas uma vez por sessão de teste."""
    generate_fixtures_main(["--skip-video"])
    return {
        "eicu_dir": FIXTURES_DIR / "mock_eicu",
        "video": FIXTURES_DIR / "test_video.mp4",
    }


def test_e2e_mock_pipeline_gera_relatorio(fixtures: dict[str, Path]) -> None:
    """A pipeline E2E com dados mockados deve gerar o relatório multimodal."""
    from main import main as run_main

    output_path = FIXTURES_DIR / "final_multimodal_report_e2e.json"

    returncode = run_main(
        [
            "--video",
            str(fixtures["video"]),
            "--eicu-data",
            str(fixtures["eicu_dir"]),
            "--video-patient-id",
            "e2e_test",
            "--sem-objetos",
            "--silencioso",
            "--saida",
            str(output_path),
        ]
    )

    assert returncode == 0, "A pipeline E2E retornou código de erro"
    assert output_path.exists(), "Relatório final não foi gerado"

    with open(output_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "resumo" in report
    assert "alertas" in report
    assert report["resumo"]["modulos_analisados"] == [
        "anomalias_clinicas_uti",
        "video_fisioterapia",
    ]
    assert report["resumo"]["total_alertas"] >= 0
    assert isinstance(report["alertas"], list)

    # Pelo menos um alerta clínico é esperado com o mock realista.
    clinical_alerts = [
        a for a in report["alertas"] if a["modulo"] == "anomalias_clinicas_uti"
    ]
    assert len(clinical_alerts) >= 1, "Esperado ao menos um alerta clínico"

    # O alerta de vídeo deve usar o patient_id informado como module_id.
    video_alerts = [
        a for a in report["alertas"] if a["modulo"] == "video_fisioterapia"
    ]
    if video_alerts:
        assert video_alerts[0]["module_id"] == "e2e_test"
