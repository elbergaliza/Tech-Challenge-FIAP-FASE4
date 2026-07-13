"""Valida fronteira do modulo de audio (FR-016)."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_MODULES = {"video_pipeline", "text_pipeline", "anomaly", "alerts", "fusion"}

TARGET_FILES = [
    "src/audio/audio_pipeline.py",
    "src/audio/audio_azure.py",
    "src/audio/audio_acoustics.py",
    "src/audio/audio_scoring.py",
    "src/audio/audio_storage.py",
]


def _import_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_audio_module_does_not_import_other_modalities() -> None:
    root = Path(__file__).resolve().parents[3]
    for relative_path in TARGET_FILES:
        file_path = root / relative_path
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        imported = _import_names(tree)
        assert imported.isdisjoint(FORBIDDEN_MODULES), (
            f"{relative_path} importa modulo proibido: {imported & FORBIDDEN_MODULES}"
        )
