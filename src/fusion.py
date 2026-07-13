import json
from pathlib import Path


class MultimodalFusion:
    """
    Combina alertas gerados pelos módulos clínico, vídeo e áudio/texto.
    A fusão é feita no nível dos alertas e scores de risco.
    """

    def __init__(self):
        pass

    def load_alerts(self, file_path: str):
        path = Path(file_path)

        if not path.exists():
            print(f"Arquivo não encontrado: {file_path}")
            return []

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def calculate_final_score(self, alerts):
        if not alerts:
            return 0.0

        scores = [float(alert["score_risco"]) for alert in alerts]
        return round(sum(scores) / len(scores), 3)

    def classify_risk(self, score):
        # Limiares de agregação da fusão (0.45 / 0.75) são independentes dos
        # limiares de cada módulo de origem (ex.: audio_texto usa 0.4 / 0.7 —
        # ver specs/001-audio-texto-pipeline/data-model.md). Não assumir que
        # os dois conjuntos de limiares precisam coincidir.
        if score >= 0.75:
            return "alto"
        elif score >= 0.45:
            return "moderado"
        return "baixo"

    def generate_final_report(self, clinical_alerts, video_alerts, audio_alerts):
        all_alerts = clinical_alerts + video_alerts + audio_alerts

        score_final = self.calculate_final_score(all_alerts)
        risco_final = self.classify_risk(score_final)

        modulos = sorted(list(set(alert["modulo"] for alert in all_alerts)))

        alertas_detectados = [
            alert["descricao"] for alert in all_alerts
        ]

        recomendacao_final = self._build_recommendation(risco_final)

        return {
            "case_id": "caso_demo_001",
            "score_final": score_final,
            "risco_final": risco_final,
            "modulos_analisados": modulos,
            "quantidade_alertas": len(all_alerts),
            "alertas_detectados": alertas_detectados,
            "recomendacao_final": recomendacao_final
        }

    def _build_recommendation(self, risco_final):
        if risco_final == "alto":
            return "Acionar equipe médica para reavaliação imediata do paciente."
        elif risco_final == "moderado":
            return "Manter paciente em observação e repetir avaliação clínica."
        return "Continuar monitoramento preventivo."


if __name__ == "__main__":
    fusion = MultimodalFusion()

    clinical_alerts = fusion.load_alerts("outputs/alerts.json")
    video_alerts = fusion.load_alerts("outputs/video_alerts.json")
    audio_alerts = fusion.load_alerts("outputs/audio_alerts.json")

    final_report = fusion.generate_final_report(
        clinical_alerts=clinical_alerts,
        video_alerts=video_alerts,
        audio_alerts=audio_alerts
    )

    output_path = Path("outputs/final_multimodal_report.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    print("Relatório multimodal final gerado:")
    print(json.dumps(final_report, ensure_ascii=False, indent=2))