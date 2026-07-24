import pandas as pd


class AlertGenerator:
    """
    Gera alertas padronizados para integração com os outros módulos.
    """

    def generate_alerts(
        self,
        predictions: pd.DataFrame,
        features: pd.DataFrame,
        id_col: str = "patientunitstayid"
    ) -> pd.DataFrame:

        df = predictions.merge(features, on=id_col, how="left")

        alerts = []

        for _, row in df.iterrows():
            if not row["is_anomaly"]:
                continue

            description = self._build_description(row)

            alert = {
                "sample_id": str(row[id_col]),
                "modulo": "anomalias_clinicas_uti",
                "tipo_anomalia": "sinais_vitais",
                "score_risco": round(float(row["risk_score"]), 3),
                "nivel_risco": row["risk_level"],
                "descricao": description,
                "recomendacao": "Reavaliar paciente e acionar equipe médica se necessário."
            }

            alerts.append(alert)

        return pd.DataFrame(alerts)

    def _build_description(self, row) -> str:
        reasons = []

        # Regras didáticas e configuráveis.
        # Não são limiares clínicos oficiais; servem para protótipo acadêmico.
        if "heartrate_max" in row and row["heartrate_max"] > 120:
         reasons.append("frequência cardíaca máxima elevada")

        if "sao2_min" in row and row["sao2_min"] < 92:
            reasons.append("queda de oxigenação")

        if "respiration_max" in row and row["respiration_max"] > 30:
            reasons.append("frequência respiratória elevada")

        if "systemicsystolic_min" in row and row["systemicsystolic_min"] < 90:
            reasons.append("pressão sistólica mínima baixa")

        if "temperature_max" in row and row["temperature_max"] > 38.5:
            reasons.append("temperatura máxima elevada")

        if "lab_lactate_max" in row and row["lab_lactate_max"] > 2:
            reasons.append("lactato elevado")

        if "lab_creatinine_max" in row and row["lab_creatinine_max"] > 1.5:
            reasons.append("creatinina elevada")

        if "lab_potassium_max" in row and row["lab_potassium_max"] > 5.5:
            reasons.append("potássio elevado")

        if "lab_potassium_min" in row and row["lab_potassium_min"] < 3.5:
            reasons.append("potássio baixo")

        if "lab_glucose_max" in row and row["lab_glucose_max"] > 180:
            reasons.append("glicose elevada")

        if "medication_vasoactive_count" in row and row["medication_vasoactive_count"] > 0:
            reasons.append("uso de medicação vasoativa")

        if "medication_antibiotic_count" in row and row["medication_antibiotic_count"] > 0:
            reasons.append("uso de antibiótico")

        if "medication_sedative_count" in row and row["medication_sedative_count"] > 0:
            reasons.append("uso de sedativo")
                
        if not reasons:
            return "Paciente apresentou padrão de sinais vitais diferente do comportamento esperado pelo modelo."

        return "Paciente apresentou " + ", ".join(reasons) + "."