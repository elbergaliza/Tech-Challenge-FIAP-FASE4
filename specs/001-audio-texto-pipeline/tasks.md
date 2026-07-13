# Tasks: Pipeline de Áudio — Alerta Padronizado (`audio_texto`)

**Input**: Design documents from `specs/001-audio-texto-pipeline/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/audio/audio/ ✅ | quickstart.md ✅

**Tests**: Incluídos — obrigatórios conforme Princípio V da constituição (testes proporcionais ao risco clínico).

**Organization**: Tasks organizadas por user story para implementação e validação independente de cada story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo (arquivos diferentes, sem dependências não satisfeitas)
- **[Story]**: User story a que a task pertence (US1–US4)
- Caminhos exatos de arquivo incluídos conforme plan.md

---

## Phase 1: Setup (Infraestrutura Compartilhada)

**Purpose**: Inicialização do projeto e estrutura de diretórios conforme plan.md

- [X] T001 Criar estrutura de diretórios `src/audio/audio/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, `data/raw/coswara/`, `data/raw/pt-br/`, `data/processed/`, `data/reports/` com `.gitkeep` nos diretórios `data/` (não versionar áudio real)
- [X] T002 Adicionar dependências de produção via `uv add`: `azure-cognitiveservices-speech` `azure-ai-textanalytics` `python-dotenv` `moviepy` `pydub` `librosa` `pydantic` `typer`
- [X] T003 [P] Adicionar dependências de dev via `uv add --dev`: `pytest` `pytest-mock` `ruff` `pyright`
- [X] T004 [P] Criar `.env.example` na raiz com as 4 variáveis obrigatórias (`AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AZURE_TEXT_ANALYTICS_KEY`, `AZURE_TEXT_ANALYTICS_ENDPOINT`) sem valores reais; confirmar que `.env` está no `.gitignore`
- [X] T005 [P] Configurar `ruff` e `pyright` em `pyproject.toml` com target Python 3.14, perfil PEP 8 e regras de tipos estritas para `src/audio/audio/`

**Checkpoint**: `uv sync` e `uv run ruff check .` executam sem erros fatais

---

## Phase 2: Foundational (Pré-requisitos Bloqueantes)

**Purpose**: Schemas, contratos, exceções e storage — componentes que TODAS as user stories dependem

**⚠️ CRÍTICO**: Nenhuma user story pode começar sem esta fase completa

- [X] T006 Criar `src/audio/audio/audio_schemas.py` com todos os modelos Pydantic v2 conforme `data-model.md`: `AudioProcessingRequest` (patient_id, audio_path, language, source, max_duration_seconds, max_size_mb, `timeout_seconds` default `60` — NFR-001), `AudioMetadata` (duration_seconds, size_mb, format, sample_rate_hz, channels), `TranscriptionResult` (text, confidence, language, provider, status enum), `AcousticFeatures` (rms, peak_amplitude, silence_ratio, long_pause_count, cough_or_breathing_indicator, score_acustico, signals), `TextFindings` (critical_terms, sentiment, sentiment_confidence, score_textual, score_textual_efetivo), `AudioAlert` (patient_id, modulo literal "audio_texto", tipo_anomalia, score_risco, nivel_risco, descricao, recomendacao, evidencias com `duracao_processamento_ms` e `excedeu_limite_latencia` — SC-007) com todas as validações de faixa `[0.0, 1.0]` e enumerações
- [X] T007 [P] Adicionar exceções customizadas do módulo em `src/audio/audio/audio_schemas.py`: classe base `AudioPipelineError` com campo `error_code` suportando os códigos `invalid_patient_id`, `unsupported_format`, `file_not_found`, `file_too_large`, `duration_too_long`, `corrupted_audio`, `missing_azure_configuration`
- [X] T008 [P] Criar `tests/contract/test_audio_input_contract.py` para validar `AudioProcessingRequest` contra `specs/001-audio-texto-pipeline/contracts/audio/audio/audio-input.schema.json`: patient_id obrigatório, formatos WAV/MP3, limites de tamanho e duração
- [X] T009 [P] Criar `tests/contract/test_audio_alert_contract.py` para validar `AudioAlert` contra `specs/001-audio-texto-pipeline/contracts/audio/audio/audio-alert.schema.json`: modulo fixo "audio_texto", score_risco ∈ [0.0, 1.0], nivel_risco coerente com score (baixo < 0.4, moderado ≥ 0.4, alto ≥ 0.7), todos os 7 campos obrigatórios presentes
- [X] T010 Criar `src/audio/audio/audio_storage.py` com funções `save_processed(patient_id, data, processed_dir)` e `save_report(alert: AudioAlert, output_dir)` escrevendo JSON em `data/processed/` e `data/reports/` respectivamente; logs de storage devem incluir apenas patient_id (como referência) e caminho do arquivo, sem conteúdo clínico

**Checkpoint**: `uv run pytest tests/contract/` deve passar — contratos e schemas validados

---

## Phase 3: User Story 1 — Gerar alerta padronizado a partir de uma gravação de voz (P1) 🎯 MVP

**Goal**: Pipeline ponta a ponta funcional: recebe WAV/MP3 com patient_id → devolve um `AudioAlert` JSON padronizado com score_risco, nivel_risco, descrição e recomendação, via API Python e CLI

**Independent Test**: Fornecer gravação PT-BR com "falta de ar e dor no peito" → alerta com nivel_risco "alto"; fornecer gravação sem queixas → nivel_risco "baixo"; fornecer patient_id vazio → exceção sem alerta gerado

### Tests para US1

- [X] T011 [P] [US1] Criar `tests/unit/test_audio_scoring.py` cobrindo: piso 0.4 com ao menos um termo crítico (SC-003), `score_risco = max(score_acustico, score_textual_efetivo)` com fontes conflitantes, fronteiras exatas baixo/moderado/alto (score=0.4 → moderado, score=0.7 → alto), caso `score_acustico=0.0` e `score_textual_efetivo=0.0` → `tipo_anomalia="nenhuma"` e `nivel_risco="baixo"`
- [X] T012 [US1] Criar `tests/unit/test_audio_pipeline.py` com `pytest-mock` cobrindo: transcrição bem-sucedida com termos críticos → alerta alto, gravação sem fala compreensível (status `no_speech`) → alerta baseado apenas em sinais acústicos (FR-012), entrada com patient_id vazio → `AudioPipelineError(invalid_patient_id)` sem alerta, arquivo em formato não suportado → `AudioPipelineError(unsupported_format)`, sinais conflitantes (score acústico alto, score textual zero) → score_risco = valor acústico alto com descrição citando a fonte (demais cenários de entrada inválida de FR-015 — corrompido/tamanho/duração real — cobertos exclusivamente em T032, para evitar duplicação de teste)

### Implementation para US1

- [X] T013 [P] [US1] Criar `src/audio/audio/audio_azure.py` com adaptador Azure Speech to Text: `SpeechConfig(subscription, region, speech_recognition_language="pt-BR")` com `OutputFormat.Detailed`, `recognize_once()` sobre arquivo WAV, extração de `confidence` a partir de `NBest[0].Confidence` conforme `contracts/audio/transcription.json` (resolve CHK003), com `clamp` defensivo para `[0.0, 1.0]`, mapeamento de resultado para `TranscriptionResult` com status `success`/`no_speech`/`low_confidence`/`failed`; variáveis de ambiente lidas via `python-dotenv`; nenhum conteúdo de transcrição em logs
- [X] T014 [P] [US1] Criar `src/audio/audio_acoustics.py` com análise acústica mínima usando `pydub` e `librosa`: calcular RMS (via pydub `dBFS` ou librosa `rms`), peak_amplitude normalizado para `[0.0, 1.0]`, silence_ratio (proporção de segmentos silenciosos ≥ threshold de dB), long_pause_count (pausas > 1.5 s), cough_or_breathing_indicator (`none`/`possible`/`strong` por heurística de burst de energia), mapear indicadores para `score_acustico ∈ [0.0, 1.0]`, retornar `AcousticFeatures`; sem MFCC ou espectrograma completo nesta fase
- [X] T015 [US1] Adicionar adaptador Azure Text Analytics em `src/audio/audio_azure.py`: `TextAnalyticsClient(endpoint, credential)`, `analyze_sentiment(text, language="pt-BR")` → campo `sentiment` do `TextFindings`, `extract_key_phrases` ou `recognize_entities` para cruzar com lista de termos críticos pré-definida, calcular `score_textual ∈ [0.0, 1.0]` crescente com número de termos distintos e grau de negatividade; nenhum conteúdo do texto em logs; leitura de credenciais via variáveis de ambiente
- [X] T016 [US1] Criar `src/audio/audio_scoring.py` com regras de combinação conforme FR-003/FR-007/FR-008: `score_textual_efetivo = max(score_textual × confiança_transcrição, 0.4)` quando `critical_terms ≥ 1`, caso contrário `score_textual × confiança_transcrição`; `score_risco = max(score_acustico, score_textual_efetivo)`; classificar `nivel_risco` por faixas (baixo < 0.4, 0.4 ≤ moderado < 0.7, alto ≥ 0.7); gerar `descricao` legível citando fonte do score; gerar `recomendacao` coerente com o nível; limitar ambos os scores a `[0.0, 1.0]` antes das operações
- [X] T017 [US1] Criar `src/audio/audio_pipeline.py` com função pública `process_audio_recording(request: AudioProcessingRequest) -> AudioAlert` orquestrando: (0) capturar timestamp de início do pipeline (base para NFR-001/SC-007, ver T029); (1) validar patient_id e arquivo — checagem real do arquivo (bytes/cabeçalho legível, tamanho real via `AudioMetadata.size_mb` e duração real via `AudioMetadata.duration_seconds`, não apenas os defaults do schema de entrada) comparada aos limites de `request` → rejeitar com `corrupted_audio`/`file_too_large`/`duration_too_long`/`unsupported_format` conforme FR-015 se inválido; (2) extrair `AudioMetadata`; (3) Camada A: `TranscriptionResult` via `src/audio/audio_azure.py`; (4) Camada A: `TextFindings` via `src/audio/audio_azure.py` se transcrição disponível; (5) Camada B: `AcousticFeatures` via `src/audio/audio_acoustics.py`; (6) combinar via `src/audio/audio_scoring.py` → `AudioAlert`; (7) calcular `duracao_processamento_ms` e preencher `evidencias.excedeu_limite_latencia` conforme `request.timeout_seconds` (T029); (8) persistir via `src/audio/audio_storage.py`; emitir log estruturado por etapa (duração, patient_id como referência, status) sem conteúdo clínico
- [X] T018 [P] [US1] Criar `src/audio/audio_cli.py` com CLI Typer: comando `process` com opções `--patient-id` (obrigatório), `--audio-path` (obrigatório), `--language` (default `pt-BR`), `--output-dir` (default `data/reports`), `--processed-dir` (default `data/processed`), `--max-duration-seconds` (default `600`), `--max-size-mb` (default `50`); carregar `.env` via `python-dotenv`; em sucesso exibir apenas caminho do relatório e status; em erro retornar exit code não-zero com categoria de erro (conforme contracts/audio/cli.md); nunca exibir credenciais, transcrição ou termos clínicos

**Checkpoint Phase 3**: `uv run pytest tests/` deve passar. `uv run python -m src.audio_cli process --patient-id sample_001 --audio-path data/raw/pt-br/sample.wav` deve gerar JSON em `data/reports/` com todos os 7 campos obrigatórios.

---

## Phase 4: User Story 2 — Obter transcrição confiável da fala do paciente (P2)

**Goal**: Transcrição rastreável com indicador de confiança, persistida para auditoria, com baixa confiança refletida no alerta

**Independent Test**: Fornecer gravação com fala clara → TranscriptionResult com status success e confiança alta; fornecer gravação com ruído → TranscriptionResult com status low_confidence; verificar que transcrição é salva em `data/processed/` e não aparece em logs

### Implementation para US2

- [X] T019 [P] [US2] Criar `tests/unit/test_audio_azure_adapters.py` com mocks do Azure Speech SDK (`pytest-mock`): sucesso com confiança alta (status `success`), confiança abaixo do threshold (status `low_confidence`), sem fala detectada (status `no_speech`), falha de serviço (status `failed`), normalização de confiança de escala alternativa para `[0.0, 1.0]`
- [X] T020 [US2] Adicionar `save_transcription(patient_id, transcription_result, processed_dir)` em `src/audio/audio_storage.py` persistindo `TranscriptionResult` serializado em `data/processed/` para rastreabilidade/auditoria (FR-017); garantir que o texto da transcrição não aparece em nenhum log do pipeline

**Checkpoint Phase 4**: `uv run pytest tests/unit/test_audio_azure_adapters.py` deve cobrir todos os status de transcrição. Arquivo em `data/processed/` gerado após processamento.

---

## Phase 5: User Story 3 — Extrair sinais acústicos de cansaço vocal e dificuldade respiratória (P3)

**Goal**: Produzir `AcousticFeatures` com `score_acustico > 0` para gravações de tosse/respiração sem fala, independentemente da transcrição

**Independent Test**: Fornecer WAV de tosse do Coswara → `cough_or_breathing_indicator = "strong"` e `score_acustico > 0`; fornecer WAV com pausas longas frequentes → `long_pause_count` alto e `score_acustico > 0`; fornecer gravação limpa sem sinais de risco → `score_acustico = 0.0`

### Implementation para US3

- [X] T021 [P] [US3] Criar `tests/unit/test_audio_acoustics.py` com cenários usando fixtures WAV sintéticas (silêncio, burst de energia para tosse, fala de baixa intensidade): tosse alterada → `cough_or_breathing_indicator="strong"` e `score_acustico ≥ 0.5`, pausas longas → `long_pause_count ≥ 3` e `score_acustico > 0`, áudio limpo → `score_acustico = 0.0`, invariantes de faixa `[0.0, 1.0]` para todos os campos numéricos
- [X] T022 [US3] Adicionar suporte a pré-processamento com `moviepy` em `src/audio/audio_pipeline.py`: se o arquivo de entrada for MP4/vídeo, extrair faixa de áudio para WAV temporário antes de passar para `pydub`/`librosa`; garantir cleanup de temporários após processamento

**Checkpoint Phase 5**: Gravação Coswara `breathing-deep` ou `cough-heavy` processada deve gerar `score_acustico > 0` no alerta final.

---

## Phase 6: User Story 4 — Identificar termos críticos e tom de risco no texto transcrito (P4)

**Goal**: Detecção confiável de termos de risco clínico e classificação de sentimento reutilizável em textos já transcritos

**Independent Test**: Fornecer texto "sinto muita dificuldade para respirar desde ontem" → `critical_terms` não vazio e `sentiment = "negative"`; fornecer texto "hoje me sinto bem, sem queixas" → `critical_terms = []` e `sentiment = "neutral"` ou `"positive"`

### Implementation para US4

- [X] T023 [P] [US4] Adicionar cenários de Text Analytics em `tests/unit/test_audio_azure_adapters.py`: mock `TextAnalyticsClient` com frase "falta de ar e dor no peito" → `critical_terms` com ao menos 2 entradas e `score_textual > 0`; texto neutro → `critical_terms = []` e `score_textual = 0.0`; sentimento `mixed` → tratado como negativo para fins de scoring
- [X] T024 [US4] Definir lista de termos críticos configurável em `src/audio/audio_scoring.py` como constante/configuração: `["falta de ar", "dor no peito", "cansaço", "tontura", "piora", "dificuldade para respirar"]`; adicionar comentário no código documentando a limitação de negação linguística (ex.: "não sinto falta de ar" ainda conta como termo crítico nesta versão — débito técnico registrado na spec)

**Checkpoint Phase 6**: `uv run pytest tests/unit/test_audio_azure_adapters.py` deve cobrir casos de termos críticos e sentimento.

---

## Phase 7: Remediação `/speckit-analyze` — Observabilidade, Rejeição de Entrada Inválida e Validação por Amostragem

**Purpose**: Cobrir lacunas identificadas na análise de consistência (`/speckit-analyze`, 2026-07-13): NFR-001/SC-007 (limite de latência configurável e registro de falha de performance), SC-006 (validação por amostragem de baixo falso-alarme), FR-015 (rejeição real de arquivo corrompido/tamanho/duração), NFR-002 (métricas mínimas obrigatórias) e FR-016 (independência entre módulos)

**Depende de**: Phase 3 (US1) completa — usa `src/audio/audio_pipeline.py`, `src/audio/audio_scoring.py` e o subconjunto Coswara/PT-BR já preparados

- [X] T029 [US1] Adicionar medição de latência total em `src/audio/audio_pipeline.py`: capturar timestamp de início/fim do pipeline, calcular `duracao_processamento_ms`, comparar com `request.timeout_seconds` (default `60`, NFR-001) e preencher `AudioAlert.evidencias.excedeu_limite_latencia = True` quando excedido; **não** abortar o processamento nem lançar exceção — apenas registrar a violação como falha de performance observável (SC-007) via log estruturado (ex.: `status="performance_timeout"`) além do campo em `evidencias`
- [X] T030 [P] [US1] Criar `tests/unit/test_audio_latency.py` cobrindo: processamento dentro do `timeout_seconds` configurado → `excedeu_limite_latencia = False` e nenhum log de falha de performance; processamento simulado (via mock de tempo) que excede o limite → `excedeu_limite_latencia = True`, log de falha de performance emitido e `AudioAlert` ainda gerado normalmente; alteração de `timeout_seconds` via parâmetro de configuração sem qualquer mudança de código (NFR-001)
- [X] T031 [P] Criar `tests/integration/test_audio_batch_sample_validation.py` (ou script equivalente em `tests/integration/`) que processa um conjunto de amostras conhecidas sem queixas relevantes e sem sinais acústicos de risco (ex.: 10–20 amostras PT-BR/Coswara "healthy" do subconjunto de demo) e valida que ao menos 90% resultam em `nivel_risco = "baixo"` e `tipo_anomalia = "nenhuma"`, conforme SC-006; documentar no teste a origem/composição da amostra usada
- [X] T032 [P] [US1] Estender `tests/unit/test_audio_pipeline.py` (ou criar `tests/unit/test_audio_input_validation.py`) com fixtures reais cobrindo FR-015 de ponta a ponta via `process_audio_recording`: arquivo WAV vazio/com bytes corrompidos → `AudioPipelineError(corrupted_audio)`; arquivo cujo tamanho em disco excede `max_size_mb` → `AudioPipelineError(file_too_large)`; arquivo cuja duração real (via `AudioMetadata.duration_seconds`) excede `max_duration_seconds` → `AudioPipelineError(duration_too_long)`; em todos os casos, nenhum `AudioAlert` deve ser gerado nem persistido em `data/reports/`
- [X] T033 [P] Criar `tests/unit/test_audio_observability.py` validando as 3 métricas mínimas obrigatórias de NFR-002 emitidas por `src/audio/audio_pipeline.py`: log estruturado contém latência total (`duracao_processamento_ms`), indicação de rejeição de entrada (taxa de rejeição observável a partir do status/`error_code` logado) e o `score_risco` gerado; validar também que nenhum log contém áudio bruto, transcrição ou termos críticos (reforço de VII/VIII)
- [X] T034 [P] Criar `tests/unit/test_audio_module_boundary.py` (opcional, reforça FR-016 e Princípio III da constituição) verificando por inspeção estática de imports que `src/audio/audio_pipeline.py`, `src/audio/audio_azure.py`, `src/audio/audio_acoustics.py`, `src/audio/audio_scoring.py` e `src/audio/audio_storage.py` não importam módulos de outras modalidades (`video_pipeline`, `text_pipeline`, `anomaly`, `alerts`, `fusion`)

**Checkpoint Phase 7**: `uv run pytest tests/unit/test_audio_latency.py tests/integration/test_audio_batch_sample_validation.py tests/unit/test_audio_observability.py tests/unit/test_audio_module_boundary.py` deve passar, cobrindo NFR-001, NFR-002, FR-015, FR-016, SC-006 e SC-007.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Qualidade final, conformidade com toolchain e validação do quickstart

- [X] T035 [P] Executar `uv run ruff check .` e corrigir todos os avisos em `src/audio/` e `tests/` (Princípio IV)
- [X] T036 [P] Executar `uv run pyright` e corrigir erros de tipo em todas as interfaces públicas de `src/audio/audio_pipeline.py`, `src/audio/audio_schemas.py`, `src/audio/audio_azure.py`, `src/audio/audio_scoring.py` e `src/audio/audio_acoustics.py`
- [X] T037 Adicionar docstrings nas interfaces públicas de `src/audio/audio_pipeline.py` (`process_audio_recording`), `src/audio/audio_schemas.py` (classes principais), `src/audio/audio_azure.py` e `src/audio/audio_scoring.py` explicando contratos e invariantes (Princípio X)
- [ ] T038 [P] Validar quickstart.md end-to-end: `uv sync` → configurar `.env` → `uv run pytest` → `uv run ruff check .` → `uv run pyright` → `uv run python -m src.audio.audio_cli process --patient-id demo_001 --audio-path data/raw/pt-br/sample.wav`; verificar alerta JSON gerado em `data/audio/reports/` com todos os 7 campos e `nivel_risco` coerente com o conteúdo do áudio

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode iniciar imediatamente
- **Foundational (Phase 2)**: Depende de Setup (Phase 1) — **bloqueia todas as user stories**
- **US1 (Phase 3)**: Depende de Foundational (Phase 2) — **MVP entregável; integra US2, US3 e US4**
- **US2 (Phase 4)**: Depende de Foundational (Phase 2) e das implementações de `audio_azure.py` criadas na Phase 3 — pode estender em paralelo com US3/US4
- **US3 (Phase 5)**: Depende de Foundational (Phase 2) e de `audio_acoustics.py` criado na Phase 3 — pode estender em paralelo com US2/US4
- **US4 (Phase 6)**: Depende de Foundational (Phase 2) e do adaptador Text Analytics de `audio_azure.py` criado na Phase 3 — pode estender em paralelo com US2/US3
- **Remediação (Phase 7)**: Depende de Phase 3 (US1) completa — pode estender em paralelo com US2/US3/US4
- **Polish (Phase N)**: Depende de todas as user stories desejadas e da Phase 7 estarem completas

### User Story Dependencies

- **US1 (P1)**: Depende de Foundational + implementações internas de transcrição (US2), acústica (US3) e análise de texto (US4) — entregável final do módulo
- **US2 (P2)**: Testável isoladamente após Phase 3 (adaptador Azure Speech já criado)
- **US3 (P3)**: Testável isoladamente após Phase 3 (`audio_acoustics.py` já criado)
- **US4 (P4)**: Testável isoladamente após Phase 3 (adaptador Azure Text Analytics já criado)

### Within Each User Story

- Testes de contrato (Phase 2) antes da implementação
- Testes unitários (marcados no início de cada phase) devem **falhar** antes da implementação
- Schemas e modelos antes de adaptadores e serviços
- Serviços/adaptadores antes da orquestração do pipeline
- Core implementation antes de CLI e integração

### Parallel Opportunities

- T003, T004, T005 podem rodar em paralelo com T002 (durante setup)
- T007, T008, T009 podem rodar em paralelo com T006 (durante foundational)
- T011, T013, T014 podem rodar em paralelo (tests e adaptadores independentes dentro de US1)
- T018 (CLI) pode rodar em paralelo com T017 (pipeline) após T013–T016 completarem
- Phases US2 (4), US3 (5), US4 (6) e Remediação (7) podem ser trabalhadas em paralelo por desenvolvedores diferentes após Phase 3 estar completa
- T030, T031, T032, T033 e T034 podem rodar em paralelo entre si (arquivos de teste diferentes); T030 depende de T029, T032 depende de T017, T033 depende de T017 e T034 não tem dependência de implementação (apenas inspeciona imports)
- T035, T036, T037, T038 podem rodar em paralelo (polish)

---

## Parallel Example: User Story 1

```bash
# Após T006–T010 (Foundational completo):

# Iniciar em paralelo (arquivos diferentes):
Task T011: "Criar tests/unit/test_audio_scoring.py"
Task T013: "Criar src/audio/audio_azure.py (Speech adapter)"
Task T014: "Criar src/audio/audio_acoustics.py"

# Após T013 e T014 concluídos:
Task T015: "Adicionar Text Analytics em src/audio/audio_azure.py"

# Após T015:
Task T016: "Criar src/audio/audio_scoring.py"

# Após T016:
Task T017: "Criar src/audio/audio_pipeline.py"

# Após T017, em paralelo:
Task T018: "Criar src/audio/audio_cli.py"
Task T012: "Criar tests/unit/test_audio_pipeline.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 como entregável)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia tudo)
3. Completar Phase 3: US1 (MVP completo — pipeline ponta a ponta funcional)
4. **PARAR E VALIDAR**: `uv run pytest` + demo CLI com amostra PT-BR
5. Entregar/demonstrar se pronto

### Incremental Delivery

1. Setup + Foundational → Base pronta para desenvolvimento
2. Phase 3 (US1) → Pipeline completo testável → MVP!
3. Phase 4 (US2) → Rastreabilidade de transcrição melhorada
4. Phase 5 (US3) → Cobertura de tosse/respiração sem fala validada
5. Phase 6 (US4) → Configuração de termos críticos e sentimento refinada
6. Phase 7 (Remediação) → Observabilidade de latência (NFR-001/SC-007) e validação por amostragem (SC-006)
7. Phase N (Polish) → Qualidade final, docstrings, quickstart validado

### Parallel Team Strategy

Com múltiplos desenvolvedores após Phase 3:

- Developer A: Melhorias US2 (Phase 4) — foco em rastreabilidade de transcrição
- Developer B: Melhorias US3 (Phase 5) — foco em sinais acústicos Coswara
- Developer C: Melhorias US4 (Phase 6) — foco em termos críticos e sentimento
- Todos: Phase N (Polish) ao final

---

## Notes

- `[P]` = arquivos diferentes, sem dependências pendentes — seguro para paralelo
- Labels `[US1]`–`[US4]` mapeiam para user stories de `spec.md` para rastreabilidade
- Cada user story deve ser independentemente completável e testável após Phase 3
- Testes de contrato (Phase 2) validam invariantes que protegem o alerta clínico
- Credenciais Azure somente via variáveis de ambiente ou `.env` não versionado — nunca em código, commits ou logs (Princípio VIII)
- Logs de todas as etapas não devem conter áudio, transcrição, termos clínicos nem credenciais (Princípios VII e VIII)
- `tipo_anomalia = "nenhuma"` somente quando `score_acustico = 0.0` **e** `score_textual_efetivo = 0.0` (edge case da spec)
- Negação linguística (ex.: "não sinto falta de ar") não é tratada nesta versão — registrar como débito técnico no código (Suposição da spec)
- T029–T034 (Phase 7) foram adicionadas via remediação de `/speckit-analyze` (2026-07-13) para cobrir NFR-001, SC-006, SC-007 (severidade HIGH/MEDIUM) e FR-015, NFR-002, FR-016 (severidade MEDIUM/LOW), que não tinham task associada ou tinham cobertura apenas parcial na geração original de `tasks.md`
- T034 é opcional (severidade LOW) — pode ser adiada sem impacto no MVP se o cronograma estiver apertado
- Segunda rodada de `/speckit-analyze` (2026-07-13): T012 teve os 3 cenários de FR-015 (corrupted_audio/file_too_large/duration_too_long) removidos por duplicação com T032 (D1); T025–T028 (Phase N) foram renumeradas para T035–T038 para restaurar numeração monotônica alinhada à ordem de execução, já que Phase N é executada após a Phase 7 (N1)
