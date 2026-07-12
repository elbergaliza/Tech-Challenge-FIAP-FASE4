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

1. **Given** uma gravação de voz em que o paciente relata "estou com muita falta de ar e dor no peito", **When** o sistema processa a gravação, **Then** o alerta gerado indica nível de risco "alto" (ou "moderado", conforme intensidade combinada dos sinais), com descrição citando os termos críticos encontrados e recomendação de encaminhamento clínico.
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
- O que acontece quando há sinais conflitantes (ex.: sinais acústicos indicam risco alto, mas nenhum termo crítico é encontrado no texto, ou vice-versa)? O sistema MUST combinar ambos os sinais em um único score, sem que a ausência de um sinal anule a presença de risco identificada pelo outro.
- O que acontece quando não há `patient_id`/identificador de amostra associado à gravação? O sistema MUST rejeitar o processamento antes de gerar qualquer alerta, já que este campo é obrigatório e não pode ser nulo.
- O que acontece quando múltiplos termos críticos diferentes são encontrados na mesma transcrição? O sistema MUST considerar a ocorrência combinada como fator de aumento do score de risco (mais termos críticos simultâneos → maior probabilidade de nível "alto").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST aceitar como entrada uma única gravação de voz de paciente (podendo conter fala, tosse e/ou respiração), associada a um identificador de paciente/amostra.
- **FR-002**: O sistema MUST produzir uma transcrição em texto do conteúdo falado presente na gravação, quando houver fala compreensível.
- **FR-003**: O sistema MUST associar à transcrição um indicador de confiança/qualidade (ex.: alta/baixa confiança), permitindo que etapas posteriores considerem o grau de certeza do texto obtido.
- **FR-004**: O sistema MUST extrair características acústicas do sinal de áudio (relacionadas a intensidade, pausas e padrão sonoro) e usá-las para identificar sinais de cansaço vocal, tosse alterada e/ou dificuldade respiratória.
- **FR-005**: O sistema MUST analisar o texto transcrito para identificar a presença de termos críticos pré-definidos associados a risco clínico (ex.: falta de ar, dor no peito, cansaço, tontura, piora, dificuldade para respirar).
- **FR-006**: O sistema MUST classificar o tom geral do texto transcrito (ex.: negativo/neutro/positivo) como sinal adicional de risco, considerando tom negativo como fator que aumenta a probabilidade de risco.
- **FR-007**: O sistema MUST combinar os sinais acústicos (FR-004) e os achados textuais (FR-005, FR-006) em um único score de risco numérico entre 0.0 e 1.0.
- **FR-008**: O sistema MUST classificar o score de risco combinado em um nível de risco categórico: "baixo" (score < 0.4), "moderado" (0.4 ≤ score < 0.7) ou "alto" (score ≥ 0.7).
- **FR-009**: O sistema MUST gerar uma descrição legível por humanos, resumindo os principais achados acústicos e textuais que fundamentaram o score.
- **FR-010**: O sistema MUST gerar uma recomendação de ação específica e acionável para a equipe médica, coerente com o nível de risco identificado.
- **FR-011**: O sistema MUST produzir, para cada gravação processada, exatamente um alerta padronizado contendo: identificador do paciente/amostra, identificação do módulo de origem (fixo, "audio_texto"), tipo de anomalia identificada (ou "nenhuma" quando não houver risco relevante), score de risco, nível de risco, descrição e recomendação.
- **FR-012**: O sistema MUST processar corretamente gravações sem fala compreensível (apenas tosse/respiração/silêncio), baseando o alerta somente nos sinais acústicos disponíveis, sem falhar por ausência de transcrição.
- **FR-013**: O sistema MUST processar corretamente casos em que os sinais acústicos não indiquem nenhuma anomalia, baseando o alerta somente nos achados textuais disponíveis.
- **FR-014**: O sistema MUST rejeitar entradas sem identificador de paciente/amostra, sem gerar alerta associado a uma entrada não identificável.
- **FR-015**: O sistema MUST rejeitar de forma explícita gravações corrompidas, vazias ou em formato não reconhecido, sem produzir um alerta com dados inválidos.
- **FR-016**: O sistema MUST tratar cada gravação de forma independente de outras modalidades do sistema (vídeo, dados clínicos), produzindo sua saída sem depender da disponibilidade dessas outras modalidades.
- **FR-017**: O sistema MUST preservar o texto transcrito original como parte dos dados rastreáveis do processamento, para fins de auditoria e revisão humana posterior.

### Key Entities

- **Gravação de Áudio**: representa a entrada do módulo — um arquivo de voz do paciente (podendo conter fala, tosse e/ou respiração), identificado por um `patient_id`/id de amostra.
- **Transcrição**: representa o texto derivado da fala contida na gravação, acompanhado de um indicador de confiança/qualidade; referencia a gravação de origem.
- **Sinais Acústicos**: conjunto de indicadores extraídos diretamente do sinal sonoro (intensidade, padrão de pausas, indícios de cansaço vocal, tosse alterada, dificuldade respiratória), independente do conteúdo verbal.
- **Achados Textuais**: termos críticos encontrados na transcrição e classificação de tom (negativo/neutro/positivo) associada ao texto.
- **Alerta Padronizado**: o entregável final do módulo — registro único combinando os Sinais Acústicos e os Achados Textuais, contendo `patient_id`, `modulo` (fixo "audio_texto"), `tipo_anomalia`, `score_risco` (0.0–1.0), `nivel_risco` (baixo/moderado/alto), `descricao` e `recomendacao`. É o registro consumido pela camada de fusão multimodal do sistema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das gravações processadas com sucesso resultam em exatamente um alerta com todos os sete campos obrigatórios preenchidos (nenhum campo nulo ou ausente).
- **SC-002**: 100% dos scores de risco gerados estão dentro do intervalo 0.0–1.0, e 100% das classificações de nível de risco são consistentes com as faixas definidas (baixo/moderado/alto) para o score correspondente.
- **SC-003**: 100% das gravações em que ao menos um termo crítico pré-definido é identificado no texto transcrito resultam em nível de risco igual ou superior a "moderado" (nenhum termo crítico é silenciosamente ignorado no score final).
- **SC-004**: 100% das gravações sem fala compreensível (apenas tosse/respiração/silêncio) ainda produzem um alerta válido, sem erro de processamento por ausência de transcrição.
- **SC-005**: 100% das gravações rejeitadas por identificador ausente, arquivo corrompido ou formato não suportado são identificadas explicitamente como entrada inválida, sem gerar um alerta com dados incompletos ou inconsistentes.
- **SC-006**: Em revisão por amostragem de um conjunto de gravações sem queixas relevantes e sem sinais acústicos de risco, ao menos 90% são classificadas como nível de risco "baixo" com `tipo_anomalia` "nenhuma" (baixa taxa de falso alarme).

## Assumptions

- O idioma padrão das gravações e das transcrições é o português falado no Brasil; suporte a outros idiomas está fora do escopo desta versão.
- Cada invocação do pipeline processa uma única gravação de um único paciente por vez; processamento em lote/streaming em tempo real está fora do escopo desta versão (pode ser adicionado depois sem alterar o contrato de saída).
- A identificação de múltiplos falantes (diarização) na mesma gravação está fora do escopo; assume-se que a gravação contém primariamente a voz do paciente.
- A lista de termos críticos é pré-definida e mantida como configuração conhecida do sistema (ex.: falta de ar, dor no peito, cansaço, tontura, piora, dificuldade para respirar); expansão dessa lista é considerada evolução incremental, não uma mudança de contrato.
- Detecção de negação linguística (ex.: "não sinto falta de ar") não é tratada nesta versão; termos críticos são considerados presentes por ocorrência léxica, mesmo em contexto de negação. Esta limitação MUST ser registrada na descrição do alerta como debito técnico conhecido, não como bloqueio de entrega.
- Os limiares de classificação de nível de risco (baixo < 0.4, moderado 0.4–0.7, alto ≥ 0.7) são adotados como padrão inicial de negócio e podem ser recalibrados em versões futuras sem alterar o contrato de saída (mesmos nomes de campo e faixa de score).
- Gravações de voz de pacientes são tratadas como dado sensível de saúde; este módulo não define aqui os mecanismos de anonimização/consentimento/controle de acesso, que são tratados como requisito transversal do sistema (fora do escopo desta spec, mas de observância obrigatória na implementação).
- A saída deste módulo é consumida por uma camada de fusão multimodal fora do escopo desta spec; este módulo é responsável apenas por produzir o alerta padronizado, não por combiná-lo com os alertas de vídeo ou de dados clínicos.
