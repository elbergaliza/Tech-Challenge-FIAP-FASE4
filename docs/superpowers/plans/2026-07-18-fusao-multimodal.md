# Fusão Multimodal — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar `fusion.py` + `main.py` na raiz que executam os módulos clínico e de vídeo sequencialmente e consolidam os alertas em `outputs/final_multimodal_report.json` com um único `python main.py --video <path>`.

**Architecture:** Padrão adaptador — cada módulo tem um `ModuleAdapter` que injeta o `sys.path` correto, executa o pipeline e normaliza os alertas para um schema interno unificado (`AlertaNormalizado`). `MultimodalFusion` recebe listas de alertas e produz o relatório final. `EICUDataLoader` é modificado para aceitar `data_dir` opcional, desacoplando os testes do path hardcoded.

**Tech Stack:** Python 3.11, dataclasses, abc, argparse, pathlib, pytest, sklearn (Isolation Forest — já no módulo clínico), MediaPipe + YOLOv8 (já no módulo de vídeo), GitHub Actions.

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `fusion.py` | Criar (mover de `src/`) | `AlertaNormalizado`, `ModuleAdapter`, `ClinicalAdapter`, `VideoAdapter`, `MultimodalFusion` |
| `main.py` | Criar | CLI — orquestra adaptadores e fusão |
| `src/fusion.py` | Remover | Rascunho obsoleto |
| `eicu-anomaly-detection/src/data_loader.py` | Modificar | `EICUDataLoader(data_dir=None)` |
| `tests/test_fusion.py` | Criar | Testes unitários de `MultimodalFusion`, `ClinicalAdapter` e `VideoAdapter` |
| `tests/fixtures/test_video.mp4` | Criar | Vídeo MP4 curto (≤ 5s) para CI e testes locais |
| `.github/workflows/fusion.yml` | Criar | CI que baixa eICU Demo e valida o relatório |
| `README.md` | Modificar | Seção "Fusão Multimodal" com instrução de uso |
| `outputs/.gitkeep` | Criar | Garante que `outputs/` existe no repo |

---

## Task 1: Remover `src/fusion.py` e criar `fusion.py` vazio na raiz

**Files:**
- Remove: `src/fusion.py`, `src/`
- Create: `fusion.py`

- [ ] **Step 1: Criar `fusion.py` na raiz com docstring**

```python
"""
fusion.py
---------
Módulo de fusão multimodal do Tech Challenge FIAP Fase 4.

Integra os alertas dos módulos clínico e de vídeo em um relatório consolidado.
Extensível: adicionar novo módulo = criar um ModuleAdapter e registrá-lo no main.py.
"""
```

- [ ] **Step 2: Remover `src/`**

```bash
git rm -r src/
```

- [ ] **Step 3: Verificar**

```bash
python -c "import fusion; print('OK')"
git status  # src/ deve aparecer como deleted
```

- [ ] **Step 4: Commit**

```bash
git add fusion.py
git commit -m "refactor: mover fusion.py para raiz e remover src/"
```

---

## Task 2: Definir `AlertaNormalizado` e `ModuleAdapter`

**Files:**
- Modify: `fusion.py`

- [ ] **Step 1: Adicionar imports e `AlertaNormalizado`**

```python
from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class AlertaNormalizado:
    """Schema interno unificado entre adaptadores e core de fusão."""
    module_id: str
    modulo: str
    tipo_anomalia: str
    score_risco: float   # 0.0 – 1.0
    nivel_risco: str     # "baixo" | "moderado" | "alto"
    descricao: str
    recomendacao: str
```

- [ ] **Step 2: Adicionar `ModuleAdapter`**

```python
class ModuleAdapter(ABC):
    """Contrato que todo adaptador de módulo deve implementar."""

    @abstractmethod
    def run(self) -> list[AlertaNormalizado]:
        """Executa o pipeline do módulo e retorna alertas normalizados."""
        ...
```

- [ ] **Step 3: Verificar**

```bash
python -c "from fusion import AlertaNormalizado, ModuleAdapter; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add fusion.py
git commit -m "feat(fusion): adicionar AlertaNormalizado e ModuleAdapter"
```

---

## Task 3: Tornar `EICUDataLoader` flexível

**Files:**
- Modify: `eicu-anomaly-detection/src/data_loader.py`

- [ ] **Step 1: Escrever o teste primeiro**

Criar `tests/test_data_loader.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, "eicu-anomaly-detection")
sys.path.insert(0, "eicu-anomaly-detection/src")

from src.data_loader import EICUDataLoader


def test_data_loader_default_usa_config():
    """Sem data_dir, usa config.DATA_RAW_DIR."""
    from src import config
    loader = EICUDataLoader()
    assert loader.data_dir == config.DATA_RAW_DIR


def test_data_loader_aceita_data_dir_customizado(tmp_path):
    """Com data_dir, usa o path fornecido."""
    loader = EICUDataLoader(data_dir=tmp_path)
    assert loader.data_dir == tmp_path


def test_load_vital_usa_data_dir(tmp_path):
    """load_vital_periodic usa self.data_dir para montar o path."""
    import pandas as pd
    # Criar CSV mínimo compatível com o schema do eICU
    csv_path = tmp_path / "vitalPeriodic.csv.gz"
    pd.DataFrame({
        "patientunitstayid": [1], "heartrate": [80.0],
        "sao2": [98.0], "respiration": [16.0],
        "systemicsystolic": [120.0], "temperature": [36.6],
        "observationoffset": [0]
    }).to_csv(csv_path, index=False, compression="gzip")

    loader = EICUDataLoader(data_dir=tmp_path)
    df = loader.load_vital_periodic()
    assert len(df) == 1
```

- [ ] **Step 2: Rodar e verificar que falha**

```bash
cd /caminho/do/repo && pytest tests/test_data_loader.py -v
```

Esperado: `FAILED — EICUDataLoader() got an unexpected keyword argument 'data_dir'`

- [ ] **Step 3: Modificar `EICUDataLoader`**

```python
import pandas as pd
from pathlib import Path
from src import config


class EICUDataLoader:
    """
    Carrega os arquivos principais do eICU-CRD Demo.

    data_dir: diretório com os CSVs brutos. Quando None, usa config.DATA_RAW_DIR.
    Isso permite testes com fixtures locais e CI com paths configuráveis.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir is not None else config.DATA_RAW_DIR

    def load_patients(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "patient.csv.gz")

    def load_vital_periodic(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "vitalPeriodic.csv.gz")

    def load_vital_aperiodic(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "vitalAperiodic.csv.gz")

    def load_labs(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "lab.csv.gz")

    def load_medications(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "medication.csv.gz")


if __name__ == "__main__":
    loader = EICUDataLoader()
    print("Testando carregamento do eICU-CRD Demo...")
    vital_df = loader.load_vital_periodic()
    print(f"\nArquivo vitalPeriodic carregado com sucesso!")
    print(f"Quantidade de linhas: {vital_df.shape[0]}")
    print(f"Quantidade de colunas: {vital_df.shape[1]}")
    print("\nColunas encontradas:")
    print(vital_df.columns.tolist())
    print("\nPrimeiras linhas:")
    print(vital_df.head())
```

- [ ] **Step 4: Rodar e verificar que passa**

```bash
pytest tests/test_data_loader.py -v
```

Esperado: 3 testes PASSED

- [ ] **Step 5: Verificar que `train.py` ainda funciona**

`train.py` usa `EICUDataLoader()` sem argumentos — compatibilidade retroativa garantida.

```bash
cd eicu-anomaly-detection && python -c "from src.data_loader import EICUDataLoader; EICUDataLoader(); print('OK')" && cd ..
```

- [ ] **Step 6: Commit**

```bash
git add eicu-anomaly-detection/src/data_loader.py tests/test_data_loader.py
git commit -m "feat(eicu): EICUDataLoader aceita data_dir opcional"
```

---

## Task 4: Implementar `ClinicalAdapter`

**Files:**
- Modify: `fusion.py`
- Modify: `tests/test_fusion.py` (criar se não existe)

- [ ] **Step 1: Escrever testes do `ClinicalAdapter`**

Criar `tests/test_fusion.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Garante que fusion.py na raiz é importável
sys.path.insert(0, str(Path(__file__).parents[1]))

from fusion import AlertaNormalizado, ClinicalAdapter


# ---------- fixtures ----------

ALERTA_CLINICO_SAMPLE = {
    "sample_id": "141765",
    "modulo": "anomalias_clinicas_uti",
    "tipo_anomalia": "sinais_vitais",
    "score_risco": 0.91,
    "nivel_risco": "alto",
    "descricao": "Frequência cardíaca elevada.",
    "recomendacao": "Reavaliar paciente.",
}


# ---------- ClinicalAdapter ----------

def test_clinical_adapter_normaliza_sample_id(tmp_path):
    """sample_id deve virar module_id no AlertaNormalizado."""
    alerts_path = tmp_path / "outputs"
    alerts_path.mkdir()
    (alerts_path / "alerts.json").write_text(
        json.dumps([ALERTA_CLINICO_SAMPLE]), encoding="utf-8"
    )

    adapter = ClinicalAdapter(data_dir=tmp_path / "raw")

    with patch.object(adapter, "_executar_pipeline"):
        with patch.object(adapter, "_alerts_path", alerts_path / "alerts.json"):
            alertas = adapter.run()

    assert len(alertas) == 1
    assert alertas[0].module_id == "141765"
    assert alertas[0].modulo == "anomalias_clinicas_uti"
    assert alertas[0].score_risco == 0.91


def test_clinical_adapter_lista_vazia(tmp_path):
    """Sem alertas no JSON retorna lista vazia."""
    alerts_path = tmp_path / "outputs"
    alerts_path.mkdir()
    (alerts_path / "alerts.json").write_text("[]", encoding="utf-8")

    adapter = ClinicalAdapter(data_dir=tmp_path / "raw")

    with patch.object(adapter, "_executar_pipeline"):
        with patch.object(adapter, "_alerts_path", alerts_path / "alerts.json"):
            alertas = adapter.run()

    assert alertas == []
```

- [ ] **Step 2: Rodar e verificar que falha**

```bash
pytest tests/test_fusion.py -k "clinical" -v
```

Esperado: `FAILED — cannot import name 'ClinicalAdapter' from 'fusion'`

- [ ] **Step 3: Implementar `ClinicalAdapter` em `fusion.py`**

```python
class ClinicalAdapter(ModuleAdapter):
    """
    Executa o pipeline clínico (eICU Demo) e normaliza sample_id → module_id.

    data_dir: diretório com os CSVs brutos do eICU. Quando None, usa o path
    padrão do módulo (eicu-anomaly-detection/modulo_anomalias/data/raw/).
    """

    _EICU_ROOT = Path(__file__).parent / "eicu-anomaly-detection"
    _OUTPUTS = _EICU_ROOT / "modulo_anomalias" / "outputs"

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self._alerts_path = self._OUTPUTS / "alerts.json"
        self._injetar_syspath()

    def _injetar_syspath(self):
        eicu_src = str(self._EICU_ROOT / "src")
        eicu_root = str(self._EICU_ROOT)
        if eicu_src not in sys.path:
            sys.path.insert(0, eicu_src)
        if eicu_root not in sys.path:
            sys.path.insert(0, eicu_root)

    def _executar_pipeline(self):
        from src.data_loader import EICUDataLoader
        from src.feature_builder import ClinicalFeatureBuilder
        from src.anomaly_detector import ClinicalAnomalyDetector
        from src.alert_generator import AlertGenerator
        from src import config

        loader = EICUDataLoader(data_dir=self.data_dir)
        vital_df = loader.load_vital_periodic()

        builder = ClinicalFeatureBuilder()
        features = builder.build_vital_features(vital_df)

        config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        detector = ClinicalAnomalyDetector()
        detector.train(features)
        predictions = detector.predict(features)

        alert_generator = AlertGenerator()
        alerts = alert_generator.generate_alerts(predictions, features)
        alerts.to_json(self._alerts_path, orient="records", force_ascii=False, indent=2)

    def run(self) -> list[AlertaNormalizado]:
        print("[ClinicalAdapter] Executando pipeline clínico...")
        self._executar_pipeline()

        if not self._alerts_path.exists():
            raise RuntimeError(
                f"alerts.json não gerado em {self._alerts_path}. "
                "Verifique se os dados eICU estão em data/raw/."
            )

        with open(self._alerts_path, encoding="utf-8") as f:
            raw = json.load(f)

        return [
            AlertaNormalizado(
                module_id=str(a["sample_id"]),
                modulo=a["modulo"],
                tipo_anomalia=a["tipo_anomalia"],
                score_risco=float(a["score_risco"]),
                nivel_risco=a["nivel_risco"],
                descricao=a["descricao"],
                recomendacao=a["recomendacao"],
            )
            for a in raw
        ]
```

- [ ] **Step 4: Rodar e verificar que passa**

```bash
pytest tests/test_fusion.py -k "clinical" -v
```

Esperado: 2 testes PASSED

- [ ] **Step 5: Commit**

```bash
git add fusion.py tests/test_fusion.py
git commit -m "feat(fusion): implementar ClinicalAdapter"
```

---

## Task 5: Implementar `VideoAdapter`

**Files:**
- Modify: `fusion.py`
- Modify: `tests/test_fusion.py`

- [ ] **Step 1: Adicionar testes do `VideoAdapter`**

Acrescentar em `tests/test_fusion.py` — **atualizar a linha de import existente** (não duplicar):

```python
# Atualizar a linha de import no topo do arquivo de:
#   from fusion import AlertaNormalizado, ClinicalAdapter
# para:
from fusion import AlertaNormalizado, ClinicalAdapter, VideoAdapter
```

Adicionar os novos testes:

```python
from fusion import AlertaNormalizado, ClinicalAdapter, VideoAdapter

ALERTA_VIDEO_SAMPLE = {
    "patient_id": "video_001",
    "modulo": "video_fisioterapia",
    "tipo_anomalia": "movimento",
    "score_risco": 0.42,
    "nivel_risco": "moderado",
    "descricao": "Assimetria de passada (28%).",
    "recomendacao": "Revisar exercício.",
}


def test_video_adapter_normaliza_patient_id(tmp_path):
    """patient_id deve virar module_id no AlertaNormalizado."""
    video_path = tmp_path / "test.mp4"
    video_path.touch()

    adapter = VideoAdapter(video_path=str(video_path), patient_id="video_001")

    with patch.object(adapter, "_executar_pipeline", return_value=ALERTA_VIDEO_SAMPLE):
        alertas = adapter.run()

    assert len(alertas) == 1
    assert alertas[0].module_id == "video_001"
    assert alertas[0].modulo == "video_fisioterapia"
    assert alertas[0].score_risco == 0.42


def test_video_adapter_arquivo_inexistente():
    """FileNotFoundError quando o vídeo não existe."""
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        VideoAdapter(video_path="/nao/existe.mp4", patient_id="p1").run()
```

- [ ] **Step 2: Rodar e verificar que falha**

```bash
pytest tests/test_fusion.py -k "video" -v
```

Esperado: `FAILED — cannot import name 'VideoAdapter'`

- [ ] **Step 3: Implementar `VideoAdapter` em `fusion.py`**

```python
class VideoAdapter(ModuleAdapter):
    """
    Executa o pipeline de vídeo e normaliza patient_id → module_id.

    video_path: caminho do arquivo MP4 de entrada.
    patient_id: identificador da sessão.
    sem_objetos: desativa YOLOv8 (útil em máquinas sem GPU).
    """

    _VIDEO_ROOT = Path(__file__).parent / "modulo_video"

    def __init__(
        self,
        video_path: str,
        patient_id: str = "video_001",
        sem_objetos: bool = False,
        verbose: bool = True,
    ):
        self.video_path = video_path
        self.patient_id = patient_id
        self.sem_objetos = sem_objetos
        self.verbose = verbose
        self._injetar_syspath()

    def _injetar_syspath(self):
        video_root = str(self._VIDEO_ROOT)
        if video_root not in sys.path:
            sys.path.insert(0, video_root)

    def _executar_pipeline(self) -> dict:
        from src.pipeline import processar_video
        return processar_video(
            caminho_video=self.video_path,
            patient_id=self.patient_id,
            usar_objetos=not self.sem_objetos,
            verbose=self.verbose,
        )

    def run(self) -> list[AlertaNormalizado]:
        if not Path(self.video_path).exists():
            raise FileNotFoundError(
                f"Arquivo de vídeo não encontrado: {self.video_path}"
            )

        print(f"[VideoAdapter] Processando vídeo: {self.video_path}")
        alerta = self._executar_pipeline()

        return [
            AlertaNormalizado(
                module_id=str(alerta.get("patient_id", self.patient_id)),
                modulo=alerta["modulo"],
                tipo_anomalia=alerta["tipo_anomalia"],
                score_risco=float(alerta["score_risco"]),
                nivel_risco=alerta["nivel_risco"],
                descricao=alerta["descricao"],
                recomendacao=alerta["recomendacao"],
            )
        ]
```

- [ ] **Step 4: Rodar e verificar que passa**

```bash
pytest tests/test_fusion.py -k "video" -v
```

Esperado: 2 testes PASSED

- [ ] **Step 5: Commit**

```bash
git add fusion.py tests/test_fusion.py
git commit -m "feat(fusion): implementar VideoAdapter"
```

---

## Task 6: Implementar `MultimodalFusion`

**Files:**
- Modify: `fusion.py`
- Modify: `tests/test_fusion.py`

- [ ] **Step 1: Adicionar testes do `MultimodalFusion`**

Acrescentar em `tests/test_fusion.py` — **atualizar a linha de import existente** para:

```python
from fusion import AlertaNormalizado, ClinicalAdapter, VideoAdapter, MultimodalFusion


def _alerta(module_id, modulo, score, nivel):
    return AlertaNormalizado(
        module_id=module_id, modulo=modulo, tipo_anomalia="teste",
        score_risco=score, nivel_risco=nivel,
        descricao="desc", recomendacao="rec",
    )


def test_fusao_score_medio():
    """score_medio = média aritmética dos scores (0.9 + 0.1) / 2 = 0.5."""
    alertas = [
        [_alerta("1", "clinico", 0.9, "alto")],
        [_alerta("v1", "video", 0.1, "baixo")],
    ]
    report = MultimodalFusion().fuse(alertas)
    # (0.9 + 0.1) / 2 = 0.5 — nota: o spec menciona "0.51" por erro tipográfico
    assert report["resumo"]["score_medio"] == pytest.approx(0.5, abs=0.001)


def test_fusao_nivel_mais_critico_preservado():
    """nivel_mais_critico reflete o alerta de maior score, não a média."""
    alertas = [
        [_alerta("1", "clinico", 0.9, "alto")],
        [_alerta("v1", "video", 0.1, "baixo")],
    ]
    report = MultimodalFusion().fuse(alertas)
    assert report["resumo"]["nivel_mais_critico"] == "alto"


def test_fusao_recomendacao_baseada_no_pior():
    """recomendacao_geral segue nivel_mais_critico."""
    alertas = [[_alerta("1", "clinico", 0.9, "alto")]]
    report = MultimodalFusion().fuse(alertas)
    assert "imediata" in report["resumo"]["recomendacao_geral"]


def test_fusao_zero_alertas():
    """Sem alertas, relatório válido com total_alertas = 0."""
    report = MultimodalFusion().fuse([[], []])
    assert report["resumo"]["total_alertas"] == 0
    assert report["alertas"] == []


def test_fusao_normaliza_module_id():
    """Alertas individuais preservam o module_id normalizado."""
    alertas = [[_alerta("141765", "clinico", 0.8, "alto")]]
    report = MultimodalFusion().fuse(alertas)
    assert report["alertas"][0]["module_id"] == "141765"


def test_fusao_modulos_analisados_sorted():
    """modulos_analisados e modulos_com_alerta ficam ordenados."""
    alertas = [
        [_alerta("1", "video_fisioterapia", 0.5, "moderado")],
        [_alerta("2", "anomalias_clinicas_uti", 0.8, "alto")],
    ]
    report = MultimodalFusion().fuse(alertas)
    assert report["resumo"]["modulos_analisados"] == sorted(
        ["video_fisioterapia", "anomalias_clinicas_uti"]
    )
```

- [ ] **Step 2: Rodar e verificar que falha**

```bash
pytest tests/test_fusion.py -k "fusao" -v
```

Esperado: `FAILED — cannot import name 'MultimodalFusion'`

- [ ] **Step 3: Implementar `MultimodalFusion` em `fusion.py`**

```python
class MultimodalFusion:
    """
    Recebe listas de AlertaNormalizado de múltiplos adaptadores
    e produz o relatório consolidado final.
    """

    _FAIXAS = [
        ("alto",     0.70, 1.01),
        ("moderado", 0.40, 0.70),
        ("baixo",    0.00, 0.40),
    ]

    _RECOMENDACOES = {
        "alto":     "Acionar equipe médica para reavaliação imediata do paciente.",
        "moderado": "Manter paciente em observação e repetir avaliação clínica.",
        "baixo":    "Continuar monitoramento preventivo.",
    }

    def fuse(self, listas: list[list[AlertaNormalizado]]) -> dict:
        """Consolida alertas de múltiplos módulos em um FinalReport."""
        todos = [a for lista in listas for a in lista]

        score_medio = self._score_medio(todos)
        nivel_critico = self._nivel_mais_critico(todos)

        modulos_analisados = sorted({
            a.modulo for lista in listas for a in lista
        })
        modulos_com_alerta = sorted({a.modulo for a in todos})

        return {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "resumo": {
                "total_alertas": len(todos),
                "score_medio": score_medio,
                "nivel_mais_critico": nivel_critico,
                "modulos_analisados": modulos_analisados,
                "modulos_com_alerta": modulos_com_alerta,
                "recomendacao_geral": self._recomendacao(nivel_critico),
            },
            "alertas": [asdict(a) for a in todos],
        }

    def _score_medio(self, alertas: list[AlertaNormalizado]) -> float:
        if not alertas:
            return 0.0
        return round(sum(a.score_risco for a in alertas) / len(alertas), 3)

    def _nivel_mais_critico(self, alertas: list[AlertaNormalizado]) -> str:
        if not alertas:
            return "baixo"
        return self._classificar_nivel(max(a.score_risco for a in alertas))

    def _classificar_nivel(self, score: float) -> str:
        for nivel, minimo, maximo in self._FAIXAS:
            if minimo <= score < maximo:
                return nivel
        return "alto"

    def _recomendacao(self, nivel: str) -> str:
        return self._RECOMENDACOES.get(nivel, self._RECOMENDACOES["baixo"])
```

- [ ] **Step 4: Rodar todos os testes**

```bash
pytest tests/test_fusion.py -v
```

Esperado: ≥ 8 testes PASSED, 0 FAILED

- [ ] **Step 5: Commit**

```bash
git add fusion.py tests/test_fusion.py
git commit -m "feat(fusion): implementar MultimodalFusion"
```

---

## Task 7: Criar `main.py` e `tests/fixtures/`

**Files:**
- Create: `main.py`
- Create: `tests/fixtures/test_video.mp4`
- Create: `outputs/.gitkeep`

- [ ] **Step 1: Obter vídeo de teste leve**

Baixar um vídeo MP4 curto de domínio público (ex: 5s, < 2MB) ou gerar um sintético:

```bash
# Opção: gerar vídeo sintético com ffmpeg (10 frames pretos, suficiente para o pipeline)
ffmpeg -f lavfi -i color=c=black:s=640x480:d=5 -c:v libx264 -t 5 tests/fixtures/test_video.mp4
```

Verificar que é um MP4 válido:

```bash
ffprobe tests/fixtures/test_video.mp4
```

- [ ] **Step 2: Criar `outputs/.gitkeep`**

```bash
mkdir -p outputs && touch outputs/.gitkeep
```

- [ ] **Step 3: Criar `main.py`**

```python
"""
main.py
-------
Ponto de entrada da fusão multimodal.

Executa os módulos clínico e de vídeo sequencialmente e consolida
os alertas em outputs/final_multimodal_report.json.

Uso:
    python main.py --video sessao.mp4 --patient-id paciente_001
    python main.py --video sessao.mp4 --eicu-data /caminho/para/raw/
    python main.py --video sessao.mp4 --sem-objetos --silencioso
"""

import argparse
import json
import sys
from pathlib import Path

from fusion import ClinicalAdapter, VideoAdapter, MultimodalFusion

_EICU_DATA_DEFAULT = (
    Path(__file__).parent
    / "eicu-anomaly-detection"
    / "modulo_anomalias"
    / "data"
    / "raw"
)
_SAIDA_DEFAULT = Path(__file__).parent / "outputs" / "final_multimodal_report.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fusão multimodal — Tech Challenge FIAP Fase 4"
    )
    parser.add_argument("--video", required=True, help="Caminho do vídeo MP4")
    parser.add_argument("--patient-id", default="video_001", help="ID da sessão de vídeo")
    parser.add_argument(
        "--eicu-data",
        default=str(_EICU_DATA_DEFAULT),
        help="Diretório com os CSVs do eICU Demo (default: eicu-anomaly-detection/modulo_anomalias/data/raw/)",
    )
    parser.add_argument(
        "--saida",
        default=str(_SAIDA_DEFAULT),
        help="Path do relatório JSON final",
    )
    parser.add_argument("--sem-objetos", action="store_true", help="Desativa YOLOv8")
    parser.add_argument("--silencioso", action="store_true", help="Suprime prints dos módulos (passa verbose=False ao VideoAdapter)")
    return parser.parse_args()


def validar(args):
    erros = []

    video = Path(args.video)
    if not video.exists():
        erros.append(f"Arquivo de vídeo não encontrado: {args.video}")

    eicu = Path(args.eicu_data)
    vital = eicu / "vitalPeriodic.csv.gz"
    if not vital.exists():
        erros.append(
            f"Dados eICU não encontrados em: {args.eicu_data}\n"
            "  Baixe de https://physionet.org/content/eicu-crd-demo/2.0.1/\n"
            "  e coloque vitalPeriodic.csv.gz, lab.csv.gz e medication.csv.gz no diretório."
        )

    if erros:
        for e in erros:
            print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    validar(args)

    print("=" * 60)
    print("  Fusão Multimodal — Tech Challenge FIAP Fase 4")
    print("=" * 60)

    # Módulo clínico
    clinical = ClinicalAdapter(data_dir=args.eicu_data)
    alertas_clinicos = clinical.run()
    print(f"[Clínico] {len(alertas_clinicos)} alerta(s) gerado(s).")

    # Módulo de vídeo
    video = VideoAdapter(
        video_path=args.video,
        patient_id=args.patient_id,
        sem_objetos=args.sem_objetos,
        verbose=not args.silencioso,
    )
    alertas_video = video.run()
    print(f"[Vídeo] {len(alertas_video)} alerta(s) gerado(s).")

    # Fusão
    report = MultimodalFusion().fuse([alertas_clinicos, alertas_video])

    # Salvar
    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Imprimir
    print("\n" + "=" * 60)
    print("  RELATÓRIO MULTIMODAL FINAL")
    print("=" * 60)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nRelatório salvo em: {saida}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verificar CLI**

```bash
python main.py --help
```

Esperado: usage impresso sem erro.

- [ ] **Step 5: Commit**

```bash
git add main.py tests/fixtures/test_video.mp4 outputs/.gitkeep
git commit -m "feat: adicionar main.py e fixtures para CI"
```

---

## Task 8: Teste end-to-end local

> **Task de validação — sem commit.** Requer os dados eICU em `eicu-anomaly-detection/modulo_anomalias/data/raw/`.

- [ ] **Step 1: Executar a pipeline completa**

```bash
python main.py --video tests/fixtures/test_video.mp4 --patient-id e2e_test
```

Esperado: pipeline roda, relatório impresso no terminal.

- [ ] **Step 2: Validar estrutura do JSON**

```bash
python -c "
import json
r = json.load(open('outputs/final_multimodal_report.json'))
assert 'resumo' in r, 'falta resumo'
assert 'alertas' in r, 'falta alertas'
assert 'score_medio' in r['resumo'], 'falta score_medio'
assert 'nivel_mais_critico' in r['resumo'], 'falta nivel_mais_critico'
print('OK — relatório válido')
print(f'Total alertas: {r[\"resumo\"][\"total_alertas\"]}')
print(f'Nível mais crítico: {r[\"resumo\"][\"nivel_mais_critico\"]}')
"
```

- [ ] **Step 3: Rodar todos os testes unitários**

```bash
pytest tests/ -v
```

Esperado: todos PASSED.

---

## Task 9: Criar workflow CI GitHub Actions

**Files:**
- Create: `.github/workflows/fusion.yml`

- [ ] **Step 1: Criar o workflow**

```yaml
# .github/workflows/fusion.yml
name: Fusão Multimodal CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  fusion:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Instalar dependências
        run: |
          # Instala dependências dos dois módulos
          pip install -r eicu-anomaly-detection/requirements.txt || true
          pip install -r modulo_video/requirements.txt || true
          # Se existir requirements.txt na raiz, instala também
          [ -f requirements.txt ] && pip install -r requirements.txt || true

      - name: Baixar eICU Demo
        env:
          PHYSIONET_USER: ${{ secrets.PHYSIONET_USER }}
          PHYSIONET_PASSWORD: ${{ secrets.PHYSIONET_PASSWORD }}
        run: |
          if [ -z "$PHYSIONET_USER" ] || [ -z "$PHYSIONET_PASSWORD" ]; then
            echo "ERRO: secrets PHYSIONET_USER e PHYSIONET_PASSWORD não configurados."
            echo "Configure em: Settings → Secrets → Actions"
            exit 1
          fi
          DATA_DIR="eicu-anomaly-detection/modulo_anomalias/data/raw"
          mkdir -p "$DATA_DIR"
          BASE_URL="https://physionet.org/files/eicu-crd-demo/2.0.1"
          for file in vitalPeriodic.csv.gz lab.csv.gz medication.csv.gz; do
            wget --user="$PHYSIONET_USER" --password="$PHYSIONET_PASSWORD" \
              -q -O "$DATA_DIR/$file" "$BASE_URL/$file"
          done
          echo "Download concluído."

      - name: Rodar testes unitários
        run: pytest tests/test_fusion.py -v

      - name: Executar pipeline de fusão
        run: |
          python main.py \
            --video tests/fixtures/test_video.mp4 \
            --patient-id ci_test \
            --eicu-data eicu-anomaly-detection/modulo_anomalias/data/raw

      - name: Validar relatório gerado
        run: |
          python -c "
          import json, sys
          r = json.load(open('outputs/final_multimodal_report.json'))
          assert 'resumo' in r, 'falta resumo'
          assert 'alertas' in r, 'falta alertas'
          assert 'score_medio' in r['resumo'], 'falta score_medio'
          assert 'nivel_mais_critico' in r['resumo'], 'falta nivel_mais_critico'
          print('OK — relatório válido')
          print(f'Total alertas: {r[\"resumo\"][\"total_alertas\"]}')
          "
```

- [ ] **Step 2: Verificar YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/fusion.yml'))" 2>/dev/null || pip install pyyaml && python -c "import yaml; yaml.safe_load(open('.github/workflows/fusion.yml')); print('YAML válido')"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/fusion.yml
git commit -m "ci: adicionar workflow de fusão multimodal"
```

---

## Task 10: Atualizar README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Adicionar seção "Fusão Multimodal"**

Substituir a seção "Integração futura" por:

```markdown
# Fusão Multimodal

O módulo de fusão integra os resultados dos módulos clínico e de vídeo em um único relatório consolidado.

## Pré-requisitos

1. **Dados eICU Demo** — baixe de https://physionet.org/content/eicu-crd-demo/2.0.1/ e coloque em:
   ```
   eicu-anomaly-detection/modulo_anomalias/data/raw/
     vitalPeriodic.csv.gz
     lab.csv.gz
     medication.csv.gz
   ```

2. **Vídeo MP4** — qualquer arquivo de vídeo curto (10–30s).

## Executar

Da raiz do repositório:

```bash
python main.py --video caminho/para/sessao.mp4 --patient-id paciente_001
```

O relatório final é salvo em `outputs/final_multimodal_report.json` e impresso no terminal.

## Argumentos

| Argumento | Padrão | Descrição |
|-----------|--------|-----------|
| `--video` | obrigatório | Caminho do vídeo MP4 |
| `--patient-id` | `video_001` | ID da sessão de vídeo |
| `--eicu-data` | `eicu-anomaly-detection/modulo_anomalias/data/raw/` | Diretório com os CSVs eICU |
| `--saida` | `outputs/final_multimodal_report.json` | Path do relatório final |
| `--sem-objetos` | — | Desativa YOLOv8 (máquinas sem GPU) |
| `--silencioso` | — | Suprime logs dos módulos |

## Adicionar módulo de áudio (futuro)

Criar `AudioAdapter(ModuleAdapter)` em `fusion.py` e adicionar `--audio` ao `main.py`. Zero mudança no core de fusão.
```

- [ ] **Step 2: Verificar**

```bash
grep -n "Fusão Multimodal" README.md
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: atualizar README com instruções da fusão multimodal"
```

---

## Verificação Final

```bash
# Todos os testes passam
pytest tests/ -v

# Pipeline roda localmente (requer dados eICU)
python main.py --video tests/fixtures/test_video.mp4 --patient-id final_check

# Relatório válido
python -c "
import json
r = json.load(open('outputs/final_multimodal_report.json'))
print(json.dumps(r['resumo'], indent=2, ensure_ascii=False))
"
```
