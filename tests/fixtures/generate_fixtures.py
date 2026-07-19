"""
generate_fixtures.py
--------------------
Gera fixtures sintéticas realistas para testes locais e E2E da fusão
multimodal.

Como o eICU-CRD Demo exige conexão com o PhysioNet e o processamento de vídeo
exige MediaPipe/YOLOv8, este script cria dados mínimos que permitem rodar o
pipeline clínico e ter um vídeo MP4 válido sem depender de internet ou
pesados modelos de ML.

Fixtures geradas:
    - tests/fixtures/mock_eicu/patient.csv.gz
    - tests/fixtures/mock_eicu/vitalPeriodic.csv.gz
    - tests/fixtures/mock_eicu/vitalAperiodic.csv.gz
    - tests/fixtures/mock_eicu/lab.csv.gz
    - tests/fixtures/mock_eicu/medication.csv.gz
    - tests/fixtures/test_video.mp4

Uso:
    python tests/fixtures/generate_fixtures.py
    python tests/fixtures/generate_fixtures.py --skip-video
    python tests/fixtures/generate_fixtures.py --pacientes 20 --medicoes 50

Após gerar, rode a pipeline E2E com:
    python main.py --video tests/fixtures/test_video.mp4 \
        --eicu-data tests/fixtures/mock_eicu \
        --video-patient-id local_test
"""

from __future__ import annotations

import argparse
import gzip
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


FIXTURES_DIR = Path(__file__).resolve().parent
EICU_DIR = FIXTURES_DIR / "mock_eicu"
VIDEO_PATH = FIXTURES_DIR / "test_video.mp4"

VITAL_COLS = [
    "vitalperiodicid",
    "patientunitstayid",
    "observationoffset",
    "temperature",
    "sao2",
    "heartrate",
    "respiration",
    "cvp",
    "etco2",
    "systemicsystolic",
    "systemicdiastolic",
    "systemicmean",
    "pasystolic",
    "padiastolic",
    "pamean",
    "st1",
    "st2",
    "st3",
    "icp",
]

VITAL_RANGES = {
    "temperature": (36.0, 38.5),
    "sao2": (92.0, 100.0),
    "heartrate": (55.0, 110.0),
    "respiration": (12.0, 24.0),
    "cvp": (2.0, 12.0),
    "etco2": (25.0, 45.0),
    "systemicsystolic": (90.0, 140.0),
    "systemicdiastolic": (55.0, 90.0),
    "systemicmean": (65.0, 105.0),
    "pasystolic": (18.0, 30.0),
    "padiastolic": (8.0, 18.0),
    "pamean": (12.0, 22.0),
    "st1": (-1.0, 2.0),
    "st2": (-1.0, 2.0),
    "st3": (-1.0, 2.0),
    "icp": (5.0, 15.0),
}

LAB_NAMES = [
    "creatinine",
    "bun",
    "glucose",
    "sodium",
    "potassium",
    "chloride",
    "bicarbonate",
    "hemoglobin",
    "hematocrit",
    "platelets x 1000",
    "wbc x 1000",
    "lactate",
    "albumin",
    "calcium",
    "magnesium",
    "phosphate",
]

LAB_RANGES = {
    "creatinine": (0.6, 1.4),
    "bun": (7, 20),
    "glucose": (70, 140),
    "sodium": (135, 145),
    "potassium": (3.5, 5.0),
    "chloride": (95, 105),
    "bicarbonate": (22, 30),
    "hemoglobin": (11, 16),
    "hematocrit": (33, 50),
    "platelets x 1000": (150, 450),
    "wbc x 1000": (4, 11),
    "lactate": (0.5, 2.0),
    "albumin": (3.0, 5.0),
    "calcium": (8.5, 10.5),
    "magnesium": (1.7, 2.2),
    "phosphate": (2.5, 4.5),
}

DRUG_NAMES = [
    "ASPIRIN EC 81 MG PO TBEC",
    "WARFARIN SODIUM 5 MG PO TABS",
    "PROPOFOL 10 MG/ML IV EMUL",
    "FENTANYL CITRATE 50 MCG/ML INJ",
    "NOREPINEPHRINE 4 MG/250ML NS IV",
    "VANCOMYCIN 1 GM IV",
    "INSULIN REGULAR 100 UNITS/ML INJ",
    "METOPROLOL TARTRATE 50 MG PO TABS",
    "CEFEPIME 2 G IV",
    "PIPERACILLIN 4 GM/TAZOBACTAM 0.5 GM IV",
]


def _save_gz(df: pd.DataFrame, path: Path) -> None:
    """Salva DataFrame como CSV gzip."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        df.to_csv(f, index=False)


def _generate_patient_csv(n_patients: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(n_patients):
        pid = 141760 + i
        rows.append(
            {
                "patientunitstayid": pid,
                "patienthealthsystemstayid": pid,
                "gender": random.choice(["Male", "Female"]),
                "age": int(rng.integers(18, 90)),
                "ethnicity": "Unknown",
                "hospitalid": 1,
                "wardid": 1,
                "apacheadmissiondx": "Mock diagnosis",
                "admissionheight": float(rng.uniform(150, 190)),
                "admissionweight": float(rng.uniform(50, 120)),
                "dischargeweight": float(rng.uniform(50, 120)),
                "hospitaldischargestatus": random.choice(["Alive", "Expired"]),
                "unitdischargestatus": random.choice(["Alive", "Expired"]),
            }
        )
    return pd.DataFrame(rows)


def _generate_vital_periodic(
    n_patients: int, n_measurements: int, rng: np.random.Generator
) -> pd.DataFrame:
    rows = []
    vital_id = 1
    anomaly_patients = set(rng.choice(n_patients, size=max(2, n_patients // 4), replace=False))

    for p_idx in range(n_patients):
        pid = 141760 + p_idx
        is_anomaly = p_idx in anomaly_patients
        for m in range(n_measurements):
            offset = m * 60  # minutos
            row: dict[str, object] = {
                "vitalperiodicid": vital_id,
                "patientunitstayid": pid,
                "observationoffset": offset,
            }
            for col, (lo, hi) in VITAL_RANGES.items():
                if rng.random() < 0.05:
                    row[col] = ""
                    continue

                value = float(rng.uniform(lo, hi))

                if is_anomaly and rng.random() < 0.20:
                    if col == "heartrate":
                        value = float(rng.uniform(140, 180))
                    elif col == "sao2":
                        value = float(rng.uniform(70, 88))
                    elif col == "systemicsystolic":
                        value = float(rng.uniform(70, 85))
                    elif col == "respiration":
                        value = float(rng.uniform(30, 45))
                    elif col == "temperature":
                        value = float(rng.uniform(39.0, 41.0))

                row[col] = round(value, 2)

            rows.append(row)
            vital_id += 1

    return pd.DataFrame(rows, columns=VITAL_COLS)


def _generate_vital_aperiodic(
    n_patients: int, n_measurements: int, rng: np.random.Generator
) -> pd.DataFrame:
    rows = []
    for p_idx in range(n_patients):
        pid = 141760 + p_idx
        for m in range(n_measurements):
            rows.append(
                {
                    "vitalaperiodicid": len(rows) + 1,
                    "patientunitstayid": pid,
                    "observationoffset": m * 120,
                    "noninvasivesystolic": int(rng.integers(90, 140)),
                    "noninvasivediastolic": int(rng.integers(55, 90)),
                    "noninvasivemean": int(rng.integers(65, 105)),
                    "paop": "",
                    "cardiacoutput": "",
                    "cardiacinput": "",
                    "svr": "",
                    "svri": "",
                    "pvr": "",
                    "pvri": "",
                }
            )
    return pd.DataFrame(rows)


def _generate_lab_csv(n_patients: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    lab_id = 1
    for p_idx in range(n_patients):
        pid = 141760 + p_idx
        for lab_name in LAB_NAMES:
            value = round(float(rng.uniform(*LAB_RANGES[lab_name])), 4)
            rows.append(
                {
                    "labid": lab_id,
                    "patientunitstayid": pid,
                    "labresultoffset": 0,
                    "labtypeid": 3,
                    "labname": lab_name,
                    "labresult": value,
                    "labresulttext": str(value),
                    "labmeasurenamesystem": "",
                    "labmeasurenameinterface": "",
                    "labresultrevisedoffset": 0,
                }
            )
            lab_id += 1
    return pd.DataFrame(rows)


def _generate_medication_csv(n_patients: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    med_id = 1
    for p_idx in range(n_patients):
        pid = 141760 + p_idx
        n_meds = int(rng.integers(1, 5))
        for _ in range(n_meds):
            drug = rng.choice(DRUG_NAMES)
            rows.append(
                {
                    "medicationid": med_id,
                    "patientunitstayid": pid,
                    "drugorderoffset": 0,
                    "drugstartoffset": 0,
                    "drugivadmixture": "No",
                    "drugordercancelled": "No",
                    "drugname": drug,
                    "drughiclseqno": 0,
                    "dosage": "1",
                    "routeadmin": "PO",
                    "frequency": "Daily",
                    "loadingdose": "",
                    "prn": "No",
                    "drugstopoffset": 1440,
                    "gtc": 0,
                }
            )
            med_id += 1
    return pd.DataFrame(rows)


def _generate_video() -> None:
    """Gera um MP4 curto (10s, 320x240, 10fps) com uma pessoa se movendo.

    Usa OpenCV (já dependência do projeto) em vez de ffmpeg, para que o
    gerador funcione em ambientes sem ffmpeg instalado, como runners de CI.
    """
    import cv2
    import numpy as np

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    width, height, fps, duration = 320, 240, 10, 10
    total_frames = fps * duration
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(VIDEO_PATH), fourcc, float(fps), (width, height))

    if not out.isOpened():
        raise RuntimeError(f"Não foi possível abrir VideoWriter para {VIDEO_PATH}")

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Retângulo branco simulando uma pessoa se movendo da esquerda para a direita.
        box_w, box_h = 40, 80
        x = int((t / duration) * (width - box_w)) % (width - box_w)
        y = (height - box_h) // 2
        cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), (255, 255, 255), -1)

        # Texto informativo.
        cv2.putText(
            frame,
            "Person moving",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        out.write(frame)

    out.release()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera fixtures sintéticas para testes locais e E2E.",
    )
    parser.add_argument(
        "--pacientes",
        type=int,
        default=10,
        help="Número de pacientes/estadias a gerar (default: 10)",
    )
    parser.add_argument(
        "--medicoes",
        type=int,
        default=100,
        help="Número de medições vitais por paciente (default: 100)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed para reprodutibilidade (default: 42)",
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Não gerar o vídeo MP4 (útil se ffmpeg não estiver disponível)",
    )
    parser.add_argument(
        "--only-video",
        action="store_true",
        help="Gerar apenas o vídeo MP4",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    rng = np.random.default_rng(args.seed)

    if not args.only_video:
        print(f"Gerando mock eICU em: {EICU_DIR}")
        print(f"  Pacientes: {args.pacientes}")
        print(f"  Medições por paciente: {args.medicoes}")

        patient_df = _generate_patient_csv(args.pacientes, rng)
        vital_df = _generate_vital_periodic(args.pacientes, args.medicoes, rng)
        aperiodic_df = _generate_vital_aperiodic(
            args.pacientes, max(1, args.medicoes // 10), rng
        )
        lab_df = _generate_lab_csv(args.pacientes, rng)
        medication_df = _generate_medication_csv(args.pacientes, rng)

        _save_gz(patient_df, EICU_DIR / "patient.csv.gz")
        _save_gz(vital_df, EICU_DIR / "vitalPeriodic.csv.gz")
        _save_gz(aperiodic_df, EICU_DIR / "vitalAperiodic.csv.gz")
        _save_gz(lab_df, EICU_DIR / "lab.csv.gz")
        _save_gz(medication_df, EICU_DIR / "medication.csv.gz")

        for nome in ["patient.csv.gz", "vitalPeriodic.csv.gz", "vitalAperiodic.csv.gz", "lab.csv.gz", "medication.csv.gz"]:
            path = EICU_DIR / nome
            size_kb = path.stat().st_size / 1024
            print(f"  ✓ {nome} ({size_kb:.1f} KB)")

        print("Mock eICU gerado com sucesso.")
        print()
        print("Para rodar a pipeline localmente:")
        print(
            "  python main.py --video tests/fixtures/test_video.mp4 "
            "--eicu-data tests/fixtures/mock_eicu "
            "--video-patient-id local_test"
        )

    if not args.skip_video:
        print("Gerando vídeo fixture...")
        _generate_video()
        print(f"  ✓ {VIDEO_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
