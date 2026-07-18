# Fusão Multimodal — Tasks

**Spec**: `.specs/features/fusao-multimodal/spec.md`
**Design**: `.specs/features/fusao-multimodal/design.md`
**Status**: Draft

---

## Execution Plan

```
Phase 1 — Foundation (Sequential)
  T1 → T2 → T2b

Phase 2 — Core Implementation (Parallel OK)
  T2b ──┬── T3 [P]
        ├── T4 [P]
        └── T5 [P]

Phase 3 — Integration (Sequential)
  T3, T4, T5 → T6 → T7

Phase 4 — CI e Cleanup (Sequential)
  T7 → T8 → T9
```

```
T1 ──► T2 ──► T2b ──┬──► T3 [P] ──┐
                     ├──► T4 [P] ──┼──► T6 ──► T7 ──► T8 ──► T9
                     └──► T5 [P] ──┘
```

---

## Task Breakdown

### T1: Mover e limpar `fusion.py`

**What**: Mover `src/fusion.py` para `fusion.py` na raiz, remover a pasta `src/`, e apagar o conteúdo do rascunho — deixar apenas o arquivo vazio com docstring de módulo.
**Where**: `fusion.py` (raiz) — criar; `src/` — remover
**Depends on**: None
**Requirement**: FUS-03

**Done when**:
- [ ] `fusion.py` existe na raiz com docstring de módulo
- [ ] `src/fusion.py` e `src/` foram removidos
- [ ] `git status` não mostra `src/` como pasta rastreada
- [ ] Nenhum import quebrado em outros arquivos

**Tests**: none
**Gate**: `python -c "import fusion"` executa sem erro

**Commit**: `refactor: mover fusion.py para raiz e remover pasta src/`

---

### T2: Definir `AlertaNormalizado` e `ModuleAdapter`

**What**: Criar a dataclass `AlertaNormalizado` e a ABC `ModuleAdapter` em `fusion.py`.
**Where**: `fusion.py`
**Depends on**: T1
**Requirement**: FUS-12

**Done when**:
- [ ] `@dataclass class AlertaNormalizado` com campos: `module_id`, `modulo`, `tipo_anomalia`, `score_risco`, `nivel_risco`, `descricao`, `recomendacao`
- [ ] `class ModuleAdapter(ABC)` com método abstrato `run(**kwargs) -> list[AlertaNormalizado]`
- [ ] `python -c "from fusion import AlertaNormalizado, ModuleAdapter"` sem erro

**Tests**: none
**Gate**: `python -c "from fusion import AlertaNormalizado, ModuleAdapter"`

**Commit**: `feat(fusion): adicionar AlertaNormalizado e ModuleAdapter`

---

### T2b: Tornar `EICUDataLoader` flexível [P com T3]

**What**: Modificar `EICUDataLoader.__init__` para aceitar `data_dir: Path | None = None`. Quando `None`, usa `config.DATA_RAW_DIR` (comportamento atual). Quando fornecido, usa o path passado. Compatibilidade retroativa garantida.
**Where**: `eicu-anomaly-detection/src/data_loader.py`
**Depends on**: T2
**Requirement**: FUS-01, FUS-05

**Done when**:
- [ ] `EICUDataLoader(data_dir=None)` mantém comportamento atual
- [ ] `EICUDataLoader(data_dir=Path("tests/fixtures/eicu/"))` usa o path passado para todos os arquivos CSV
- [ ] `load_vital_periodic()`, `load_labs()`, `load_medications()` usam `self.data_dir / filename`
- [ ] Testes existentes (se houver) continuam passando

**Tests**: unit
**Gate**: `python -c "from src.data_loader import EICUDataLoader; EICUDataLoader()"` sem erro

**Commit**: `feat(eicu): EICUDataLoader aceita data_dir opcional`

---

### T3: Implementar `ClinicalAdapter` [P]

**What**: Criar `ClinicalAdapter(ModuleAdapter)` que injeta `eicu-anomaly-detection/src` no `sys.path`, executa o pipeline clínico passando `data_dir` ao `EICUDataLoader`, e retorna `list[AlertaNormalizado]` com `sample_id` normalizado para `module_id`.
**Where**: `fusion.py`
**Depends on**: T2, T2b
**Reuses**: `eicu-anomaly-detection/src/train.py`, `EICUDataLoader`
**Requirement**: FUS-01, FUS-10

**Done when**:
- [ ] `ClinicalAdapter(data_dir=None)` implementa `ModuleAdapter`
- [ ] `__init__` aceita `data_dir: str | Path | None = None`
- [ ] `sys.path` injeta `eicu-anomaly-detection/` e `eicu-anomaly-detection/src/` antes do import
- [ ] Pipeline clínico roda passando `data_dir` ao `EICUDataLoader`
- [ ] `sample_id` de cada alerta é mapeado para `module_id` no `AlertaNormalizado`
- [ ] Testes unitários cobrem: normalização de `sample_id`, `data_dir` alternativo, lista vazia

**Tests**: unit
**Gate**: `pytest tests/test_fusion.py -k "clinical"` passa

**Commit**: `feat(fusion): implementar ClinicalAdapter`

---

### T4: Implementar `VideoAdapter` [P]

**What**: Criar `VideoAdapter(ModuleAdapter)` que injeta `modulo_video/` no `sys.path`, chama `processar_video()` e retorna `list[AlertaNormalizado]` com `patient_id` normalizado para `module_id`.
**Where**: `fusion.py`
**Depends on**: T2
**Reuses**: `modulo_video/src/pipeline.py:processar_video()`
**Requirement**: FUS-02, FUS-11

**Done when**:
- [ ] `VideoAdapter` implementa `ModuleAdapter`
- [ ] `__init__` recebe `video_path: str`, `patient_id: str`, `sem_objetos: bool = False`
- [ ] `sys.path` injeta `modulo_video/` antes do import
- [ ] `patient_id` do alerta retornado é mapeado para `module_id`
- [ ] Se `video_path` não existe, levanta `FileNotFoundError` com mensagem clara
- [ ] Testes unitários cobrem: normalização de `patient_id`, `FileNotFoundError`

**Tests**: unit
**Gate**: `pytest tests/test_fusion.py -k "video"` passa

**Commit**: `feat(fusion): implementar VideoAdapter`

---

### T5: Implementar `MultimodalFusion` [P]

**What**: Criar `MultimodalFusion` em `fusion.py` com métodos `fuse()`, `_score_medio()`, `_nivel_mais_critico()`, `_classificar_nivel()`, `_recomendacao()`.
**Where**: `fusion.py`
**Depends on**: T2
**Requirement**: FUS-06, FUS-07, FUS-08, FUS-09

**Done when**:
- [ ] `fuse(listas: list[list[AlertaNormalizado]]) -> dict` retorna `FinalReport`
- [ ] `score_medio` = média aritmética dos `score_risco` (round 3 casas)
- [ ] `nivel_mais_critico` = `nivel_risco` do alerta com maior `score_risco`
- [ ] `recomendacao_geral` baseada em `nivel_mais_critico` (tabela do design)
- [ ] `modulos_analisados` = todos os módulos passados (sorted)
- [ ] `modulos_com_alerta` = módulos com ≥ 1 alerta (sorted)
- [ ] `gerado_em` = `datetime.now().isoformat()`
- [ ] Faixas de risco: baixo < 0.40, moderado 0.40–0.69, alto ≥ 0.70
- [ ] Testes unitários cobrem: score médio, nível crítico preservado, 0 alertas, 1 módulo só

**Tests**: unit
**Gate**: `pytest tests/test_fusion.py -k "fusion"` passa

**Commit**: `feat(fusion): implementar MultimodalFusion`

---

### T6: Criar `main.py` e `tests/fixtures/`

**What**: Criar `main.py` na raiz com CLI via `argparse`, criar fixture `tests/fixtures/test_video.mp4` (vídeo curto público), e criar `tests/test_fusion.py` com todos os casos unitários.
**Where**: `main.py`, `tests/fixtures/test_video.mp4`, `tests/test_fusion.py`
**Depends on**: T3, T4, T5
**Requirement**: FUS-01, FUS-03, FUS-04, FUS-05, FUS-17, FUS-18, FUS-19

**Done when**:
- [ ] `main.py` aceita `--video`, `--patient-id`, `--eicu-data`, `--saida`, `--sem-objetos`, `--silencioso`
- [ ] `--eicu-data` tem default `eicu-anomaly-detection/modulo_anomalias/data/raw/`
- [ ] Valida existência do vídeo antes de chamar adaptadores — `sys.exit(1)` com mensagem
- [ ] Valida existência do `--eicu-data` dir — `sys.exit(1)` com instrução de download
- [ ] Cria `outputs/` se não existir
- [ ] Salva `outputs/final_multimodal_report.json`
- [ ] Imprime relatório formatado no terminal
- [ ] `tests/fixtures/test_video.mp4` existe e é um vídeo MP4 válido (mínimo 5s, < 2MB)
- [ ] `pytest tests/test_fusion.py` passa com ≥ 6 testes cobrindo: score_medio, nivel_critico, recomendacao, normalização IDs, 0 alertas, 1 módulo
- [ ] `python main.py --help` imprime usage sem erro

**Tests**: unit
**Gate**: `pytest tests/test_fusion.py` passa (≥ 6 testes)

**Commit**: `feat: adicionar main.py, fixtures e testes unitários da fusão`

---

### T7: Teste end-to-end local

**What**: Executar `python main.py --video tests/fixtures/test_video.mp4 --patient-id e2e_test` localmente com os dados eICU reais e validar o relatório gerado.
**Where**: execução local (não cria arquivos novos)
**Depends on**: T6
**Requirement**: FUS-01, FUS-02, FUS-03, FUS-04

**Done when**:
- [ ] Comando executa sem erro até o fim
- [ ] `outputs/final_multimodal_report.json` existe e é JSON válido
- [ ] JSON contém `resumo.score_medio`, `resumo.nivel_mais_critico`, `resumo.recomendacao_geral`
- [ ] JSON contém lista `alertas` com pelo menos 1 alerta do módulo clínico
- [ ] Terminal imprime o relatório formatado

**Tests**: none (validação manual)
**Gate**: `python -c "import json; r=json.load(open('outputs/final_multimodal_report.json')); assert 'resumo' in r and 'alertas' in r; print('OK')"`

**Commit**: — (sem commit — task de validação)

---

### T8: Criar workflow CI GitHub Actions

**What**: Criar `.github/workflows/fusion.yml` que baixa eICU Demo, roda a pipeline completa e valida o JSON gerado.
**Where**: `.github/workflows/fusion.yml`
**Depends on**: T7
**Requirement**: FUS-14, FUS-15, FUS-16

**Done when**:
- [ ] Workflow dispara em `push` e `pull_request` no branch `main`
- [ ] Step de download usa `wget` com `${{ secrets.PHYSIONET_USER }}` e `${{ secrets.PHYSIONET_PASSWORD }}`
- [ ] Baixa os 3 arquivos necessários: `vitalPeriodic.csv.gz`, `lab.csv.gz`, `medication.csv.gz`
- [ ] Roda `python main.py --video tests/fixtures/test_video.mp4 --patient-id ci_test`
- [ ] Valida estrutura do JSON com `python -c "..."`
- [ ] Roda `pytest tests/test_fusion.py`
- [ ] Se secrets não configurados, step de download falha com mensagem de erro no log

**Tests**: none
**Gate**: Push em branch de teste → job `fusion` passa verde no GitHub Actions

**Commit**: `ci: adicionar workflow de fusão multimodal`

---

### T9: Atualizar README e remover `src/`

**What**: Atualizar a seção "Integração futura" do `README.md` para documentar a execução do `main.py`, e garantir que `src/` foi removida do tracking do git.
**Where**: `README.md`
**Depends on**: T8
**Requirement**: FUS-03

**Done when**:
- [ ] README tem seção "Fusão Multimodal" com comando `python main.py --video <path>`
- [ ] README documenta pré-requisitos: dados eICU em `data/raw/` e arquivo de vídeo
- [ ] README menciona o relatório gerado em `outputs/final_multimodal_report.json`
- [ ] `src/` não aparece em `git status` nem em `git ls-files`

**Tests**: none
**Gate**: `git ls-files src/` retorna vazio

**Commit**: `docs: atualizar README com instruções da fusão multimodal`

---

## Granularity Check

| Task | Escopo | Status |
|------|--------|--------|
| T1: Mover fusion.py | 1 operação de refactor | ✅ Granular |
| T2: AlertaNormalizado + ModuleAdapter | 2 classes no mesmo arquivo, cohesivas | ✅ OK |
| T2b: EICUDataLoader flexível | 1 modificação pontual em 1 arquivo | ✅ Granular |
| T3: ClinicalAdapter | 1 classe | ✅ Granular |
| T4: VideoAdapter | 1 classe | ✅ Granular |
| T5: MultimodalFusion | 1 classe | ✅ Granular |
| T6: main.py + fixtures + testes | 3 arquivos mas todos integração do mesmo passo | ✅ OK |
| T7: E2E local | 1 validação | ✅ Granular |
| T8: CI workflow | 1 arquivo | ✅ Granular |
| T9: README | 1 arquivo | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends on (body) | Diagram mostra | Status |
|------|------------------|---------------|--------|
| T1 | None | Início | ✅ |
| T2 | T1 | T1 → T2 | ✅ |
| T2b | T2 | T2 → T2b | ✅ |
| T3 | T2, T2b | T2b → T3 | ✅ |
| T4 | T2 | T2b → T4 | ✅ |
| T5 | T2 | T2b → T5 | ✅ |
| T6 | T3, T4, T5 | T3,T4,T5 → T6 | ✅ |
| T7 | T6 | T6 → T7 | ✅ |
| T8 | T7 | T7 → T8 | ✅ |
| T9 | T8 | T8 → T9 | ✅ |

---

## Test Co-location Validation

| Task | Camada criada | Requer teste | Task diz | Status |
|------|--------------|-------------|---------|--------|
| T1 | refactor (sem lógica) | none | none | ✅ |
| T2 | dataclass + ABC | none (sem lógica) | none | ✅ |
| T2b | EICUDataLoader modificado | unit | unit | ✅ |
| T3 | ClinicalAdapter | unit | unit | ✅ |
| T4 | VideoAdapter | unit | unit | ✅ |
| T5 | MultimodalFusion | unit | unit | ✅ |
| T6 | main.py + testes | unit (colocados) | unit | ✅ |
| T7 | validação | none | none | ✅ |
| T8 | CI workflow | none | none | ✅ |
| T9 | docs | none | none | ✅ |
