# Fusão Multimodal — Design

**Spec**: `.specs/features/fusao-multimodal/spec.md`
**Status**: Approved

---

## Architecture Overview

```
python main.py --video sessao.mp4
        │
        ├─► ClinicalAdapter.run()
        │       └─► eicu-anomaly-detection/src/train.main()
        │               └─► [carrega eICU Demo → treina → prediz → gera alertas]
        │               └─► retorna list[AlertaNormalizado]
        │
        ├─► VideoAdapter.run(video, patient_id)
        │       └─► modulo_video/src/pipeline.processar_video()
        │               └─► [MediaPipe + YOLOv8 → score → alerta]
        │               └─► retorna list[AlertaNormalizado]
        │
        └─► MultimodalFusion.fuse([alertas_clinicos, alertas_video])
                ├─► score_medio = média dos scores
                ├─► nivel_mais_critico = nivel do max(score_risco)
                ├─► recomendacao_geral = baseada em nivel_mais_critico
                └─► FinalReport → outputs/final_multimodal_report.json
                                → print no terminal
```

Os módulos rodam **sequencialmente** (clínico → vídeo). Não há estado compartilhado entre eles — cada adaptador roda de forma isolada e retorna uma lista de alertas normalizados.

---

## Code Reuse Analysis

### Componentes existentes a reutilizar

| Componente | Localização | Como reutilizar |
|-----------|------------|----------------|
| `EICUDataLoader` | `eicu-anomaly-detection/src/data_loader.py` | Modificar para aceitar `data_dir` opcional — `ClinicalAdapter` passa o path que quiser |
| `train.main()` | `eicu-anomaly-detection/src/train.py:8` | Extrair lógica em função `run_pipeline(data_dir)` chamável pelo `ClinicalAdapter` |
| `processar_video()` | `modulo_video/src/pipeline.py:81` | Chamar direto via `sys.path` injection no `VideoAdapter` |
| `MultimodalFusion` | `src/fusion.py` (rascunho) | Refatorar no lugar — mover para `fusion.py` na raiz |
| `alerta_agachamento.json` | `modulo_video/data/exemplos/` | Referência de schema para fixtures de teste |

### Integração com módulos existentes

| Módulo | Campo original | Campo normalizado | Arquivo de saída |
|--------|---------------|------------------|-----------------|
| Clínico | `sample_id` | `module_id` | `eicu-anomaly-detection/modulo_anomalias/outputs/alerts.json` |
| Vídeo | `patient_id` | `module_id` | retornado diretamente por `processar_video()` |

---

## Components

### `AlertaNormalizado` (dataclass)

- **Purpose**: Schema interno unificado entre adaptadores e core de fusão
- **Location**: `fusion.py`
- **Interface**:
  ```python
  @dataclass
  class AlertaNormalizado:
      module_id: str
      modulo: str
      tipo_anomalia: str
      score_risco: float   # 0.0 – 1.0
      nivel_risco: str     # "baixo" | "moderado" | "alto"
      descricao: str
      recomendacao: str
  ```
- **Dependencies**: stdlib apenas (`dataclasses`)
- **Reuses**: Schema inspirado em `AudioAlert` da branch de áudio (Pydantic v2)

---

### `ModuleAdapter` (abstract base class)

- **Purpose**: Contrato que todo adaptador de módulo deve implementar. Garante extensibilidade sem mudança no core.
- **Location**: `fusion.py`
- **Interface**:
  ```python
  from abc import ABC, abstractmethod

  class ModuleAdapter(ABC):
      @abstractmethod
      def run(self, **kwargs) -> list[AlertaNormalizado]:
          """Executa o pipeline do módulo e retorna alertas normalizados."""
          ...
  ```
- **Dependencies**: stdlib (`abc`)

---

### `ClinicalAdapter(ModuleAdapter)`

- **Purpose**: Executa o pipeline clínico (eICU Demo) e normaliza `sample_id` → `module_id`
- **Location**: `fusion.py`
- **Interface**:
  ```python
  class ClinicalAdapter(ModuleAdapter):
      def __init__(
          self,
          data_dir: str | Path | None = None,
          patient_id: str | None = None,   # None = retorna todos os anômalos
      ): ...
      def run(self) -> list[AlertaNormalizado]: ...
  ```
- **Dependencies**: `eicu-anomaly-detection/src/` (via `sys.path`)
- **Reuses**: `EICUDataLoader`, `ClinicalFeatureBuilder`, `ClinicalAnomalyDetector`, `AlertGenerator`
- **Normalização**: `alert["sample_id"]` → `module_id`
- **`data_dir`**: quando `None`, usa o path padrão. Quando fornecido, passa para `EICUDataLoader(data_dir=data_dir)`.
- **`patient_id`**: quando `None`, retorna todos os alertas anômalos (modo lote). Quando fornecido, filtra os alertas pelo `sample_id == patient_id` **após** a predição em lote. O modelo sempre treina com todos os dados — só o output é filtrado.
- **Filtro ID inexistente**: se `patient_id` não existe no dataset, retorna `[]` sem erro.

---

### `VideoAdapter(ModuleAdapter)`

- **Purpose**: Executa o pipeline de vídeo e normaliza `patient_id` → `module_id`
- **Location**: `fusion.py`
- **Interface**:
  ```python
  class VideoAdapter(ModuleAdapter):
      def __init__(
          self,
          video_path: str,
          patient_id: str = "video_001",   # aparece como module_id no alerta
          sem_objetos: bool = False,
          verbose: bool = True,
      ): ...
      def run(self) -> list[AlertaNormalizado]: ...
  ```
- **Dependencies**: `modulo_video/src/` (via `sys.path`)
- **Reuses**: `pipeline.processar_video()` — retorna dict de alerta diretamente
- **Normalização**: `alert["patient_id"]` → `module_id`
- **`patient_id`**: sempre obrigatório conceitualmente; default `"video_001"` quando não fornecido pelo CLI.

---

### `MultimodalFusion`

- **Purpose**: Recebe listas de `AlertaNormalizado` de múltiplos adaptadores e produz o `FinalReport`
- **Location**: `fusion.py`
- **Interface**:
  ```python
  class MultimodalFusion:
      def fuse(self, listas: list[list[AlertaNormalizado]]) -> dict: ...
      def _score_medio(self, alertas: list[AlertaNormalizado]) -> float: ...
      def _nivel_mais_critico(self, alertas: list[AlertaNormalizado]) -> str: ...
      def _recomendacao(self, nivel: str) -> str: ...
      def _classificar_nivel(self, score: float) -> str: ...
  ```
- **Dependencies**: `AlertaNormalizado`
- **Lógica de score**:
  - `score_medio` = média aritmética de todos os `score_risco`
  - `nivel_mais_critico` = `nivel_risco` do alerta com maior `score_risco`
  - `recomendacao_geral` = baseada em `nivel_mais_critico`

---

### `main.py` (CLI)

- **Purpose**: Ponto de entrada — valida argumentos, instancia adaptadores, executa fusão, salva e imprime
- **Location**: `main.py` (raiz)
- **Interface**:
  ```
  python main.py --video <path> [--clinical-patient-id <id>] [--video-patient-id <id>]
                               [--eicu-data <dir>] [--saida <path>] [--sem-objetos] [--silencioso]
  ```
- **Dependencies**: `fusion.py`, `argparse`, `json`, `pathlib`
- **Argumentos**:
  | Argumento | Padrão | Descrição |
  |-----------|--------|-----------|
  | `--video` | obrigatório | Path do MP4 para o módulo de vídeo |
  | `--clinical-patient-id` | `None` (lote) | Filtra alertas clínicos por `patientunitstayid` após predição |
  | `--video-patient-id` | `"video_001"` | ID que aparece como `module_id` no alerta de vídeo |
  | `--eicu-data` | `eicu-anomaly-detection/modulo_anomalias/data/raw/` | Path dos CSVs eICU |
  | `--saida` | `outputs/final_multimodal_report.json` | Path do relatório final |
  | `--sem-objetos` | False | Desativa YOLOv8 no módulo de vídeo |
  | `--silencioso` | False | Suprime logs dos módulos |
- **Fluxo**:
  1. Parse args
  2. Validar existência do vídeo e do `--eicu-data` dir — falhar cedo com mensagem clara
  3. `ClinicalAdapter(data_dir=args.eicu_data, patient_id=args.clinical_patient_id).run()` → `alertas_clinicos`
  4. `VideoAdapter(video_path=args.video, patient_id=args.video_patient_id).run()` → `alertas_video`
  5. `MultimodalFusion().fuse([alertas_clinicos, alertas_video])` → `report`
  6. `outputs/`.mkdir → salvar JSON → imprimir

---

## Data Models

### `FinalReport` (dict / JSON de saída)

```python
{
    "gerado_em": "2026-07-18T14:30:22",          # datetime.now().isoformat()
    "resumo": {
        "total_alertas": int,
        "score_medio": float,                      # round(média, 3)
        "nivel_mais_critico": str,                 # "baixo" | "moderado" | "alto"
        "modulos_analisados": list[str],           # sorted, todos os módulos chamados
        "modulos_com_alerta": list[str],           # sorted, módulos que geraram ≥1 alerta
        "recomendacao_geral": str
    },
    "alertas": [
        {
            "module_id": str,
            "modulo": str,
            "tipo_anomalia": str,
            "score_risco": float,
            "nivel_risco": str,
            "descricao": str,
            "recomendacao": str
        }
    ]
}
```

### Faixas de risco (unificadas)

| Nível | Score |
|-------|-------|
| baixo | 0.00 – 0.39 |
| moderado | 0.40 – 0.69 |
| alto | 0.70 – 1.00 |

---

## Error Handling Strategy

| Cenário | Handling | Saída para o usuário |
|---------|----------|---------------------|
| Arquivo de vídeo não encontrado | `sys.exit(1)` | `"Erro: arquivo de vídeo não encontrado: <path>"` |
| Dados eICU ausentes em `data/raw/` | `sys.exit(1)` | `"Erro: dados eICU não encontrados. Baixe de https://physionet.org/..."` |
| Módulo retorna 0 alertas | Continua normalmente | `resumo.total_alertas = 0`, `alertas = []` |
| `outputs/` não existe | `mkdir(parents=True, exist_ok=True)` | Criada silenciosamente |
| Exceção inesperada em adaptador | Captura + mensagem + `sys.exit(1)` | `"Erro ao executar módulo <nome>: <mensagem>"` |

---

## Tech Decisions

| Decisão | Escolha | Racional |
|---------|---------|---------|
| Injeção de `sys.path` nos adaptadores | `sys.path.insert(0, ...)` antes do import | Evita instalar cada módulo como pacote; os módulos não têm `setup.py` |
| `dataclass` vs Pydantic para `AlertaNormalizado` | `dataclass` | Sem dependência extra; Pydantic fica para o módulo de áudio quando integrado |
| Execução sequencial | Default sem ThreadPoolExecutor | CPU local; paralelismo adiciona complexidade sem ganho real em batch local |
| `src/fusion.py` → `fusion.py` na raiz | Mover e refatorar | `src/` sozinha na raiz é inconsistente; fusão é o integrador do projeto |
| Fixtures de teste em `tests/fixtures/` | JSONs estáticos + `test_video.mp4` | CI usa os mesmos dados — sem dados sintéticos separados |
| Adaptadores recebem paths como parâmetro | `ClinicalAdapter(data_dir=)`, `VideoAdapter(video_path=)` | Desacopla os módulos dos paths hardcoded — testes passam fixtures, CI passa paths configuráveis, sem monkey-patching |
| Modificar `EICUDataLoader` para aceitar `data_dir` | `data_dir: Path \| None = None` com fallback para `config.DATA_RAW_DIR` | Mínima mudança no módulo clínico; compatibilidade retroativa garantida; habilita flexibilidade nos adaptadores |

---

## CI — GitHub Actions

**Arquivo**: `.github/workflows/fusion.yml`

**Fluxo**:
1. Checkout
2. Setup Python 3.11
3. `pip install -r requirements.txt`
4. Download eICU Demo (wget com `PHYSIONET_USER` / `PHYSIONET_PASSWORD` secrets)
5. `python main.py --video tests/fixtures/test_video.mp4 --patient-id ci_test`
6. `python -c "import json; r=json.load(open('outputs/final_multimodal_report.json')); assert 'resumo' in r and 'alertas' in r"`
7. `pytest tests/test_fusion.py`

**Pré-condições**: secrets `PHYSIONET_USER` e `PHYSIONET_PASSWORD` configurados no repositório GitHub.
