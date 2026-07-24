"""
main.py
-------
Ponto de entrada único da fusão multimodal.

Executa os módulos clínico e de vídeo, consolida os alertas e gera o
relatório final ``outputs/final_multimodal_report.json``.

Exemplos de uso:

    # Modo padrão: pipeline clínico em lote + vídeo
    python main.py --video modulo_video/data/entrada/sessao01.mp4

    # Filtrar paciente clínico específico + ID de vídeo customizado
    python main.py --video sessao.mp4 \
        --clinical-patient-id 141765 \
        --video-patient-id p001

    # Sem YOLOv8 (máquina fraca)
    python main.py --video sessao.mp4 --sem-objetos

    # Saída alternativa
    python main.py --video sessao.mp4 --saida meu_relatorio.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Garante que os pacotes na raiz do repositório sejam encontrados,
# mesmo quando main.py é executado de outro diretório (ex.: no Colab).
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fusion.adapters.audio.adapter import AudioAdapter
from fusion.adapters.clinical.adapter import ClinicalAdapter
from fusion.adapters.video.adapter import VideoAdapter
from fusion.core.fusion import MultimodalFusion
from fusion.io import salvar_relatorio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fusão multimodal de alertas clínicos e de vídeo.",
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Caminho do vídeo MP4 para o módulo de vídeo",
    )
    parser.add_argument(
        "--clinical-patient-id",
        default=None,
        help="ID do paciente no eICU para filtrar alertas clínicos (modo lote se omitido)",
    )
    parser.add_argument(
        "--video-patient-id",
        default="video_001",
        help="ID da sessão de vídeo (default: video_001)",
    )
    parser.add_argument(
        "--audio",
        default=None,
        help="Caminho do áudio para o módulo de áudio/texto",
    )
    parser.add_argument(
        "--audio-language",
        default="pt-BR",
        choices=["pt-BR", "en-US", "en-GB"],
        help="Idioma do áudio para transcrição (default: pt-BR)",
    )
    parser.add_argument(
        "--eicu-data",
        default="eicu-anomaly-detection/modulo_anomalias/data/raw/",
        help="Diretório com os arquivos CSV do eICU Demo",
    )
    parser.add_argument(
        "--saida",
        default="outputs/final_multimodal_report.json",
        help="Caminho para salvar o relatório final",
    )
    parser.add_argument(
        "--sem-objetos",
        action="store_true",
        help="Desativa detecção YOLOv8 no módulo de vídeo",
    )
    parser.add_argument(
        "--silencioso",
        action="store_true",
        help="Suprime logs dos módulos",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Arquivo de vídeo não encontrado: {video_path}", file=sys.stderr)
        return 1

    eicu_data_dir = Path(args.eicu_data)
    arquivos_eicu = [
        eicu_data_dir / "vitalPeriodic.csv.gz",
        eicu_data_dir / "lab.csv.gz",
        eicu_data_dir / "medication.csv.gz",
    ]
    if not all(f.exists() for f in arquivos_eicu):
        print(
            "Dados do eICU Demo não encontrados em:\n"
            f"  {eicu_data_dir}\n\n"
            "Execute o download com:\n"
            "  python scripts/download_eicu_demo.py",
            file=sys.stderr,
        )
        return 1

    if not args.silencioso:
        print("=" * 60)
        print(" Fusão Multimodal — Tech Challenge FIAP Fase 4")
        print("=" * 60)
        print()

    print(f"[main] Dados eICU: {eicu_data_dir}")
    print(f"[main] Vídeo: {video_path}")
    print(f"[main] Clinical patient id: {args.clinical_patient_id}")
    print(f"[main] Video patient id: {args.video_patient_id}")

    fusion = MultimodalFusion()
    fusion.register(
        ClinicalAdapter(
            data_dir=eicu_data_dir,
            patient_id=args.clinical_patient_id,
        )
    )
    fusion.register(
        VideoAdapter(
            video_path=str(video_path),
            patient_id=args.video_patient_id,
            sem_objetos=args.sem_objetos,
            silencioso=args.silencioso,
        )
    )
    if args.audio:
        audio_path = Path(args.audio)
        audio_patient_id = audio_path.stem
        fusion.register(
            AudioAdapter(
                audio_path=args.audio,
                patient_id=audio_patient_id,
                language=args.audio_language,
            )
        )

    try:
        relatorio = fusion.execute()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Erro durante a fusão: {exc}", file=sys.stderr)
        return 1

    saida = salvar_relatorio(relatorio, args.saida)

    print(f"Relatório salvo em: {saida}")
    print()
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
