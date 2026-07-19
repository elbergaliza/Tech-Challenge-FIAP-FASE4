"""
Helpers de entrada/saída para o módulo de fusão multimodal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def salvar_relatorio(relatorio: dict[str, Any], caminho: str | Path) -> Path:
    """Salva o relatório final em JSON UTF-8, criando diretórios se necessário."""
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)
    return path
