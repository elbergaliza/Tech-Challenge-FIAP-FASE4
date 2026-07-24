from . import config
from .alert_generator import AlertGenerator
from .anomaly_detector import ClinicalAnomalyDetector
from .data_loader import EICUDataLoader
from .feature_builder import ClinicalFeatureBuilder


def main():
    print("Carregando dados do eICU-CRD Demo...")

    loader = EICUDataLoader()
    vital_df = loader.load_vital_periodic()

    print(f"VitalPeriodic carregado: {vital_df.shape[0]} linhas, {vital_df.shape[1]} colunas")

    print("Criando features clínicas...")
    builder = ClinicalFeatureBuilder()
    features = builder.build_vital_features(vital_df)

    print(f"Features criadas: {features.shape[0]} pacientes/internações, {features.shape[1]} colunas")

    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    features_path = config.DATA_PROCESSED_DIR / "vital_features.csv"
    features.to_csv(features_path, index=False)

    print(f"Features salvas em: {features_path}")

    print("Treinando modelo de detecção de anomalias...")
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    detector = ClinicalAnomalyDetector()
    detector.train(features)
    detector.save()

    print("Modelo salvo em models/clinical_anomaly_detector.joblib")

    print("Gerando predições...")
    predictions = detector.predict(features)

    predictions_path = config.OUTPUTS_DIR / "predictions.csv"
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(predictions_path, index=False)

    print(f"Predições salvas em: {predictions_path}")

    print("Gerando alertas...")
    alert_generator = AlertGenerator()
    alerts = alert_generator.generate_alerts(predictions, features)

    alerts_path = config.OUTPUTS_DIR / "alerts.csv"
    alerts_json_path = config.OUTPUTS_DIR / "alerts.json"

    alerts.to_csv(alerts_path, index=False)
    alerts.to_json(alerts_json_path, orient="records", force_ascii=False, indent=2)

    print(f"Alertas CSV salvos em: {alerts_path}")
    print(f"Alertas JSON salvos em: {alerts_json_path}")

    print("Resumo:")
    print(predictions["risk_level"].value_counts())
    print(f"Total de alertas gerados: {len(alerts)}")


if __name__ == "__main__":
    main()