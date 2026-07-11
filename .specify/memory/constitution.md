<!--
SYNC IMPACT REPORT
==================
Version change: (template placeholder) → 1.0.0
Operation: First ratification — all placeholders replaced

Principles added (10):
  I.   Simplicidade e Clareza sobre Generalidade
  II.  Papel da IA como Pair Programmer Assistente
  III. Arquitetura Modular com Responsabilidades Claras
  IV.  Qualidade de Código Python (PEP 8, ruff, pytest, mypy/pyright)
  V.   Testes Proporcionais ao Risco de Negócio
  VI.  Specs como Fonte de Verdade antes da Implementação
  VII. Segurança e Privacidade de Dados Clínicos (LGPD)
  VIII.Credenciais Nunca em Código, Logs ou Documentação
  IX.  Evolução Incremental — Sem Reescritas Amplas sem Pedido Explícito
  X.   Documentação Útil e Próxima do Código

Sections added:
  - Core Principles (I–X)
  - Segurança e Conformidade
  - Fluxo de Trabalho com IA
  - Governance (amendment procedure + versioning policy + compliance review)

Templates reviewed:
  - .specify/templates/plan-template.md   ✅ Constitution Check updated with project-specific gates
  - .specify/templates/spec-template.md   ✅ no mandatory updates required
  - .specify/templates/tasks-template.md  ✅ no mandatory updates required
  - .specify/templates/commands/          ✅ no command files present; skipped silently

Follow-up TODOs: none
Source input: docs/spec/constitution-input.md (used as initial reference only;
              this file is now the sole source of truth)
-->

# Tech Challenge FIAP Fase 4 — Sistema Multimodal de Monitoramento Clínico Constitution

## Core Principles

### I. Simplicidade e Clareza sobre Generalidade

O código e as especificações MUST otimizar para clareza e entendimento, não para cobertura
genérica de casos hipotéticos. Soluções óbvias e padrão do ecossistema MUST ser preferidas.
Abstrações prematuras e over-engineering MUST ser evitados.

**Rationale**: Um sistema clínico precisa ser auditável e mantível por qualquer membro da
equipe. Complexidade desnecessária aumenta o risco de erros em contexto de saúde e dificulta
revisão por pares.

---

### II. Papel da IA como Pair Programmer Assistente

A IA MUST atuar como pair programmer sênior assistente, alinhada à constituição e às specs
existentes. A IA MUST propor opções quando houver ambiguidade e explicitar trade-offs
(complexidade, custo, DX). A IA MUST NOT reescrever módulos inteiros nem introduzir mudanças
estruturais amplas sem pedido explícito.

**Rationale**: A autoridade de design e decisão arquitetural pertence aos desenvolvedores
humanos do projeto. A IA é um acelerador, não um substituto de julgamento técnico.

---

### III. Arquitetura Modular com Responsabilidades Claras

Cada módulo (`audio_pipeline`, `video_pipeline`, `text_pipeline`, `anomaly`, `alerts`,
`fusion`) MUST ter responsabilidade única e dependências explícitas. Acoplamento entre
módulos MUST ser minimizado. Novos componentes MUST nascer como módulos independentes e
testáveis antes de serem acoplados a APIs ou integrações.

**Rationale**: A natureza multimodal do sistema exige que cada pipeline possa ser
desenvolvido, testado e entregue de forma independente, sem bloquear os demais membros
da equipe.

---

### IV. Qualidade de Código Python (PEP 8, ruff, pytest, mypy/pyright)

Todo código Python MUST seguir PEP 8 e ser idiomático, legível e simples. Lint com `ruff`,
testes com `pytest` e verificação de tipos com `mypy` ou `pyright` MUST passar antes de
qualquer entrega. Type hints MUST ser usados nas interfaces públicas e no domínio principal.

**Rationale**: Ferramentas automatizadas de qualidade reduzem defeitos silenciosos e
garantem que o código permaneça revisável por qualquer membro do grupo ao longo do prazo
do desafio.

---

### V. Testes Proporcionais ao Risco de Negócio

Todo código novo MUST vir acompanhado de testes automatizados proporcionais ao risco. Toda
nova regra de negócio MUST ter no mínimo um teste unitário cobrindo o comportamento esperado.
Bugs corrigidos MUST ganhar um teste de regressão. A implementação MUST NOT ser considerada
concluída enquanto os testes relevantes não estiverem passando.

**Rationale**: Em um sistema de alerta clínico, falsos negativos (anomalia não detectada)
ou falsos positivos excessivos têm consequências diretas sobre a segurança do paciente.
Testes são a primeira linha de defesa.

---

### VI. Specs como Fonte de Verdade antes da Implementação

Arquivos de spec MUST ser criados ou atualizados antes de mudanças relevantes. A
implementação MUST seguir a spec de forma explícita e verificável. Quando uma spec estiver
vaga ou incompleta, MUST-se pedir esclarecimento antes de codar. Specs MUST cobrir
contexto, objetivo, regras de negócio, interfaces, critérios de aceitação e riscos.

**Rationale**: Minimizar retrabalho é crítico dado o prazo fixo do Tech Challenge. Specs
escritas antes evitam divergências de entendimento sobre contratos de interface entre
membros da equipe (ex.: schema JSON de saída de cada módulo).

---

### VII. Segurança e Privacidade de Dados Clínicos (LGPD)

Dados de voz, vídeo e sinais vitais de pacientes MUST ser tratados como dados sensíveis
conforme a LGPD. O sistema MUST NOT processar ou transmitir dados pessoais de saúde sem
consentimento explícito documentado. Anonimização MUST ser aplicada antes de qualquer
processamento em serviços externos. Acesso aos dados MUST ser restrito às funções
estritamente necessárias.

**Rationale**: Dados de saúde são categoria especial de dados sensíveis sob a LGPD
(Art. 11). O uso de serviços de nuvem (Azure, AWS) para processar áudio e documentos
clínicos exige conformidade explícita, inclusive na fase de desenvolvimento e demo.

---

### VIII. Credenciais Nunca em Código, Logs ou Documentação

Credenciais, chaves de API, tokens e segredos (ex.: `AZURE_SPEECH_KEY`,
`AZURE_TEXT_ANALYTICS_KEY`, `AWS_SECRET_ACCESS_KEY`) MUST NOT aparecer em código-fonte,
logs, relatórios técnicos, README ou documentação pública. MUST ser carregadas
exclusivamente via variáveis de ambiente ou arquivos `.env` não versionados. O arquivo
`.env` MUST estar listado no `.gitignore`.

**Rationale**: Exposição de credenciais em repositórios públicos resulta em comprometimento
imediato dos serviços e potencial uso indevido de dados de pacientes. O risco é
irreversível e de alto impacto.

---

### IX. Evolução Incremental — Sem Reescritas Amplas sem Pedido Explícito

O sistema MUST ser construído e evoluído em entregas pequenas, frequentes e testáveis
(F0 → F6 conforme plano). A IA e os desenvolvedores MUST NOT substituir módulos funcionais
por reescritas amplas sem pedido explícito. SHOULD-se preferir extensões plugáveis
(ex.: Camada B de análise acústica) em vez de alterar o pipeline principal.

**Rationale**: Reescritas amplas em projetos com prazo fixo introduzem regressões e
consomem tempo que deveria ser investido nas etapas seguintes. A abordagem incremental
protege o que já funciona.

---

### X. Documentação Útil e Próxima do Código

Documentação MUST ser curta, útil e mantida próxima do código (docstrings, comentários de
intenção, README por módulo). Comentários MUST explicar por que uma decisão existe, MUST NOT
descrever o óbvio. Quando houver inconsistência entre código, spec e documentação, isso MUST
ser tratado como débito técnico a corrigir imediatamente.

**Rationale**: Em um projeto acadêmico com múltiplos colaboradores e prazo fixo, documentação
desatualizada é tão prejudicial quanto ausência de documentação. A entrega final inclui
relatório técnico e vídeo demonstrativo — documentação precisa ser confiável.

---

## Segurança e Conformidade

Credenciais e dados sensíveis obedecem rigorosamente aos Princípios VII e VIII. Qualquer
módulo que interaja com serviços externos (Azure, AWS) MUST ter revisão de segurança antes
de integração ao branch principal. Anonimização de dados clínicos não é opcional: é
pré-requisito de merge para os módulos `audio_pipeline`, `video_pipeline` e `text_pipeline`.

## Fluxo de Trabalho com IA

Toda interação entre desenvolvedor e IA MUST respeitar o Princípio II. A IA MUST sempre
citar qual spec, princípio ou decisão registrada fundamenta uma proposta antes de
implementar. Quando não houver spec, a IA MUST recomendar criá-la antes de prosseguir com
a implementação.

## Governance

### Procedimento de Emenda

Qualquer membro da equipe PODE propor uma emenda à constituição abrindo uma discussão no
repositório (issue ou PR dedicado). A aprovação requer consenso explícito de todos os
membros ativos do projeto. Emendas que alterem princípios de segurança (VII, VIII) ou
arquitetura (III) DEVEM ser revisadas com atenção redobrada e justificativa de risco
documentada.

### Política de Versionamento (semver)

| Tipo de mudança                                           | Incremento |
|-----------------------------------------------------------|-----------|
| Novo princípio ou remoção de princípio existente          | MAJOR     |
| Alteração de regra (MUST/SHOULD) em princípio existente   | MINOR     |
| Correção de redação, formatação ou metadados              | PATCH     |

### Frequência de Revisão de Conformidade

A constituição DEVE ser revisada ao final de cada fase de implementação (F0–F6). Qualquer
spec, plano ou tarefa que entre em conflito com a constituição DEVE ser ajustado antes de
prosseguir para implementação. A versão vigente da constituição é a registrada em
`.specify/memory/constitution.md` no branch principal.

---

**Version**: 1.0.0 | **Ratified**: 2026-07-11 | **Last Amended**: 2026-07-11
