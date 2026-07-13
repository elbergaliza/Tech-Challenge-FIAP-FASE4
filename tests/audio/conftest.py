"""Fixtures compartilhadas para testes do modulo de audio."""

from __future__ import annotations

import math
import wave
from pathlib import Path

import pytest


def create_wav_file(
    path: Path,
    *,
    duration_seconds: float = 1.0,
    sample_rate: int = 16_000,
    amplitude: float = 0.2,
    include_bursts: bool = False,
    include_long_pauses: bool = False,
) -> Path:
    """Cria um WAV mono de 16 bits para testes."""

    total_samples = int(duration_seconds * sample_rate)
    max_value = 32767
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for index in range(total_samples):
            time_position = index / sample_rate

            if include_long_pauses and int(time_position) % 4 in {2, 3}:
                value = 0.0
            else:
                value = amplitude * math.sin(2 * math.pi * 220 * time_position)
                if include_bursts and index % 800 < 120:
                    value = 0.95

            integer_value = int(max(-1.0, min(1.0, value)) * max_value)
            wav_file.writeframesraw(integer_value.to_bytes(2, byteorder="little", signed=True))

    return path


@pytest.fixture
def audio_tmp_dir(tmp_path: Path) -> Path:
    """Diretorio temporario para audio de teste."""

    directory = tmp_path / "audio"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
