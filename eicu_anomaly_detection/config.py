from pathlib import Path

# Após refatoração, o pacote eicu_anomaly_detection fica na raiz do repo.
# Os dados continuam em eicu-anomaly-detection/modulo_anomalias/.
BASE_DIR = Path(__file__).resolve().parents[1]

DATA_RAW_DIR = BASE_DIR / "eicu-anomaly-detection" / "modulo_anomalias" / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "eicu-anomaly-detection" / "modulo_anomalias" / "data" / "processed"
MODELS_DIR = BASE_DIR / "eicu-anomaly-detection" / "modulo_anomalias" / "models"
OUTPUTS_DIR = BASE_DIR / "eicu-anomaly-detection" / "modulo_anomalias" / "outputs"

PATIENT_FILE = DATA_RAW_DIR / "patient.csv.gz"
VITAL_PERIODIC_FILE = DATA_RAW_DIR / "vitalPeriodic.csv.gz"
VITAL_APERIODIC_FILE = DATA_RAW_DIR / "vitalAperiodic.csv.gz"
LAB_FILE = DATA_RAW_DIR / "lab.csv.gz"
MEDICATION_FILE = DATA_RAW_DIR / "medication.csv.gz"

RANDOM_STATE = 42