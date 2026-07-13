# Feature Specification: Pipeline de Áudio — Alerta Padronizado (módulo `audio_texto`)

**Feature Branch**: `001-audio-texto-pipeline`

**Created**: 2026-07-12

**Status**: Draft

**Input**: User description: "Criar a spec do pipeline de áudio (módulo audio_texto), consolidando os requisitos: 003-egaliza-audio-transcricao, 004-egaliza-audio-analise-texto, 002-egaliza-audio-features, 005-egaliza-audio-alerta. O entregável final é um alerta JSON padronizado do módulo áudio. Foco no 'o que' e 'por quê'; sem decidir tecnologias nesta fase."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar alerta padronizado a partir de uma gravação de voz do paciente (Priority: P1)

A equipe médica recebe uma gravação de voz de um paciente (consulta, checagem remota ou registro de sintomas). O sistema processa essa gravação de ponta a ponta e devolve um único alerta padronizado indicando se há sinais de risco respiratório/vocal, com um score de risco, um nível de risco e uma recomendação de ação — sem que ninguém precise ouvir o áudio bruto ou ler a transcrição completa para decidir o próximo passo.

**Why this priority**: É o entregável final do módulo de áudio e a única fatia que, isolada, já gera valor clínico direto: um alerta acionável. Todas as demais capacidades (transcrição, extração de sinais acústicos, detecção de termos críticos) existem para alimentar este resultado.

**Independent Test**: Pode ser testado fornecendo uma gravação de áudio de exemplo (com e sem sinais de risco) e verificando que o sistema retorna exatamente um registro de alerta com todos os campos obrigatórios preenchidos e coerentes com o conteúdo do áudio.

**Acceptance Scenarios**:

1. **Given** uma gravação de voz em que o paciente relata "estou com muita falta de ar e dor no peito", **When** o sistema processa a gravação, **Then** o alerta gerado indica nível de risco **"alto"** (dois termos críticos de alta severidade → `score_textual_efetivo ≥ 0.7` pelo piso mínimo de FR-003, podendo ser maior dependendo da confiança e de sinais acústicos combinados), com descrição citando os termos críticos encontrados e recomendação de encaminhamento clínico.
2. **Given** uma gravação de voz sem queixas relevantes e sem sinais acústicos de cansaço/dificuldade respiratória, **When** o sistema processa a gravação, **Then** o alerta gerado indica nível de risco "baixo", tipo de anomalia "nenhuma" e recomendação de rotina (sem encaminhamento urgente).
3. **Given** uma gravação em que a fala contém sinais acústicos de cansaço vocal, mas o conteúdo verbal não menciona termos críticos, **When** o sistema processa a gravação, **Then** o alerta reflete o risco identificado pelos sinais acústicos, mesmo sem termos críticos no texto.

---

### User Story 2 - Obter transcrição confiável da fala do paciente (Priority: P2)

A equipe clínica e as demais etapas do pipeline precisam de uma versão em texto do que o paciente falou, junto com uma indicação de quão confiável é essa transcrição, para permitir auditoria, revisão humana e como insumo para a análise de termos críticos.

**Why this priority**: É pré-requisito funcional do alerta final (User Story 1), mas também tem valor isolado: permite auditoria/rastreabilidade humana da gravação sem depender da geração do alerta.

**Independent Test**: Pode ser testado fornecendo uma gravação de áudio e verificando que o sistema retorna o texto transcrito acompanhado de um indicador de confiança/qualidade, mesmo sem prosseguir para as etapas de análise de termos ou geração de alerta.

**Acceptance Scenarios**:

1. **Given** uma gravação de voz clara e em volume adequado, **When** o sistema transcreve a gravação, **Then** o texto retornado corresponde ao conteúdo falado e vem acompanhado de um indicador de alta confiança.
2. **Given** uma gravação com fala pouco clara, ruído de fundo ou hesitações longas, **When** o sistema transcreve a gravação, **Then** o texto retornado vem acompanhado de um indicador de baixa confiança, permitindo que etapas seguintes considerem essa incerteza em vez de tratá-la como certeza absoluta.

---

### User Story 3 - Extrair sinais acústicos de cansaço vocal e dificuldade respiratória (Priority: P3)

Mesmo quando a fala não é clara, é curta demais para transcrição confiável, ou a gravação contém principalmente tosse/respiração (sem conteúdo verbal), o sistema precisa identificar diretamente no sinal sonoro indícios de cansaço vocal, tosse alterada ou dificuldade respiratória.

**Why this priority**: Cobre casos em que o conteúdo semântico (texto) é insuficiente ou inexistente, mas o padrão sonoro ainda contém informação clinicamente relevante (ex.: tosse, respiração ofegante). Sem esta capacidade, gravações sem fala útil não gerariam nenhum sinal de risco.

**Independent Test**: Pode ser testado fornecendo uma gravação contendo apenas tosse/respiração (sem fala compreensível) e verificando que o sistema ainda produz indicadores acústicos (ex.: intensidade, padrão de pausas, sinal de tosse/respiração alterada), independentemente do resultado da transcrição.

**Acceptance Scenarios**:

1. **Given** uma gravação contendo episódios de tosse com padrão diferente do esperado, **When** o sistema analisa o sinal de áudio, **Then** ele identifica e sinaliza a tosse como potencialmente alterada, mesmo sem transcrição de fala.
2. **Given** uma gravação de fala com pausas longas e frequentes e baixa intensidade sustentada, **When** o sistema analisa o sinal de áudio, **Then** ele sinaliza um indício de cansaço vocal/dificuldade respiratória com base nesses padrões.

---

### User Story 4 - Identificar termos críticos e tom de risco no texto transcrito (Priority: P4)

A partir de um texto já transcrito (desta gravação ou de uma fonte de texto já transcrita anteriormente), o sistema precisa identificar a presença de termos associados a risco clínico (ex.: falta de ar, dor no peito, cansaço, tontura, piora, dificuldade para respirar) e o tom geral (positivo/negativo/neutro) do relato.

**Why this priority**: É a capacidade de menor prioridade isolada porque seu valor pleno só se realiza quando combinada ao alerta final (User Story 1); ainda assim, é testável de forma independente e reutilizável para textos já transcritos por outras fontes.

**Independent Test**: Pode ser testado fornecendo um texto já transcrito (sem precisar rodar a transcrição de áudio) e verificando que o sistema retorna a lista de termos críticos encontrados e a classificação de tom associada.

**Acceptance Scenarios**:

1. **Given** um texto contendo a frase "sinto muita dificuldade para respirar desde ontem", **When** o sistema analisa o texto, **Then** ele identifica ao menos o termo crítico correspondente a dificuldade respiratória e classifica o tom como predominantemente negativo.
2. **Given** um texto neutro sem menção a sintomas ("hoje me sinto bem, sem queixas"), **When** o sistema analisa o texto, **Then** ele não identifica termos críticos e classifica o tom como neutro/positivo.

---

### Edge Cases

- O que acontece quando a gravação não contém fala compreensível (apenas silêncio, ruído ou tosse/respiração isolada)? O sistema MUST ainda produzir um alerta, baseado apenas nos sinais acústicos disponíveis, sem falhar por ausência de texto transcrito.
- O que acontece quando a transcrição tem confiança muito baixa? O sistema MUST refletir essa incerteza na descrição/recomendação do alerta, em vez de tratar o texto transcrito como certeza absoluta para o cálculo do score.
- O que acontece quando o arquivo de áudio está corrompido, vazio ou em formato não suportado? O sistema MUST rejeitar a entrada de forma explícita e identificável, sem gerar um alerta com dados inválidos ou incompletos.
- O que acontece quando um termo crítico aparece de forma negada (ex.: "não sinto falta de ar")? Ver Assunções — tratamento de negação é explicitamente fora do escopo desta versão.
- O que acontece quando há sinais conflitantes (ex.: sinais acústicos indicam risco alto, mas nenhum termo crítico é encontrado no texto, ou vice-versa)? O sistema MUST combinar ambos os sinais em um único score, sem que a ausência de um sinal anule a presença de risco identificada pelo outro. Em caso de conflito extremo (ex.: `score_acústico = 0.9`, `score_textual_efetivo = 0.0`), o resultado é determinístico: `score_risco = max(0.9, 0.0) = 0.9` → `nivel_risco = "alto"`, e a descrição do alerta MUST citar explicitamente qual fonte sustentou o score (ex.: "risco identificado por sinais acústicos; conteúdo verbal não apresentou termos críticos").
- O que acontece quando ambos `score_acústico = 0.0` e `score_textual_efetivo = 0.0`? O resultado é `score_risco = 0.0` → `nivel_risco = "baixo"` e `tipo_anomalia = "nenhuma"`. Este é o único caso em que `tipo_anomalia` MUST ser "nenhuma", e a recomendação MUST ser de rotina (sem encaminhamento urgente), consistente com SC-006.
- O que acontece quando não há `patient_id`/identificador de amostra associado à gravação? O sistema MUST rejeitar o processamento antes de gerar qualquer alerta, já que este campo é obrigatório e não pode ser nulo.
- O que acontece quando múltiplos termos críticos diferentes são encontrados na mesma transcrição? O sistema MUST considerar a ocorrência combinada como fator de aumento do score de risco (mais termos críticos simultâneos → maior probabilidade de nível "alto").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST aceitar como entrada uma única gravação de voz de paciente (podendo conter fala, tosse e/ou respiração), associada a um identificador de paciente/amostra. Os formatos suportados são WAV e MP3; a gravação MUST ter duração máxima de 10 minutos e tamanho máximo de 50 MB.
- **FR-002**: O sistema MUST produzir uma transcrição em texto do conteúdo falado presente na gravação, quando houver fala compreensível.
- **FR-003**: O sistema MUST associar à transcrição um indicador de confiança numérico entre 0.0 e 1.0, representando a qualidade/certeza do texto obtido. Este valor MUST ser usado para ponderar o score textual antes da combinação usando a fórmula com piso: `score_textual_efetivo = max(score_textual × confiança_transcrição, piso_termo_crítico)`, onde `piso_termo_crítico = 0.4` quando ao menos um termo crítico pré-definido for identificado na transcrição (FR-005), e `piso_termo_crítico = 0.0` caso contrário. **Invariante de normalização**: tanto `score_textual` quanto `confiança_transcrição` MUST estar no intervalo [0.0, 1.0] antes da operação, garantindo que `score_textual_efetivo ∈ [0.0, 1.0]` em todos os casos. Esta regra garante simultaneamente dois objetivos: (1) transcrições de baixa confiança sem termos críticos não inflam artificialmente o risco; (2) a detecção de qualquer termo crítico sempre resulta em `nivel_risco ≥ "moderado"`, preservando SC-003 independentemente do valor de `confiança_transcrição`.
- **FR-004**: O sistema MUST extrair características acústicas do sinal de áudio (relacionadas a intensidade, pausas e padrão sonoro) e usá-las para identificar sinais de cansaço vocal, tosse alterada e/ou dificuldade respiratória. O resultado MUST ser expresso como `score_acústico`, um valor numérico no intervalo [0.0, 1.0], com `score_acústico = 0.0` quando nenhum sinal acústico de risco for detectado, e `score_acústico > 0.0` proporcional à severidade dos sinais identificados. O método de mapeamento das características ao score é decisão de implementação, a ser definida em `/speckit-plan`.
- **FR-005**: O sistema MUST analisar o texto transcrito para identificar a presença de termos críticos pré-definidos associados a risco clínico (ex.: falta de ar, dor no peito, cansaço, tontura, piora, dificuldade para respirar). O resultado parcial desta análise combinado com FR-006 MUST ser expresso como `score_textual`, um valor numérico no intervalo [0.0, 1.0], com `score_textual = 0.0` quando nenhum termo crítico for encontrado e o tom for neutro/positivo, e `score_textual > 0.0` crescente com o número de termos críticos distintos identificados e o grau de negatividade do tom. O método de mapeamento é decisão de implementação, a ser definida em `/speckit-plan`.
- **FR-006**: O sistema MUST classificar o tom geral do texto transcrito (ex.: negativo/neutro/positivo) como sinal adicional de risco, considerando tom negativo como fator que aumenta a probabilidade de risco.
- **FR-007**: O sistema MUST combinar os sinais acústicos (FR-004) e os achados textuais (FR-005, FR-006) em um único score de risco numérico entre 0.0 e 1.0, adotando a regra de máximo: `score_risco = max(score_acústico, score_textual_efetivo)`, onde `score_textual_efetivo` é calculado conforme FR-003 (com piso para termos críticos). Nenhuma fonte pode suprimir o risco identificado pela outra; a ausência de sinal de uma fonte não reduz o score produzido pela outra.
- **FR-008**: O sistema MUST classificar o score de risco combinado em um nível de risco categórico: "baixo" (score < 0.4), "moderado" (0.4 ≤ score < 0.7) ou "alto" (score ≥ 0.7).
- **FR-009**: O sistema MUST gerar uma descrição legível por humanos, resumindo os principais achados acústicos e textuais que fundamentaram o score.
- **FR-010**: O sistema MUST gerar uma recomendação de ação específica e acionável para a equipe médica, coerente com o nível de risco identificado.
- **FR-011**: O sistema MUST produzir, para cada gravação processada, exatamente um alerta padronizado contendo: identificador do paciente/amostra, identificação do módulo de origem (fixo, "audio_texto"), tipo de anomalia identificada (ou "nenhuma" quando não houver risco relevante), score de risco, nível de risco, descrição e recomendação.
- **FR-012**: O sistema MUST processar corretamente gravações sem fala compreensível (apenas tosse/respiração/silêncio), baseando o alerta somente nos sinais acústicos disponíveis, sem falhar por ausência de transcrição.
- **FR-013**: O sistema MUST processar corretamente casos em que os sinais acústicos não indiquem nenhuma anomalia, baseando o alerta somente nos achados textuais disponíveis.
- **FR-014**: O sistema MUST rejeitar entradas sem identificador de paciente/amostra, sem gerar alerta associado a uma entrada não identificável.
- **FR-015**: O sistema MUST rejeitar de forma explícita gravações corrompidas, vazias, em formato não reconhecido (qualquer formato diferente de WAV ou MP3), com duração superior a 10 minutos ou com tamanho superior a 50 MB, sem produzir um alerta com dados inválidos.
- **FR-016**: O sistema MUST tratar cada gravação de forma independente de outras modalidades do sistema (vídeo, dados clínicos), produzindo sua saída sem depender da disponibilidade dessas outras modalidades.
- **FR-017**: O sistema MUST preservar o texto transcrito original como parte dos dados rastreáveis do processamento, para fins de auditoria e revisão humana posterior.

### Key Entities

- **Gravação de Áudio**: representa a entrada do módulo — um arquivo de voz do paciente (podendo conter fala, tosse e/ou respiração), identificado por um `patient_id`/id de amostra.
- **Transcrição**: representa o texto derivado da fala contida na gravação, acompanhado de um indicador de confiança/qualidade; referencia a gravação de origem.
- **Sinais Acústicos**: conjunto de indicadores extraídos diretamente do sinal sonoro (intensidade, padrão de pausas, indícios de cansaço vocal, tosse alterada, dificuldade respiratória), independente do conteúdo verbal.
- **Achados Textuais**: termos críticos encontrados na transcrição e classificação de tom (negativo/neutro/positivo) associada ao texto.
- **Alerta Padronizado**: o entregável final do módulo — registro único combinando os Sinais Acústicos e os Achados Textuais, contendo `patient_id`, `modulo` (fixo "audio_texto"), `tipo_anomalia`, `score_risco` (0.0–1.0), `nivel_risco` (baixo/moderado/alto), `descricao` e `recomendacao`. É o registro consumido pela camada de fusão multimodal do sistema.

## Success Criteria *(mandatory)*

### Non-Functional Requirements

- **NFR-001**: O pipeline MUST concluir o processamento completo de uma gravação (do recebimento do arquivo à entrega do alerta) em no máximo **60 segundos** por padrão. Este limite MUST ser parametrizável via configuração, sem alteração de código, para acomodar diferentes ambientes de execução (ex.: modelos de transcrição mais pesados em GPU vs. CPU).
- **NFR-002**: O módulo MUST emitir logs estruturados por etapa do pipeline, registrando: início e fim de cada etapa, duração em milissegundos, `patient_id` (anonimizado ou referência, nunca conteúdo clínico) e status (sucesso/falha). O conteúdo do áudio, da transcrição e dos termos críticos encontrados MUST NOT ser incluído nos logs. As métricas mínimas obrigatórias são: latência total por invocação, taxa de rejeições de entrada e score de risco gerado.

### Measurable Outcomes

- **SC-001**: 100% das gravações processadas com sucesso resultam em exatamente um alerta com todos os sete campos obrigatórios preenchidos (nenhum campo nulo ou ausente).
- **SC-002**: 100% dos scores de risco gerados estão dentro do intervalo 0.0–1.0, e 100% das classificações de nível de risco são consistentes com as faixas definidas (baixo/moderado/alto) para o score correspondente.
- **SC-003**: 100% das gravações em que ao menos um termo crítico pré-definido é identificado no texto transcrito resultam em nível de risco igual ou superior a "moderado" (nenhum termo crítico é silenciosamente ignorado no score final).
- **SC-004**: 100% das gravações sem fala compreensível (apenas tosse/respiração/silêncio) ainda produzem um alerta válido, sem erro de processamento por ausência de transcrição.
- **SC-005**: 100% das gravações rejeitadas por identificador ausente, arquivo corrompido ou formato não suportado são identificadas explicitamente como entrada inválida, sem gerar um alerta com dados incompletos ou inconsistentes.
- **SC-006**: Em revisão por amostragem de um conjunto de gravações sem queixas relevantes e sem sinais acústicos de risco, ao menos 90% são classificadas como nível de risco "baixo" com `tipo_anomalia` "nenhuma" (baixa taxa de falso alarme).
- **SC-007**: 100% das gravações processadas com sucesso têm seu alerta gerado dentro do limite de latência configurado (padrão: 60 segundos); ultrapassar esse limite MUST ser registrado como falha de performance observável.

## Clarifications

### Session 2026-07-12

- Q: Como os sinais acústicos e os achados textuais devem ser combinados para produzir o score de risco único (FR-007)? → A: Regra de máximo — `score_risco = max(score_acústico, score_textual_efetivo)`, onde `score_textual_efetivo = max(score_textual × confiança_transcrição, piso_termo_crítico)` conforme FR-003
- Q: Quais formatos de arquivo de áudio e restrições de entrada devem ser suportados (FR-001 / FR-015)? → A: WAV e MP3; duração máxima 10 min; tamanho máximo 50 MB
- Q: Como o indicador de confiança da transcrição deve ser representado e como afeta o score de risco (FR-003 / FR-007)? → A: Numérico contínuo 0.0–1.0; `score_textual_efetivo = score_textual × confiança` antes do `max()`
- Q: Qual é a latência máxima aceitável para o processamento completo de uma gravação? → A: 60 segundos por padrão, valor parametrizável
- Q: Quais sinais de observabilidade o módulo deve emitir durante o processamento? → A: Log estruturado por etapa (duração + patient_id + status); métricas de latência, rejeição e score — sem logar conteúdo de áudio ou transcrição

### Session 2026-07-12 (checklist score-formula — resolução de conflitos)

- Q: Como garantir que SC-003 ("ao menos um termo crítico → `nivel_risco ≥ moderado`") não seja violado pela fórmula de ponderação por confiança de FR-003? → A: Regra de piso em FR-003 — `score_textual_efetivo = max(score_textual × confiança_transcrição, 0.4)` quando `termos_críticos ≥ 1`; `piso_termo_crítico = 0.0` caso contrário. O piso 0.4 é o limiar mínimo de "moderado" (FR-008), garantindo SC-003 independentemente da confiança da transcrição.
- Q: Qual é a faixa de valores e as invariantes de `score_acústico` (FR-004)? → A: Numérico [0.0, 1.0]; `score_acústico = 0.0` quando sem sinal de risco acústico; `score_acústico > 0.0` proporcional à severidade. Mapeamento detalhado definido em `/speckit-plan`.
- Q: Qual é a faixa de valores e as invariantes de `score_textual` (FR-005)? → A: Numérico [0.0, 1.0]; `score_textual = 0.0` sem termos críticos e tom neutro/positivo; `score_textual > 0.0` crescente com número de termos e grau de negatividade. Mapeamento detalhado definido em `/speckit-plan`.

### Session 2026-07-12 (preparação `/speckit.plan` — decisões técnicas)

Decisões registradas em [decisions.md](./decisions.md); argumento compacto em [plan-argument.md](./plan-argument.md).

- Q: Qual dataset de áudio usar (Coswara vs AudioSet)? → A: **Coswara** como base principal (subconjunto 20–50 participantes); AudioSet descartado no MVP.
- Q: Como demonstrar Azure Speech + Text Analytics em `pt-BR` se Coswara é predominantemente inglês? → A: **2–3 gravações WAV locais em português** em `data/raw/pt-br/` para demo da Camada A.
- Q: Camada B (análise acústica direta) entra nesta fase? → A: **Sim, escopo mínimo** — heurísticas com `pydub`/`librosa` (intensidade, pausas, RMS) sobre clips Coswara; MFCC/espectrograma completo adiado pós-MVP. Camada A Azure permanece obrigatória e prioritária.
- Q: Stack de qualidade e validação (lacunas do plano macro)? → A: `pytest` + mocks Azure, `ruff`, `pyright`, validação de contratos com **Pydantic v2**; CLI com **Typer**; logging estruturado por etapa (NFR-002).

## Assumptions

- O idioma padrão das gravações e das transcrições é o português falado no Brasil; suporte a outros idiomas está fora do escopo desta versão.
- Cada invocação do pipeline processa uma única gravação de um único paciente por vez; processamento em lote/streaming em tempo real está fora do escopo desta versão (pode ser adicionado depois sem alterar o contrato de saída).
- A identificação de múltiplos falantes (diarização) na mesma gravação está fora do escopo; assume-se que a gravação contém primariamente a voz do paciente.
- A lista de termos críticos é pré-definida e mantida como configuração conhecida do sistema (ex.: falta de ar, dor no peito, cansaço, tontura, piora, dificuldade para respirar); expansão dessa lista é considerada evolução incremental, não uma mudança de contrato.
- Detecção de negação linguística (ex.: "não sinto falta de ar") não é tratada nesta versão; termos críticos são considerados presentes por ocorrência léxica, mesmo em contexto de negação. Esta limitação MUST ser registrada na descrição do alerta como debito técnico conhecido, não como bloqueio de entrega.
- Os limiares de classificação de nível de risco (baixo < 0.4, moderado 0.4–0.7, alto ≥ 0.7) são adotados como padrão inicial de negócio e podem ser recalibrados em versões futuras sem alterar o contrato de saída (mesmos nomes de campo e faixa de score). Os valores de fronteira são: `score = 0.4` → "moderado" (piso inclusivo), `score = 0.7` → "alto" (piso inclusivo).
- `confiança_transcrição` é esperada no intervalo [0.0, 1.0] conforme entregue pelo serviço de transcrição. Caso o serviço retorne confiança em escala diferente (ex.: 0–100), a normalização para [0.0, 1.0] MUST ser aplicada na camada de integração antes de chegar à fórmula de FR-003. Esta normalização é responsabilidade do adaptador do serviço de transcrição, a ser definida em `/speckit-plan`.
- Gravações de voz de pacientes são tratadas como dado sensível de saúde; este módulo não define aqui os mecanismos de anonimização/consentimento/controle de acesso, que são tratados como requisito transversal do sistema (fora do escopo desta spec, mas de observância obrigatória na implementação).
- A saída deste módulo é consumida por uma camada de fusão multimodal fora do escopo desta spec; este módulo é responsável apenas por produzir o alerta padronizado, não por combiná-lo com os alertas de vídeo ou de dados clínicos.
