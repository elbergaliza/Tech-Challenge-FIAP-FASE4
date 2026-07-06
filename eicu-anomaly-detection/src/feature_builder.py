import pandas as pd
import numpy as np
import re


class ClinicalFeatureBuilder:
    """
    Cria features clínicas agregadas por patientunitstayid.
    Usa sinais vitais, exames laboratoriais e medicamentos.
    """

    def build_vital_features(self, vital_df: pd.DataFrame) -> pd.DataFrame:
        df = vital_df.copy()
        df.columns = [col.lower() for col in df.columns]

        id_col = "patientunitstayid"

        if id_col not in df.columns:
            raise ValueError(f"Coluna {id_col} não encontrada em vitalPeriodic.")

        candidate_cols = [
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
            "icp"
        ]

        vital_cols = [col for col in candidate_cols if col in df.columns]

        for col in vital_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        agg_dict = {}
        for col in vital_cols:
            agg_dict[col] = ["mean", "min", "max", "std"]

        features = df.groupby(id_col).agg(agg_dict)

        features.columns = [
            f"{col}_{stat}" for col, stat in features.columns
        ]

        features = features.reset_index()
        features = features.dropna(axis=1, how="all")

        return features

    def build_lab_features(self, lab_df: pd.DataFrame) -> pd.DataFrame:
        df = lab_df.copy()
        df.columns = [col.lower() for col in df.columns]

        id_col = "patientunitstayid"

        if id_col not in df.columns:
            raise ValueError(f"Coluna {id_col} não encontrada em lab.")

        if "labname" not in df.columns or "labresult" not in df.columns:
            raise ValueError("As colunas labname e labresult são necessárias em lab.csv.gz.")

        df["labresult"] = pd.to_numeric(df["labresult"], errors="coerce")
        df = df.dropna(subset=["labresult"])

        # Exames principais para manter o projeto simples e interpretável.
        important_labs = [
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
            "phosphate"
        ]

        df["labname_clean"] = df["labname"].astype(str).str.lower().str.strip()

        df = df[df["labname_clean"].isin(important_labs)]

        if df.empty:
            # Retorna pelo menos a lista de pacientes caso nenhum exame bata.
            return lab_df[[id_col]].drop_duplicates()

        features = df.groupby([id_col, "labname_clean"])["labresult"].agg(
            ["mean", "min", "max", "std", "count"]
        ).reset_index()

        features_pivot = features.pivot(
            index=id_col,
            columns="labname_clean"
        )

        features_pivot.columns = [
            f"lab_{self._sanitize_name(lab)}_{stat}"
            for stat, lab in features_pivot.columns
        ]

        features_pivot = features_pivot.reset_index()
        features_pivot = features_pivot.dropna(axis=1, how="all")

        return features_pivot

    def build_medication_features(self, medication_df: pd.DataFrame) -> pd.DataFrame:
        df = medication_df.copy()
        df.columns = [col.lower() for col in df.columns]

        id_col = "patientunitstayid"

        if id_col not in df.columns:
            raise ValueError(f"Coluna {id_col} não encontrada em medication.")

        if "drugname" not in df.columns:
            raise ValueError("A coluna drugname é necessária em medication.csv.gz.")

        df["drugname_clean"] = df["drugname"].astype(str).str.lower()

        # Features gerais de medicação
        base_features = df.groupby(id_col).agg(
            medication_total_count=("drugname_clean", "count"),
            medication_unique_count=("drugname_clean", "nunique")
        ).reset_index()

        # Grupos de medicamentos que podem indicar maior gravidade clínica.
        vasoactive_keywords = [
            "norepinephrine", "epinephrine", "dopamine", "dobutamine",
            "vasopressin", "phenylephrine", "levophed", "neosynephrine"
        ]

        antibiotic_keywords = [
            "vancomycin", "cefepime", "ceftriaxone", "piperacillin",
            "tazobactam", "meropenem", "levofloxacin", "ciprofloxacin",
            "azithromycin", "metronidazole"
        ]

        sedative_keywords = [
            "propofol", "midazolam", "fentanyl", "lorazepam",
            "dexmedetomidine", "morphine"
        ]

        insulin_keywords = [
            "insulin"
        ]

        df["has_vasoactive"] = df["drugname_clean"].apply(
            lambda x: self._contains_any(x, vasoactive_keywords)
        )

        df["has_antibiotic"] = df["drugname_clean"].apply(
            lambda x: self._contains_any(x, antibiotic_keywords)
        )

        df["has_sedative"] = df["drugname_clean"].apply(
            lambda x: self._contains_any(x, sedative_keywords)
        )

        df["has_insulin"] = df["drugname_clean"].apply(
            lambda x: self._contains_any(x, insulin_keywords)
        )

        group_features = df.groupby(id_col).agg(
            medication_vasoactive_count=("has_vasoactive", "sum"),
            medication_antibiotic_count=("has_antibiotic", "sum"),
            medication_sedative_count=("has_sedative", "sum"),
            medication_insulin_count=("has_insulin", "sum")
        ).reset_index()

        features = base_features.merge(group_features, on=id_col, how="left")

        return features

    def build_all_features(
        self,
        vital_df: pd.DataFrame,
        lab_df: pd.DataFrame = None,
        medication_df: pd.DataFrame = None
    ) -> pd.DataFrame:

        vital_features = self.build_vital_features(vital_df)

        final_features = vital_features.copy()

        if lab_df is not None:
            lab_features = self.build_lab_features(lab_df)
            final_features = final_features.merge(
                lab_features,
                on="patientunitstayid",
                how="left"
            )

        if medication_df is not None:
            medication_features = self.build_medication_features(medication_df)
            final_features = final_features.merge(
                medication_features,
                on="patientunitstayid",
                how="left"
            )

        final_features = final_features.dropna(axis=1, how="all")

        numeric_cols = final_features.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if col != "patientunitstayid":
                median_value = final_features[col].median()

                if pd.isna(median_value):
                    median_value = 0

                final_features[col] = final_features[col].fillna(median_value)

        return final_features

    def _contains_any(self, text: str, keywords: list) -> int:
        return int(any(keyword in text for keyword in keywords))

    def _sanitize_name(self, name: str) -> str:
        name = str(name).lower()
        name = re.sub(r"[^a-z0-9]+", "_", name)
        name = name.strip("_")
        return name


if __name__ == "__main__":
    from src.data_loader import EICUDataLoader

    print("Testando criação de features com vital + lab + medication...")

    loader = EICUDataLoader()

    vital_df = loader.load_vital_periodic()
    lab_df = loader.load_labs()
    medication_df = loader.load_medications()

    builder = ClinicalFeatureBuilder()

    features = builder.build_all_features(
        vital_df=vital_df,
        lab_df=lab_df,
        medication_df=medication_df
    )

    print("\nFeatures criadas com sucesso!")
    print(f"Quantidade de internações/pacientes: {features.shape[0]}")
    print(f"Quantidade de colunas: {features.shape[1]}")

    print("\nColunas criadas:")
    print(features.columns.tolist())

    print("\nPrimeiras linhas:")
    print(features.head())