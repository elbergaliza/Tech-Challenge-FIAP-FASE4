#!/usr/bin/env bash
# prepare_audio_sample.sh
# Baixa 1 arquivo do dataset deepgram-diarized-272, corta só a fala do
# paciente e exporta como WAV pronto para o pipeline de áudio.
#
# Uso:
#   bash scripts/prepare_audio_sample.sh [AUDIO_FILE]
#
# Exemplos:
#   bash scripts/prepare_audio_sample.sh          # usa RES0001 (padrão)
#   bash scripts/prepare_audio_sample.sh RES0042
#   bash scripts/prepare_audio_sample.sh MSK0001

set -euo pipefail

AUDIO_FILE="${1:-RES0001}"
AUDIO_DIR="data/audio/deepgram"

echo "========================================"
echo " Dataset: deepgram-diarized-272"
echo " Arquivo: ${AUDIO_FILE}"
echo " Saída:   ${AUDIO_DIR}/${AUDIO_FILE}_patient_only.wav"
echo "========================================"

uv run python - <<EOF
import os, json
from pathlib import Path
from pydub import AudioSegment
from huggingface_hub import hf_hub_download

DATASET_ID  = "wmatbooth/medical-conversation-deepgram-diarized-272"
AUDIO_FILE  = "${AUDIO_FILE}"
AUDIO_DIR   = "${AUDIO_DIR}"
os.makedirs(AUDIO_DIR, exist_ok=True)

print(f"[1/4] Baixando {AUDIO_FILE}.mp3 ...")
mp3_path = hf_hub_download(
    repo_id=DATASET_ID,
    repo_type="dataset",
    filename=f"audio/{AUDIO_FILE}.mp3",
    local_dir=AUDIO_DIR,
)
print(f"      → {mp3_path}")

print(f"[2/4] Baixando diarização {AUDIO_FILE}.json ...")
conv_json_path = hf_hub_download(
    repo_id=DATASET_ID,
    repo_type="dataset",
    filename=f"deepgram/conversation_json/{AUDIO_FILE}.json",
    local_dir=AUDIO_DIR,
)
print(f"      → {conv_json_path}")

print("[3/4] Identificando speaker do paciente ...")
with open(conv_json_path) as f:
    raw = json.load(f)

# suporta tanto lista plana quanto {"turns": [...]}
turns = raw["turns"] if isinstance(raw, dict) else raw

speaker_duration: dict[int, float] = {}
for turn in turns:
    spk = turn.get("speaker", 0)
    dur = turn.get("end", 0) - turn.get("start", 0)
    speaker_duration[spk] = speaker_duration.get(spk, 0) + dur

patient_speaker = min(speaker_duration, key=speaker_duration.get)
print(f"      Speakers detectados: {speaker_duration}")
print(f"      Paciente = speaker {patient_speaker} (menor tempo de fala)")

patient_turns = [t for t in turns if t.get("speaker") == patient_speaker]
print(f"      Segmentos do paciente: {len(patient_turns)}")
for t in patient_turns[:5]:
    print(f"        [{t['start']:.1f}s → {t['end']:.1f}s] {t.get('transcript','')[:80]}")
if len(patient_turns) > 5:
    print(f"        ... (+{len(patient_turns)-5} segmentos)")

print("[4/4] Cortando e exportando WAV ...")
full_audio = AudioSegment.from_mp3(mp3_path)
print(f"      Duração total do MP3: {len(full_audio)/1000:.1f}s")

patient_audio = AudioSegment.empty()
for turn in patient_turns:
    patient_audio += full_audio[int(turn["start"]*1000):int(turn["end"]*1000)]

patient_wav = f"{AUDIO_DIR}/{AUDIO_FILE}_patient_only.wav"
patient_audio.export(patient_wav, format="wav")

duration_s = len(patient_audio) / 1000
size_kb    = Path(patient_wav).stat().st_size / 1024
print(f"      WAV exportado: {patient_wav}")
print(f"      Duração: {duration_s:.1f}s | Tamanho: {size_kb:.1f} KB")

print()
print("Para processar no pipeline:")
print(f"  uv run python main.py --audio {patient_wav} --audio-language en-US --video <video> --eicu-data <eicu>")
EOF
