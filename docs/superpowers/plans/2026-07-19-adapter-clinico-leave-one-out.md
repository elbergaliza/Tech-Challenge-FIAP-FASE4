> **For agentic workers:** REQUIRED: Use @superpowers:subagent-driven-development (if subagents available) or @superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

# Adapter Clínico Leave-One-Out Implementation Plan

**Goal:** Alterar apenas o `ClinicalAdapter` para separar treino e predição via leave-one-out, controlável por variável de ambiente `ADAPTER_CLINICAL_LEAVE_ONE_OUT`, e adicionar testes comparativos.

**Architecture:** Manter a orquestração dentro do adapter, mas splitar o DataFrame de features em treino/predição com base no `patient_id` quando a flag de ambiente estiver ativada. O detector é treinado no subconjunto de treino e prediz no subconjunto do alvo. Testes cobrem ambos os modos e comparam os alertas gerados.

**Tech Stack:** Python, pandas, scikit-learn, pytest.

**Scope note:** Este plano é deliberadamente menor do que a spec `2026-07-19-pipeline-clinico.md` anterior (removida). O escopo aqui é apenas o adapter; o módulo clínico em si (`eicu-anomaly-detection/src/train.py`) **não** será alterado.

---

## File Structure

- **Modify:** `fusion/adapters/clinical/adapter.py`
  - Responsável por adicionar o split leave-one-out e leitura da variável de ambiente.
- **Modify:** `tests/fusion/test_adapters.py`
  - Adicionar testes que validam o modo batch, leave-one-out, patient_id inexistente e treino vazio.

---

## Task 1: Adicionar helper de split e leitura de env no adapter

**Files:**
- Modify: `fusion/adapters/clinical/adapter.py`
- Test: `tests/fusion/test_adapters.py`

- [ ] **Step 1: Escrever o teste de falha**

```python
def test_clinical_adapter_split_features_por_patient_id():
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2", "3"],
        "heartrate_max": [100, 120, 90],
    })

    train_df, predict_df = ClinicalAdapter._split_leave_one_out(features, "2")

    assert train_df["patientunitstayid"].tolist() == ["1", "3"]
    assert predict_df["patientunitstayid"].tolist() == ["2"]
```

Run: `pytest tests/fusion/test_adapters.py::test_clinical_adapter_split_features_por_patient_id -v`
Expected: FAIL with "_split_leave_one_out not defined"

- [ ] **Step 2: Implementar o helper no adapter**

Em `fusion/adapters/clinical/adapter.py`, adicionar import de `os` e método estático:

```python
import os

@staticmethod
def _split_leave_one_out(features, patient_id, id_col="patientunitstayid"):
    target_mask = features[id_col].astype(str) == str(patient_id)
    if not target_mask.any():
        raise ValueError(f"Paciente {patient_id} não encontrado nos dados.")

    train_features = features[~target_mask].copy()
    predict_features = features[target_mask].copy()

    if train_features.empty:
        raise ValueError("Conjunto de treino vazio após leave-one-out.")

    return train_features, predict_features
```

- [ ] **Step 3: Verificar teste passa**

Run: `pytest tests/fusion/test_adapters.py::test_clinical_adapter_split_features_por_patient_id -v`
Expected: PASS

- [ ] **Step 4: Stage alterações (sem commit)**

```bash
git add fusion/adapters/clinical/adapter.py tests/fusion/test_adapters.py
git status --short
```

**Aguardar aprovação explícita do usuário antes de commit/push.**

---

## Task 2: Integrar leave-one-out no fluxo do adapter via env

**Files:**
- Modify: `fusion/adapters/clinical/adapter.py`
- Test: `tests/fusion/test_adapters.py`

- [ ] **Step 1: Escrever testes de falha**

```python
import os


def test_clinical_adapter_env_desligado_mantem_batch(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.delenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", raising=False)

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2", "3"],
        "heartrate_max": [100, 120, 90],
    })

    adapter = ClinicalAdapter()
    train_df, predict_df = adapter._get_train_predict_features(features, "2")

    assert train_df["patientunitstayid"].tolist() == ["1", "2", "3"]
    assert predict_df["patientunitstayid"].tolist() == ["1", "2", "3"]


def test_clinical_adapter_env_ligado_ativa_leave_one_out(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "1")

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2", "3"],
        "heartrate_max": [100, 120, 90],
    })

    adapter = ClinicalAdapter()
    train_df, predict_df = adapter._get_train_predict_features(features, "2")

    assert train_df["patientunitstayid"].tolist() == ["1", "3"]
    assert predict_df["patientunitstayid"].tolist() == ["2"]
```

Run:
```bash
pytest tests/fusion/test_adapters.py::test_clinical_adapter_env_desligado_mantem_batch -v
pytest tests/fusion/test_adapters.py::test_clinical_adapter_env_ligado_ativa_leave_one_out -v
```
Expected: FAIL with "_get_train_predict_features not defined"

- [ ] **Step 2: Implementar método condicional**

Em `fusion/adapters/clinical/adapter.py`, adicionar:

```python
def _use_leave_one_out(self) -> bool:
    return os.environ.get("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "").lower() in ("1", "true", "yes")

def _get_train_predict_features(self, features, patient_id):
    if self._use_leave_one_out() and patient_id is not None:
        return self._split_leave_one_out(features, patient_id)
    return features.copy(), features.copy()
```

- [ ] **Step 3: Alterar run() para usar o split**

Substituir no `run()`:

```python
features = builder.build_vital_features(vital_df)

train_features, predict_features = self._get_train_predict_features(features, self.patient_id)

detector = ClinicalAnomalyDetector()
detector.train(train_features)
predictions = detector.predict(predict_features)

alert_generator = AlertGenerator()
alerts_df = alert_generator.generate_alerts(predictions, predict_features)
alerts_df = self._filtrar_alertas(alerts_df, self.patient_id)
```

Manter `_filtrar_alertas` para preservar o comportimento externo do modo batch. No modo leave-one-out o filtro não remove linhas adicionais porque a predição já está restrita ao alvo.

- [ ] **Step 4: Verificar testes passam**

Run:
```bash
pytest tests/fusion/test_adapters.py::test_clinical_adapter_env_desligado_mantem_batch -v
pytest tests/fusion/test_adapters.py::test_clinical_adapter_env_ligado_ativa_leave_one_out -v
```
Expected: PASS

- [ ] **Step 5: Stage alterações (sem commit)**

```bash
git add fusion/adapters/clinical/adapter.py tests/fusion/test_adapters.py
git status --short
```

**Aguardar aprovação explícita do usuário antes de commit/push.**

---

## Task 3: Adicionar testes de edge cases, comparação e integração com run()

**Files:**
- Modify: `tests/fusion/test_adapters.py`

**Dependências:** Task 2 deve estar completa para que `_get_train_predict_features` exista.

- [ ] **Step 1: Escrever testes de falha**

```python
def test_clinical_adapter_patient_id_inexistente_leave_one_out_levanta_erro(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "true")

    adapter = ClinicalAdapter()
    features = pd.DataFrame({
        "patientunitstayid": ["141765"],
        "heartrate_max": [120],
    })

    with pytest.raises(ValueError, match="Paciente .* não encontrado"):
        adapter._get_train_predict_features(features, "nao_existe")


def test_clinical_adapter_leave_one_out_treino_vazio_levanta_erro(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "true")

    adapter = ClinicalAdapter()
    features = pd.DataFrame({
        "patientunitstayid": ["1"],
        "heartrate_max": [100],
    })

    with pytest.raises(ValueError, match="Conjunto de treino vazio"):
        adapter._get_train_predict_features(features, "1")


def test_clinical_adapter_env_var_truthy_variations(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2"],
        "heartrate_max": [100, 120],
    })

    adapter = ClinicalAdapter()

    for valor in ("1", "true", "True", "yes", "YES"):
        monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", valor)
        train_df, _ = adapter._get_train_predict_features(features, "2")
        assert len(train_df) == 1
        assert train_df.iloc[0]["patientunitstayid"] == "1"


def test_clinical_adapter_env_var_falsy_variations(monkeypatch):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    features = pd.DataFrame({
        "patientunitstayid": ["1", "2"],
        "heartrate_max": [100, 120],
    })

    adapter = ClinicalAdapter()

    for valor in ("0", "false", "False", "no", "", None):
        if valor is None:
            monkeypatch.delenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", raising=False)
        else:
            monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", valor)

        train_df, _ = adapter._get_train_predict_features(features, "2")
        assert len(train_df) == 2


def test_clinical_adapter_run_usa_leave_one_out_quando_env_ativado(monkeypatch, tmp_path):
    from fusion.adapters.clinical.adapter import ClinicalAdapter

    monkeypatch.setenv("ADAPTER_CLINICAL_LEAVE_ONE_OUT", "1")

    adapter = ClinicalAdapter(
        data_dir=str(tmp_path),
        patient_id="paciente_2",
    )

    # Criar arquivos mock mínimos
    for nome in ["vitalPeriodic.csv.gz", "lab.csv.gz", "medication.csv.gz"]:
        (tmp_path / nome).write_text("")

    # Stub das dependências
    import eicu_anomaly_detection.data_loader as data_loader_module
    import eicu_anomaly_detection.feature_builder as feature_builder_module
    import eicu_anomaly_detection.anomaly_detector as anomaly_detector_module
    import eicu_anomaly_detection.alert_generator as alert_generator_module

    class FakeLoader:
        def load_vital_periodic(self):
            return pd.DataFrame({"patientunitstayid": ["paciente_1", "paciente_2"], "heartrate": [70, 120]})
        def load_labs(self):
            return pd.DataFrame()
        def load_medications(self):
            return pd.DataFrame()

    class FakeBuilder:
        def build_all_features(self, vital_df, lab_df=None, medication_df=None):
            return vital_df.assign(heartrate_max=vital_df["heartrate"])

    class FakeDetector:
        def __init__(self):
            self.train_called_with = None
            self.predict_called_with = None

        def train(self, features):
            self.train_called_with = features

        def predict(self, features):
            self.predict_called_with = features
            return pd.DataFrame({
                "patientunitstayid": features["patientunitstayid"].tolist(),
                "is_anomaly": [True],
                "risk_score": [0.9],
                "risk_level": ["alto"],
            })

    class FakeAlertGenerator:
        def generate_alerts(self, predictions, features, id_col="patientunitstayid"):
            return pd.DataFrame({
                "sample_id": predictions["patientunitstayid"].tolist(),
                "modulo": ["anomalias_clinicas_uti"],
                "tipo_anomalia": ["sinais_vitais"],
                "score_risco": [0.9],
                "nivel_risco": ["alto"],
                "descricao": ["test"],
                "recomendacao": ["test"],
            })

    monkeypatch.setattr(data_loader_module, "EICUDataLoader", FakeLoader)
    monkeypatch.setattr(feature_builder_module, "ClinicalFeatureBuilder", FakeBuilder)
    monkeypatch.setattr(anomaly_detector_module, "ClinicalAnomalyDetector", FakeDetector)
    monkeypatch.setattr(alert_generator_module, "AlertGenerator", FakeAlertGenerator)

    alertas = adapter.run()

    assert len(alertas) == 1
    assert alertas[0].module_id == "paciente_2"
```

Run: `pytest tests/fusion/test_adapters.py -v`
Expected: FAIL

- [ ] **Step 2: Implementar/ajustar o adapter se necessário**

O helper já implementado no Task 1 deve cobrir os erros. Certificar que `_use_leave_one_out` trata corretamente strings vazias e case-insensitive. Ajustar `run()` para passar `patient_id` como string para o helper se necessário.

- [ ] **Step 3: Verificar testes passam**

Run: `pytest tests/fusion/test_adapters.py -v`
Expected: PASS

- [ ] **Step 4: Stage alterações (sem commit)**

```bash
git add tests/fusion/test_adapters.py
git status --short
```

**Aguardar aprovação explícita do usuário antes de commit/push.**

---

## Task 4: Validar suite completa e E2E

**Files:**
- Nenhum novo arquivo.

- [ ] **Step 1: Limpar artefatos de execuções anteriores**

Run:
```bash
rm -rf eicu-anomaly-detection/modulo_anomalias/data/processed
rm -rf eicu-anomaly-detection/modulo_anomalias/outputs
rm -rf outputs
rm -f tests/fixtures/final_multimodal_report_e2e.json
```

- [ ] **Step 2: Rodar suite completa**

Run:
```bash
source .venv/bin/activate
pip install -e . -q
pytest tests/ -q
```
Expected: all tests pass

- [ ] **Step 3: Rodar E2E no modo batch e capturar JSON**

Run:
```bash
python main.py \
  --video tests/fixtures/test_video.mp4 \
  --eicu-data tests/fixtures/mock_eicu \
  --video-patient-id local_test \
  --sem-objetos \
  --silencioso \
  --saida /tmp/report_batch.json
```
Expected: arquivo `/tmp/report_batch.json` gerado sem erros

- [ ] **Step 4: Rodar E2E no modo leave-one-out e capturar JSON**

Run:
```bash
ADAPTER_CLINICAL_LEAVE_ONE_OUT=1 python main.py \
  --video tests/fixtures/test_video.mp4 \
  --eicu-data tests/fixtures/mock_eicu \
  --video-patient-id local_test \
  --sem-objetos \
  --silencioso \
  --saida /tmp/report_loo.json
```
Expected: arquivo `/tmp/report_loo.json` gerado sem erros

- [ ] **Step 5: Comparar os dois relatórios (opcional, diagnóstico)**

Run:
```bash
python - <<'PY'
import json
for path in ["/tmp/report_batch.json", "/tmp/report_loo.json"]:
    with open(path) as f:
        data = json.load(f)
    # O schema do relatório final contém 'alertas' com chaves module_id, modulo, score_risco, nivel_risco.
    clinico = [a for a in data.get("alertas", []) if a.get("modulo") == "anomalias_clinicas_uti"]
    print(f"{path}: {len(clinico)} alertas clinicos")
    for a in clinico[:3]:
        print(f"  - {a.get('module_id')}: score={a.get('score_risco')}, nivel={a.get('nivel_risco')}")
PY
```

- [ ] **Step 6: Stage alterações finais e aguardar aprovação**

```bash
git status --short
git add fusion/adapters/clinical/adapter.py tests/fusion/test_adapters.py
git status --short  # confirmar apenas arquivos desejados
```

**Não executar commit/push sem aprovação explícita do usuário.**
