"""Persistencia local para artefatos do modulo de audio."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from audio.audio_schemas import AudioAlert, TranscriptionResult

LOGGER = logging.getLogger(__name__)


def _safe_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_processed(patient_id: str, data: dict[str, Any], processed_dir: str | Path) -> Path:
    """Salva dados intermediarios sem expor conteudo clinico em logs."""

    output_dir = Path(processed_dir)
    output_path = output_dir / f"{patient_id}_{_safe_timestamp()}_processed.json"
    file_path = _write_json(output_path, data)
    LOGGER.info(
        "audio_storage_saved_processed",
        extra={"patient_id": patient_id, "path": str(file_path)},
    )
    return file_path


def save_transcription(
    patient_id: str,
    transcription_result: TranscriptionResult,
    processed_dir: str | Path,
) -> Path:
    """Persistencia de transcricao para auditoria (FR-017)."""

    output_dir = Path(processed_dir)
    payload = {
        "patient_id": patient_id,
        "transcription": transcription_result.model_dump(),
        "saved_at": _safe_timestamp(),
    }
    output_path = output_dir / f"{patient_id}_{_safe_timestamp()}_transcription.json"
    file_path = _write_json(output_path, payload)
    LOGGER.info(
        "audio_storage_saved_transcription",
        extra={"patient_id": patient_id, "path": str(file_path)},
    )
    return file_path


def save_report(alert: AudioAlert, output_dir: str | Path) -> Path:
    """Salva o alerta final em JSON."""

    report_dir = Path(output_dir)
    output_path = report_dir / f"{alert.patient_id}_{_safe_timestamp()}_alert.json"
    file_path = _write_json(output_path, alert.model_dump(mode="json"))
    LOGGER.info(
        "audio_storage_saved_report",
        extra={"patient_id": alert.patient_id, "path": str(file_path)},
    )
    return file_path
