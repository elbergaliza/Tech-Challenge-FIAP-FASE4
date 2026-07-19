"""
Base e utilitários para adapters de módulos externos.

Todo adapter deve implementar ``run(**kwargs)`` e retornar uma lista de
``AlertaNormalizado`` para participar da fusão multimodal.
"""

from __future__ import annotations

import importlib.util
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Any

from fusion.core.schema import AlertaNormalizado


class ModuleAdapter(ABC):
    """Contrato que todo módulo deve cumprir para participar da fusão."""

    @abstractmethod
    def run(self, **kwargs: Any) -> list[AlertaNormalizado]:
        """Executa o módulo e retorna alertas no schema unificado."""
        raise NotImplementedError


def load_module_from_path(module_path: Path, package: str) -> ModuleType:
    """Carrega um módulo Python pelo caminho absoluto sem depender de sys.path."""
    module_name = f"{package}.{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_package_from_path(package_name: str, package_dir: Path) -> ModuleType:
    """Carrega um pacote Python pelo caminho absoluto como um namespace temporário."""
    init_file = package_dir / "__init__.py"
    pkg_spec = importlib.util.spec_from_file_location(
        package_name,
        init_file,
        submodule_search_locations=[str(package_dir)],
    )
    if pkg_spec is None or pkg_spec.loader is None:
        raise ImportError(f"Não foi possível carregar pacote {package_dir}")
    pkg = importlib.util.module_from_spec(pkg_spec)
    sys.modules[package_name] = pkg
    pkg_spec.loader.exec_module(pkg)
    return pkg


def expose_as_src(namespace: str, pkg: ModuleType) -> dict[str, ModuleType]:
    """
    Expõe os módulos de `namespace.*` também como `src.*` para compatibilidade
    com importações absolutas internas dos módulos legados.

    Retorna os módulos `src.*` originalmente presentes para restauração posterior.
    """
    original_modules: dict[str, ModuleType] = {}
    for mod_name in list(sys.modules.keys()):
        if mod_name == "src" or mod_name.startswith("src."):
            original_modules[mod_name] = sys.modules.pop(mod_name)

    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith(f"{namespace}."):
            src_name = "src." + mod_name.split(".", 1)[1]
            sys.modules[src_name] = sys.modules[mod_name]

    sys.modules["src"] = pkg
    return original_modules


def restore_src_modules(original_modules: dict[str, ModuleType]) -> None:
    """Restaura os módulos `src.*` salvos por `expose_as_src`."""
    for mod_name in list(sys.modules.keys()):
        if mod_name == "src" or mod_name.startswith("src."):
            sys.modules.pop(mod_name, None)
    for mod_name, mod in original_modules.items():
        sys.modules[mod_name] = mod
