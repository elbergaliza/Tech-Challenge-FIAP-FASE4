# Implementation Plan: Pipeline de Audio - Alerta Padronizado (`audio_texto`)

**Branch**: `001-audio-texto-pipeline` | **Date**: 2026-07-12 | **Spec**: `specs/001-audio-texto-pipeline/spec.md`

**Input**: Feature specification from `specs/001-audio-texto-pipeline/spec.md`; technical decisions from `docs/spec/plan-argument.md`, `docs/spec/decisions.md`, and `docs/plano-implementacao.md`.

## Summary

Implementar o modulo de audio como biblioteca Python importavel e CLI minima, processando uma gravacao por invocacao para gerar exatamente um alerta JSON padronizado com `modulo = "audio_texto"`. A Camada A e obrigatoria e usa Azure Speech to Text (`pt-BR`) e Azure Text Analytics sobre a transcricao; a Camada B entra apenas no escopo minimo, com heuristicas acusticas simples de intensidade, pausas e RMS usando `pydub`/`librosa`, sem MFCC ou espectrograma completo nesta fase.

O modulo permanece desacoplado de `video_pipeline`, `text_pipeline`, `fusion`, `anomaly` e `alerts`. A persistencia sera em filesystem local (`data/processed/` e `data/reports/`), sem banco, ORM, API web, Flask, autenticacao ou autorizacao de usuario.

## Technical Context

**Language/Version**: Python 3.14 (`requires-python >=3.14`), gerenciado com `uv`.

**Primary Dependencies**: `azure-cognitiveservices-speech`, `azure-ai-textanalytics`, `python-dotenv`, `moviepy`, `pydub`, `librosa`, `pydantic`, `typer`; dev/test: `pytest`, `pytest-mock`, `ruff`, `pyright`; `structlog` opcional, mantendo fallback com `logging` padrao.

**Storage**: Filesystem local. Entradas em `data/raw/`, artefatos intermediarios em `data/processed/` e alertas finais em `data/reports/`; sem banco de dados, ORM ou storage remoto nesta feature.

**Testing**: `pytest` para testes unitarios por etapa, mocks das APIs Azure, testes de contrato do schema Pydantic do alerta e entrada, fixtures locais para amostras Coswara/PT-BR; integracao Azure opcional com VCR/fixtures controladas; `ruff` e `pyright` conforme constituicao.

**Target Platform**: Desenvolvimento local Windows 10/11; execucao local batch; compatibilidade Linux para CI.

**Project Type**: Biblioteca Python + CLI Typer. Nao e web-service, nao possui UI web e nao expoe endpoints HTTP nesta fase.

**Performance Goals**: Processamento completo em ate 60 segundos por gravacao, parametrizavel por configuracao; suporta WAV/MP3 de ate 10 minutos e 50 MB conforme spec.

**Constraints**: Azure Speech to Text e Azure Text Analytics sao obrigatorios para audio; Whisper, Google Speech, SpeechRecognition e Comprehend nao substituem Azure nesta feature. Credenciais apenas via variaveis de ambiente/.env nao versionado; logs nao podem conter audio, transcricao nem termos clinicos. Processamento single-recording, sem streaming ou lote massivo.

**Scale/Scope**: MVP com subconjunto Coswara de 20 a 50 participantes para tosse/respiracao e 2 a 3 WAV PT-BR locais para demo da Camada A. MFCC, espectrograma completo, modelos treinados e AudioSet ficam para pos-MVP.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate (Principle) | Status |
|---|---|---|
| I | A abordagem e a solucao mais simples adequada? Sem abstracoes prematuras? | PASS - biblioteca + CLI, filesystem local, regras explicitas e sem framework web/banco. |
| III | O plano respeita os limites de modulo (`audio_pipeline`, `video_pipeline`, `text_pipeline`, `anomaly`, `alerts`, `fusion`)? | PASS - somente `audio_texto`; demais modulos fora de escopo. |
| IV | O plano inclui toolchain de qualidade: `ruff`, `mypy`/`pyright`, `pytest`? | PASS - `ruff`, `pyright` e `pytest` definidos no contexto tecnico. |
| V | O plano define cobertura de testes proporcional ao risco clinico? | PASS - unitarios, contrato de schema, mocks Azure e casos de falso alarme/termos criticos. |
| VI | A spec correspondente foi criada ou atualizada antes desta fase? | PASS - `specs/001-audio-texto-pipeline/spec.md` existe e contem clarificacoes de score, escopo e NFRs. |
| VII | Anonimizacao de dados clinicos esta enderecada (obrigatorio para modulos com servicos externos)? | PASS - `patient_id` em logs deve ser anonimizado/referencia; audio/transcricao/termos nao sao logados. |
| VIII | Todas as credenciais serao carregadas via `.env`/variaveis de ambiente (nenhuma em codigo)? | PASS - `python-dotenv` e variaveis de ambiente; `.env` ja esta no `.gitignore`. |

## Project Structure

### Documentation (this feature)

```text
specs/001-audio-texto-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── audio-input.schema.json
│   ├── audio-alert.schema.json
│   ├── cli.md
│   ├── python-api.md
│   └── transcription.json
└── tasks.md              # criado depois por /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── audio_pipeline.py      # API publica importavel e orquestracao single-recording
├── audio_cli.py           # CLI Typer minima
├── audio_schemas.py       # modelos Pydantic v2 de entrada, intermediarios e alerta
├── audio_azure.py         # adaptadores Azure Speech/Text Analytics
├── audio_acoustics.py     # heuristicas minimas pydub/librosa
├── audio_scoring.py       # regras FR-003, FR-007 e FR-008
└── audio_storage.py       # escrita JSON em data/processed e data/reports

tests/
├── contract/
│   ├── test_audio_input_contract.py
│   └── test_audio_alert_contract.py
├── integration/
│   └── test_audio_pipeline_with_fixtures.py
└── unit/
    ├── test_audio_scoring.py
    ├── test_audio_acoustics.py
    ├── test_audio_azure_adapters.py
    └── test_audio_pipeline.py

data/
├── raw/
│   ├── coswara/           # local, nao versionado
│   └── pt-br/             # 2-3 WAV locais para demo, nao versionados
├── processed/             # transcricoes/metadados sem segredos
└── reports/               # alerta JSON padronizado
```

**Structure Decision**: Usar projeto Python unico com `src/` no repositorio raiz. `src/audio_pipeline.py` sera o ponto importavel principal; os demais arquivos so existem para manter responsabilidades pequenas e testaveis dentro do limite do modulo de audio. Nao criar `backend/`, `frontend/`, Flask, FastAPI, banco, ORM ou autenticacao nesta feature.

## Complexity Tracking

Sem violacoes constitucionais identificadas. Nenhuma justificativa de complexidade adicional e necessaria.

## Phase 0 Research Summary

Todas as lacunas tecnicas foram resolvidas em `research.md`. Decisoes centrais: Azure obrigatorio para audio, Typer para CLI minima, Pydantic v2 para contratos, filesystem JSON para armazenamento, Coswara + amostras PT-BR locais para demo, Camada B minima com heuristicas acusticas simples e logs estruturados sem conteudo clinico.

## Phase 1 Design Summary

Artefatos de design criados:

- `data-model.md`: entidades, campos, validacoes e transicoes de estado.
- `contracts/audio-input.schema.json`: contrato JSON da entrada.
- `contracts/audio-alert.schema.json`: contrato JSON do alerta final.
- `contracts/cli.md`: contrato da CLI Typer.
- `contracts/python-api.md`: contrato da API Python importavel.
- `contracts/transcription.json`: contrato de origem/granularidade da confianca do Azure Speech (resolve CHK003; adicionado via remediacao de `/speckit-analyze`).
- `quickstart.md`: setup local, comandos `uv`, variaveis de ambiente e validacoes esperadas.

## Post-Design Constitution Check

| # | Gate (Principle) | Status |
|---|---|---|
| I | Simplicidade e clareza | PASS - contratos e modelos sao diretos; sem infraestrutura alem do necessario. |
| III | Modularidade | PASS - somente modulo de audio, com fronteiras explicitas. |
| IV | Qualidade Python | PASS - plano inclui `pytest`, `ruff` e `pyright`. |
| V | Testes por risco | PASS - casos de alto risco, baixo risco, sem fala e entrada invalida cobertos por contrato/testes. |
| VI | Spec como fonte | PASS - design deriva de `spec.md` e das decisoes registradas. |
| VII | LGPD | PASS - logs e contratos evitam conteudo clinico sensivel em observabilidade. |
| VIII | Credenciais | PASS - credenciais apenas por ambiente/.env local nao versionado. |
