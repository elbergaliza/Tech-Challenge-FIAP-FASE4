"""
ler_pdf.py
----------
Extrai texto de um arquivo PDF usando PyPDF2 ou pdfplumber.

Uso:
    python scripts/ler_pdf.py <caminho_do_pdf>
"""

from __future__ import annotations

import sys
from pathlib import Path


def _import_pdf_reader():
    try:
        import pdfplumber
        return pdfplumber, "pdfplumber"
    except ImportError:
        pass

    try:
        import PyPDF2
        return PyPDF2, "PyPDF2"
    except ImportError:
        raise RuntimeError(
            "Nenhuma biblioteca de leitura de PDF encontrada.\n"
            "Instale uma delas com:\n"
            "  pip install pdfplumber\n"
            "  ou\n"
            "  pip install PyPDF2"
        )


def extrair_texto(caminho: str) -> str:
    reader, nome = _import_pdf_reader()
    texto = ""

    if nome == "pdfplumber":
        with reader.open(caminho) as pdf:
            for pagina in pdf.pages:
                conteudo = pagina.extract_text()
                if conteudo:
                    texto += conteudo + "\n\n"
    else:
        with open(caminho, "rb") as f:
            pdf = reader.PdfReader(f)
            for pagina in pdf.pages:
                conteudo = pagina.extract_text()
                if conteudo:
                    texto += conteudo + "\n\n"

    return texto.strip()


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Uso: python scripts/ler_pdf.py <caminho_do_pdf>", file=sys.stderr)
        return 1

    caminho = Path(argv[0])
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
        return 1

    try:
        texto = extrair_texto(str(caminho))
        print(texto)
        return 0
    except Exception as exc:
        print(f"Erro ao ler PDF: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
