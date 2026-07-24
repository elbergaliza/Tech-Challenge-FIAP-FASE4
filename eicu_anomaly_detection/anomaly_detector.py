import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from . import config


class ClinicalAnomalyDetector:
    """
    Detector de anomalias clínicas usando Isolation Forest.
    """

    def __init__(self):
        self.model = Pipeline(steps=[
            ("scaler", StandardScaler()),
            ("isolation_forest", IsolationForest(
                n_estimators=200,
                contamination=0.10,
                random_state=config.RANDOM_STATE
            ))
        ])

    def train(self, features: pd.DataFrame, id_col: str = "patientunitstayid"):
        X = features.drop(columns=[id_col], errors="ignore")
        self.model.fit(X)
        return self

    def predict(self, features: pd.DataFrame, id_col: str = "patientunitstayid") -> pd.DataFrame:
        X = features.drop(columns=[id_col], errors="ignore")

        # IsolationForest retorna:
        #  1 = normal
        # -1 = anomalia
        predictions = self.model.predict(X)

        # Quanto menor o score bruto, mais anômalo.
        raw_scores = self.model.decision_function(X)

        result = features[[id_col]].copy()
        result["prediction"] = predictions
        result["is_anomaly"] = result["prediction"] == -1

        # Normaliza score para 0 a 1.
        # Aqui, 1 significa maior risco.
        min_score = raw_scores.min()
        max_score = raw_scores.max()

        if max_score == min_score:
            risk_score = [0.5] * len(raw_scores)
        else:
            risk_score = 1 - ((raw_scores - min_score) / (max_score - min_score))

        result["risk_score"] = risk_score
        result["risk_level"] = result["risk_score"].apply(self._risk_level)

        return result

    def _risk_level(self, score: float) -> str:
        if score >= 0.75:
            return "alto"
        elif score >= 0.45:
            return "moderado"
        return "baixo"

    def save(self, path=None):
        if path is None:
            path = config.MODELS_DIR / "clinical_anomaly_detector.joblib"
        joblib.dump(self.model, path)

    def load(self, path=None):
        if path is None:
            path = config.MODELS_DIR / "clinical_anomaly_detector.joblib"
        self.model = joblib.load(path)
        return self