import pandas as pd
from . import config


class EICUDataLoader:
    """
    Carrega os arquivos principais do eICU-CRD Demo.
    """

    def load_patients(self) -> pd.DataFrame:
        return pd.read_csv(config.PATIENT_FILE)

    def load_vital_periodic(self) -> pd.DataFrame:
        return pd.read_csv(config.VITAL_PERIODIC_FILE)

    def load_vital_aperiodic(self) -> pd.DataFrame:
        return pd.read_csv(config.VITAL_APERIODIC_FILE)

    def load_labs(self) -> pd.DataFrame:
        return pd.read_csv(config.LAB_FILE)

    def load_medications(self) -> pd.DataFrame:
        return pd.read_csv(config.MEDICATION_FILE)
    
if __name__ == "__main__":
    loader = EICUDataLoader()

    print("Testando carregamento do eICU-CRD Demo...")

    vital_df = loader.load_vital_periodic()

    print("\nArquivo vitalPeriodic carregado com sucesso!")
    print(f"Quantidade de linhas: {vital_df.shape[0]}")
    print(f"Quantidade de colunas: {vital_df.shape[1]}")

    print("\nColunas encontradas:")
    print(vital_df.columns.tolist())

    print("\nPrimeiras linhas:")
    print(vital_df.head())