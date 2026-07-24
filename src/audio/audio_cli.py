"""CLI do modulo de audio_texto."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv

from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import AudioPipelineError, AudioProcessingRequest

app = typer.Typer(help="Pipeline de audio para gerar alerta padronizado.")


def _latest_report_path(output_dir: Path, patient_id: str) -> Path | None:
    matches = sorted(output_dir.glob(f"{patient_id}_*_alert.json"))
    if not matches:
        return None
    return matches[-1]


@app.command("process")
def process_command(
    patient_id: str = typer.Option(..., "--patient-id"),
    audio_path: str = typer.Option(..., "--audio-path"),
    language: str = typer.Option("pt-BR", "--language"),
    output_dir: str = typer.Option("data/audio/reports", "--output-dir"),
    processed_dir: str = typer.Option("data/audio/processed", "--processed-dir"),
    max_duration_seconds: int = typer.Option(600, "--max-duration-seconds"),
    max_size_mb: int = typer.Option(50, "--max-size-mb"),
    timeout_seconds: int = typer.Option(60, "--timeout-seconds"),
) -> None:
    """Processa uma gravação e emite o caminho do relatório final."""

    load_dotenv()
    try:
        request = AudioProcessingRequest(
            patient_id=patient_id,
            audio_path=Path(audio_path),
            language=language,
            max_duration_seconds=max_duration_seconds,
            max_size_mb=max_size_mb,
            timeout_seconds=timeout_seconds,
        )
        process_audio_recording(
            request,
            output_dir=output_dir,
            processed_dir=processed_dir,
        )

        report_path = _latest_report_path(Path(output_dir), patient_id)
        if report_path is None:
            typer.echo("status=success report_path=unknown")
        else:
            typer.echo(f"status=success report_path={report_path}")
    except AudioPipelineError as exc:
        typer.echo(f"status=error error_code={exc.error_code}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo("status=error error_code=unexpected_failure")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
