from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
OUTPUTS_DIR = BASE_DIR / "outputs"

PATIENT_FILE = DATA_RAW_DIR / "patient.csv.gz"
VITAL_PERIODIC_FILE = DATA_RAW_DIR / "vitalPeriodic.csv.gz"
VITAL_APERIODIC_FILE = DATA_RAW_DIR / "vitalAperiodic.csv.gz"
LAB_FILE = DATA_RAW_DIR / "lab.csv.gz"
MEDICATION_FILE = DATA_RAW_DIR / "medication.csv.gz"

RANDOM_STATE = 42