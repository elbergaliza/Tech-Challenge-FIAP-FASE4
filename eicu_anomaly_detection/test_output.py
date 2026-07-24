import pandas as pd
import json


def main():
    print("=== TESTE DO MÓDULO DE ANOMALIAS CLÍNICAS ===")

    features = pd.read_csv("data/processed/vital_features.csv")
    predictions = pd.read_csv("outputs/predictions.csv")
    alerts = pd.read_csv("outputs/alerts.csv")

    print(f"\nTotal de internações processadas: {len(features)}")
    print(f"Total de predições geradas: {len(predictions)}")
    print(f"Total de alertas gerados: {len(alerts)}")

    print("\nDistribuição dos níveis de risco:")
    print(predictions["risk_level"].value_counts())

    print("\nPrimeiros alertas:")
    print(alerts.head(10))

    print("\nExemplo em JSON:")

    with open("outputs/alerts.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print(json.dumps(data[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()