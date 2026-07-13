# Research: Pipeline de Audio - `audio_texto`

## Decision: Python 3.14 com `uv`

**Rationale**: O projeto ja declara `requires-python >=3.14` em `pyproject.toml`, e a regra global do workspace padroniza `uv` para ambiente, execucao e dependencias. Manter Python 3.14 reduz divergencia entre especificacao, plano e futura implementacao.

**Alternatives considered**:

- Python 3.11/3.12: ecossistema mais maduro para algumas bibliotecas de audio, mas conflita com o `pyproject.toml` atual.
- `pip`/`venv`: funcional, mas fora do padrao definido para projetos Python neste workspace.

## Decision: Biblioteca Python importavel + CLI Typer minima

**Rationale**: A feature precisa ser executavel localmente e consumivel por testes/etapas futuras sem expor API web. `Typer` oferece CLI simples e tipada, enquanto `src/audio/audio_pipeline.py` permanece como ponto importavel principal para orquestracao de uma gravacao por invocacao.

**Alternatives considered**:

- Flask/FastAPI: fora do escopo desta feature; adicionaria superficie de autenticacao, deploy e contrato HTTP desnecessarios.
- Script unico sem CLI formal: simples, mas pior para testes, help de comandos e reproducibilidade da demo.

## Decision: Azure Speech to Text e Azure Text Analytics obrigatorios para audio

**Rationale**: O enunciado e o plano macro exigem Azure na etapa de audio. A Camada A usa Speech to Text em `pt-BR` para transcricao e metadados de reconhecimento; Text Analytics processa a transcricao para sentimento, entidades/frases-chave e termos criticos. Nenhum outro provedor substitui Azure nesta feature.

**Alternatives considered**:

- Whisper, Google Speech ou SpeechRecognition: uteis em outros contextos, mas nao atendem o requisito obrigatorio de Azure para audio.
- AWS Comprehend: permanece valido para documentos/texto clinico em outra fase, mas nao substitui Azure Text Analytics nesta feature.

## Decision: Credenciais via ambiente e `python-dotenv`

**Rationale**: A constituicao proibe credenciais em codigo, logs e documentacao publica. `python-dotenv` permite carregar variaveis locais de um `.env` nao versionado, mantendo a mesma interface de configuracao para CLI, testes e execucao manual.

**Alternatives considered**:

- Argumentos CLI com chaves de API: aumenta risco de aparecerem em historico de shell/logs.
- Arquivo de configuracao versionado: inadequado para segredos e contrario ao principio VIII.

## Decision: Filesystem local JSON em `data/audio/processed/` e `data/audio/reports/`

**Rationale**: O MVP nao precisa de consulta concorrente, historico complexo ou relacoes. Arquivos JSON sao suficientes para transcricoes/metadados intermediarios e alertas finais, facilitando auditoria, demo e testes de contrato.

**Alternatives considered**:

- SQLite/PostgreSQL/ORM: adiciona operacao e modelagem persistente sem necessidade nesta fase.
- Storage cloud: fora do escopo; tambem amplia requisitos de seguranca e credenciais.

## Decision: Contratos com Pydantic v2

**Rationale**: A feature tem regras fortes de entrada/saida: formatos permitidos, tamanho/duracao maxima, `patient_id` obrigatorio, scores em [0.0, 1.0] e enumeracoes de risco. Pydantic v2 permite validar esses invariantes e gerar JSON Schema para testes de contrato.

**Alternatives considered**:

- `dataclasses` sem validacao: simples, mas insuficiente para invariantes de contrato.
- Validacao manual em dicionarios: facil de duplicar e dificil de auditar.

## Decision: Formula de score por maximo com piso de termo critico

**Rationale**: A spec define `score_risco = max(score_acustico, score_textual_efetivo)` e `score_textual_efetivo = max(score_textual * confianca_transcricao, piso_termo_critico)`. O piso e `0.4` quando ha pelo menos um termo critico, garantindo `nivel_risco >= "moderado"` conforme SC-003; caso contrario, o piso e `0.0`.

**Alternatives considered**:

- Media ponderada: poderia reduzir um sinal clinico forte quando a outra fonte nao detecta risco.
- Soma normalizada: mais sensivel a falso positivo e exigiria calibracao adicional.

## Decision: Camada B minima com `pydub` e `librosa`

**Rationale**: A spec exige sinais acusticos para casos sem fala compreensivel. Nesta fase, o escopo minimo cobre RMS, intensidade/picos e pausas/silencio. Isso permite lidar com tosse/respiracao do Coswara sem entrar em MFCC completo, espectrogramas ou modelos treinados.

**Alternatives considered**:

- Apenas Camada A Azure: atenderia transcricao/texto, mas falharia em gravacoes de tosse/respiracao sem fala util.
- MFCC/espectrograma completo: tecnicamente rico, mas maior custo de implementacao e calibracao; adiado para pos-MVP.
- AudioSet: descartado para MVP por alto atrito de download/rotulagem e menor contexto clinico.

## Decision: Coswara + 2 a 3 WAV PT-BR locais para demo

**Rationale**: Coswara e adequado para tosse, respiracao e sinais respiratorios, com volume gerenciavel para 20 a 50 participantes. Como a demo da Camada A exige `pt-BR`, serao usadas 2 a 3 amostras WAV locais em portugues para validar Azure Speech e Text Analytics.

**Alternatives considered**:

- Apenas Coswara: fraco para demonstrar termos clinicos em portugues.
- AudioSet: dados genericos do YouTube, sem contexto clinico e com pipeline operacional mais pesado.
- Dataset real de consultas: risco maior de LGPD e consentimento; fora do escopo do MVP.

## Decision: Observabilidade com `logging` padrao e `structlog` opcional

**Rationale**: NFR-002 exige logs estruturados por etapa com duracao, status e `patient_id` anonimizado, sem conteudo clinico. `logging` atende o minimo sem dependencia extra; `structlog` pode ser habilitado posteriormente sem alterar o contrato funcional.

**Alternatives considered**:

- Prometheus/tracing distribuido: fora do escopo local e sem necessidade para single-recording.
- Logs livres com texto clinico: viola LGPD e os principios VII/VIII.

## Decision: Testes unitarios e de contrato com mocks Azure

**Rationale**: As regras de score, validacao de contrato e tratamento de entradas invalidas sao de alto risco para o alerta clinico. Mocks evitam custo, instabilidade e exposicao de credenciais em testes locais. Integracoes reais com Azure podem ser opcionais e isoladas por fixtures/VCR.

**Alternatives considered**:

- Testar somente com Azure real: fragil, lento e dependente de credenciais.
- Testes manuais de demo: insuficientes para as invariantes de score e contrato.
