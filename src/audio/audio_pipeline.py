"""Orquestracao ponta a ponta do modulo de audio_texto."""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from moviepy import VideoFileClip
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from src.audio.audio_acoustics import analyze_acoustic_features
from src.audio.audio_azure import analyze_text_findings, transcribe_audio
from src.audio.audio_schemas import (
    AudioAlert,
    AudioMetadata,
    AudioPipelineError,
    AudioProcessingRequest,
    ErrorCode,
    SentimentLabel,
    TextFindings,
    TranscriptionResult,
)
from src.audio.audio_scoring import apply_textual_effective_score, build_audio_alert
from src.audio.audio_storage import save_processed, save_report, save_transcription

LOGGER = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def _log_stage(patient_id: str, stage: str, status: str, **fields: object) -> None:
    payload = {"patient_id": patient_id, "stage": stage, "status": status, **fields}
    LOGGER.info("audio_pipeline_stage", extra=payload)


def _validate_request(request: AudioProcessingRequest) -> Path:
    patient_id = request.patient_id.strip()
    if not patient_id:
        raise AudioPipelineError(ErrorCode.INVALID_PATIENT_ID, "patient_id nao pode ser vazio.")

    path = Path(request.audio_path)
    if not path.exists():
        raise AudioPipelineError(ErrorCode.FILE_NOT_FOUND, f"Arquivo nao encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS:
        raise AudioPipelineError(
            ErrorCode.UNSUPPORTED_FORMAT,
            f"Formato nao suportado: {suffix or 'desconhecido'}",
        )

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb <= 0:
        raise AudioPipelineError(ErrorCode.CORRUPTED_AUDIO, "Arquivo de audio vazio.")
    if size_mb > request.max_size_mb:
        raise AudioPipelineError(
            ErrorCode.FILE_TOO_LARGE,
            f"Arquivo excede max_size_mb={request.max_size_mb}.",
        )

    return path


def _preprocess_if_video(path: Path) -> tuple[Path, TemporaryDirectory | None]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        return path, None

    temporary_dir = TemporaryDirectory(prefix="audio_preprocess_")
    output_file = Path(temporary_dir.name) / f"{path.stem}.wav"
    with VideoFileClip(str(path)) as clip:
        if clip.audio is None:
            raise AudioPipelineError(ErrorCode.CORRUPTED_AUDIO, "Video sem faixa de audio valida.")
        clip.audio.write_audiofile(str(output_file), logger=None)
    return output_file, temporary_dir


def _extract_metadata(path: Path, max_duration_seconds: int, max_size_mb: int) -> AudioMetadata:
    try:
        segment = AudioSegment.from_file(path)
    except CouldntDecodeError as exc:
        raise AudioPipelineError(ErrorCode.CORRUPTED_AUDIO, "Arquivo de audio corrompido.") from exc

    duration_seconds = len(segment) / 1000
    if duration_seconds <= 0:
        raise AudioPipelineError(ErrorCode.CORRUPTED_AUDIO, "Arquivo de audio invalido ou vazio.")
    if duration_seconds > max_duration_seconds:
        raise AudioPipelineError(
            ErrorCode.DURATION_TOO_LONG,
            f"Duracao acima de max_duration_seconds={max_duration_seconds}.",
        )

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise AudioPipelineError(
            ErrorCode.FILE_TOO_LARGE,
            f"Arquivo excede max_size_mb={max_size_mb}.",
        )

    suffix = path.suffix.lower()
    output_format = "wav" if suffix in {".wav", ".mp4", ".avi", ".mov", ".mkv"} else "mp3"

    return AudioMetadata(
        duration_seconds=duration_seconds,
        size_mb=size_mb,
        format=output_format,
        sample_rate_hz=segment.frame_rate,
        channels=segment.channels,
    )


def process_audio_recording(
    request: AudioProcessingRequest,
    *,
    output_dir: str | Path = "data/audio/reports",
    processed_dir: str | Path = "data/audio/processed",
) -> AudioAlert:
    """Processa uma gravacao e retorna um `AudioAlert` valido."""

    started_at = perf_counter()
    temp_dir: TemporaryDirectory | None = None
    patient_id = request.patient_id
    _log_stage(patient_id, stage="received", status="start")
    try:
        source_path = _validate_request(request)
        _log_stage(patient_id, stage="input_validated", status="ok")

        working_audio_path, temp_dir = _preprocess_if_video(source_path)
        _log_stage(
            patient_id,
            stage="audio_preprocessed",
            status="ok",
            extension=working_audio_path.suffix.lower(),
        )

        metadata = _extract_metadata(
            working_audio_path,
            max_duration_seconds=request.max_duration_seconds,
            max_size_mb=request.max_size_mb,
        )
        _log_stage(
            patient_id,
            stage="metadata_extracted",
            status="ok",
            duration_seconds=round(metadata.duration_seconds, 3),
        )

        transcription: TranscriptionResult = transcribe_audio(
            working_audio_path,
            language=request.language,
        )
        _log_stage(
            patient_id,
            stage="transcribed",
            status=transcription.status.value,
            confidence=transcription.confidence,
        )

        if transcription.text.strip():
            text_findings = analyze_text_findings(transcription.text, language=request.language)
        else:
            text_findings = TextFindings(sentiment=SentimentLabel.UNKNOWN)

        text_findings = apply_textual_effective_score(text_findings, transcription.confidence)
        _log_stage(
            patient_id,
            stage="text_analyzed",
            status="ok",
            critical_terms_count=len(text_findings.critical_terms),
        )

        acoustic_features = analyze_acoustic_features(working_audio_path)
        _log_stage(
            patient_id,
            stage="acoustic_analyzed",
            status="ok",
            score_acustico=acoustic_features.score_acustico,
        )

        processing_duration_ms = (perf_counter() - started_at) * 1000
        alert = build_audio_alert(
            patient_id=patient_id,
            acoustic_features=acoustic_features,
            text_findings=text_findings,
            transcription_result=transcription,
            processing_duration_ms=processing_duration_ms,
            timeout_seconds=request.timeout_seconds,
        )

        save_transcription(patient_id, transcription, processed_dir)
        save_processed(
            patient_id,
            {
                "metadata": metadata.model_dump(mode="json"),
                "transcription": transcription.model_dump(mode="json"),
                "text_findings": text_findings.model_dump(mode="json"),
                "acoustic_features": acoustic_features.model_dump(mode="json"),
            },
            processed_dir,
        )
        report_path = save_report(alert, output_dir)

        _log_stage(
            patient_id,
            stage="persisted",
            status="ok",
            report_path=str(report_path),
            score_risco=alert.score_risco,
            duracao_processamento_ms=processing_duration_ms,
        )

        if alert.evidencias and alert.evidencias.excedeu_limite_latencia:
            _log_stage(
                patient_id,
                stage="performance",
                status="performance_timeout",
                timeout_seconds=request.timeout_seconds,
            )

        return alert

    except AudioPipelineError as error:
        _log_stage(
            patient_id,
            stage="rejected",
            status="error",
            error_code=error.error_code,
        )
        raise
    except Exception as exc:
        _log_stage(patient_id, stage="failed", status="error", error_code="unhandled_exception")
        raise AudioPipelineError(
            ErrorCode.CORRUPTED_AUDIO,
            "Falha nao tratada ao processar o audio.",
        ) from exc
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
