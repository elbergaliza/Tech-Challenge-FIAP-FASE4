# Fusão Multimodal — Specification

**Feature**: `fusao-multimodal`
**Status**: Approved
**Design doc**: `.specs/features/fusao-multimodal/design.md`
**Brainstorm doc**: `docs/superpowers/specs/2026-07-18-multimodal-fusion-design.md`

---

## Problem Statement

Os módulos clínico e de vídeo do Tech Challenge FIAP Fase 4 rodam de forma independente e geram alertas em schemas ligeiramente diferentes. Não existe hoje um ponto único de integração que execute os módulos, consolide os resultados e gere um relatório multimodal final. O `src/fusion.py` existente é um rascunho incompleto (média simples, `case_id` hardcoded, não executa os módulos).

---

## Goals

- [x] Módulo clínico e de vídeo executam a partir de um único `python main.py`
- [x] Relatório consolidado com score médio, nível mais crítico e lista de alertas individuais
- [x] Arquitetura extensível: adicionar módulo de áudio = criar um adaptador, zero mudança no core
- [x] CI GitHub Actions valida que a pipeline não quebra (dados reais leves)

---

## Out of Scope

| Feature | Razão |
|---------|-------|
| Módulo de áudio | WIP em branch separada — integração posterior |
| Interface web / dashboard | Fora do escopo acadêmico |
| Banco de dados | Saída apenas em JSON |
| Streaming / tempo real | Processamento em lote suficiente para o protótipo |
| Validação clínica profissional | Projeto acadêmico demonstrativo |
| Paralelo entre módulos por padrão | CPU local; sequencial é mais seguro e suficiente |

---

## User Stories

### P1: Execução end-to-end com um comando ⭐ MVP

**User Story**: Como avaliador do repositório, quero executar `python main.py --video sessao.mp4` e receber um relatório multimodal consolidado, sem precisar rodar cada módulo manualmente.

**Why P1**: É o critério principal de entrega — demonstrar que os módulos funcionam integrados.

**Acceptance Criteria**:

1. WHEN `python main.py --video <path>` é executado THEN o sistema SHALL rodar o pipeline clínico em lote (todos os pacientes do eICU) e o pipeline de vídeo
2. WHEN `--clinical-patient-id <id>` é passado THEN o sistema SHALL filtrar os alertas clínicos apenas para aquele `patientunitstayid` após a predição em lote
3. WHEN `--video-patient-id <id>` é passado THEN o alerta de vídeo SHALL usar esse ID como `module_id`; quando ausente, usa default `"video_001"`
4. WHEN ambos os módulos terminam THEN o sistema SHALL consolidar os alertas em `outputs/final_multimodal_report.json`
5. WHEN o relatório é gerado THEN o sistema SHALL imprimí-lo formatado no terminal
6. WHEN um módulo não encontra seus dados de entrada THEN o sistema SHALL exibir mensagem de erro clara e interromper

**Independent Test**: `python main.py --video tests/fixtures/test_video.mp4` gera `outputs/final_multimodal_report.json` com campos `resumo` e `alertas`.

---

### P1: Relatório consolidado correto ⭐ MVP

**User Story**: Como avaliador, quero que o relatório reflita corretamente o risco mais crítico entre os módulos, mesmo que um módulo indique baixo risco.

**Why P1**: Requisito central de fusão — risco crítico não pode ser silenciado.

**Acceptance Criteria**:

1. WHEN clínico tem score 0.91 e vídeo tem score 0.10 THEN `resumo.score_medio` SHALL ser 0.51 (média)
2. WHEN clínico tem score 0.91 e vídeo tem score 0.10 THEN `resumo.nivel_mais_critico` SHALL ser `"alto"`
3. WHEN `nivel_mais_critico` é `"alto"` THEN `resumo.recomendacao_geral` SHALL ser `"Acionar equipe médica para reavaliação imediata do paciente."`
4. WHEN há N alertas dos módulos THEN `alertas` SHALL conter todos os N alertas individuais com `module_id`, `modulo`, `score_risco`, `nivel_risco`, `descricao`, `recomendacao`
5. WHEN um alerta do módulo clínico tem `sample_id` THEN ele SHALL aparecer no relatório como `module_id`
6. WHEN um alerta do módulo de vídeo tem `patient_id` THEN ele SHALL aparecer no relatório como `module_id`

**Independent Test**: `pytest tests/test_fusion.py` — testes unitários com fixtures JSON cobrem todos os cenários de score.

---

### P2: Extensibilidade para módulo de áudio

**User Story**: Como desenvolvedor, quero que adicionar o módulo de áudio exija apenas criar um `AudioAdapter`, sem alterar `MultimodalFusion`.

**Why P2**: Requisito arquitetural — a branch de áudio está quase pronta.

**Acceptance Criteria**:

1. WHEN um novo adaptador implementa a interface `ModuleAdapter` THEN ele SHALL poder ser registrado em `MultimodalFusion` sem mudança no core
2. WHEN `AudioAdapter` é registrado THEN `main.py` SHALL aceitar `--audio <path>` sem refatoração do fluxo de fusão

**Independent Test**: Criar `AudioAdapter` de stub e registrá-lo — relatório passa a incluir `"audio_texto"` em `modulos_analisados`.

---

### P2: CI GitHub Actions

**User Story**: Como mantenedor do repositório, quero que o CI valide automaticamente que a pipeline completa roda sem erros a cada push.

**Why P2**: Garante que mudanças futuras não quebram a integração silenciosamente.

**Acceptance Criteria**:

1. WHEN há push ou PR no branch `main` THEN o CI SHALL rodar `python main.py`
2. WHEN o CI roda THEN ele SHALL baixar os dados eICU Demo usando credenciais PhysioNet em GitHub Secrets
3. WHEN o CI roda THEN ele SHALL usar `tests/fixtures/test_video.mp4` incluso no repo
4. WHEN a execução completa THEN o CI SHALL validar que `outputs/final_multimodal_report.json` existe e contém `resumo` e `alertas`
5. WHEN `PHYSIONET_USER` ou `PHYSIONET_PASSWORD` não estão configurados THEN o CI SHALL falhar com mensagem de erro explicativa

**Independent Test**: Push no branch `main` dispara workflow e o job `fusion` passa verde.

---

### P3: Testes unitários da lógica de fusão

**User Story**: Como desenvolvedor, quero testes unitários que verifiquem a lógica de fusão isoladamente, sem executar os módulos pesados.

**Why P3**: Feedback rápido durante desenvolvimento.

**Acceptance Criteria**:

1. WHEN `pytest tests/test_fusion.py` é executado THEN SHALL passar com 100% dos testes
2. WHEN score_medio é calculado com fixtures JSON THEN SHALL ser a média aritmética dos scores
3. WHEN nivel_mais_critico é derivado THEN SHALL refletir o alerta de maior score_risco

**Independent Test**: `pytest tests/test_fusion.py -v` — todos os casos passam sem precisar dos datasets reais.

---

## Edge Cases

- WHEN nenhum módulo tem alertas THEN `resumo.total_alertas` SHALL ser 0 e `alertas` SHALL ser `[]`
- WHEN apenas um módulo tem alertas THEN o relatório SHALL conter apenas os alertas desse módulo
- WHEN o arquivo de vídeo não existe THEN o sistema SHALL exibir `"Arquivo de vídeo não encontrado: <path>"` e encerrar com código de saída 1
- WHEN os dados do eICU não estão em `data/raw/` THEN o sistema SHALL exibir instrução de download e encerrar com código de saída 1
- WHEN `--clinical-patient-id` é passado mas não existe no eICU THEN `alertas` SHALL conter 0 alertas clínicos e o relatório SHALL continuar válido
- WHEN todos os scores são iguais THEN `score_medio` e `nivel_mais_critico` SHALL ser consistentes entre si
- WHEN `outputs/` não existe THEN o sistema SHALL criá-la antes de salvar o relatório

---

## Requirement Traceability

| ID | Story | Fase | Status |
|----|-------|------|--------|
| FUS-01 | P1: Execução end-to-end — pipeline clínico roda | Design | Done |
| FUS-02 | P1: Execução end-to-end — pipeline vídeo roda | Design | Done |
| FUS-03 | P1: Execução end-to-end — relatório gerado | Design | Done |
| FUS-04 | P1: Execução end-to-end — imprime no terminal | Design | Done |
| FUS-05 | P1: Execução end-to-end — erro claro se dados ausentes | Design | Done |
| FUS-20 | P1: CLI — --clinical-patient-id filtra alertas pós-predição | Design | Done |
| FUS-21 | P1: CLI — --video-patient-id define module_id do alerta de vídeo | Design | Done |
| FUS-06 | P1: Relatório correto — score_medio = média | Design | Done |
| FUS-07 | P1: Relatório correto — nivel_mais_critico = pior alerta | Design | Done |
| FUS-08 | P1: Relatório correto — recomendacao_geral baseada no pior | Design | Done |
| FUS-09 | P1: Relatório correto — lista de alertas individuais | Design | Done |
| FUS-10 | P1: Relatório correto — normalização sample_id → module_id | Design | Done |
| FUS-11 | P1: Relatório correto — normalização patient_id → module_id | Design | Done |
| FUS-12 | P2: Extensibilidade — interface ModuleAdapter | Design | Done |
| FUS-13 | P2: Extensibilidade — registro sem mudança no core | Design | Done |
| FUS-14 | P2: CI — workflow dispara em push/PR | Design | Done |
| FUS-15 | P2: CI — baixa eICU Demo via secrets | Design | Won't do (usamos fixtures mockadas) |
| FUS-16 | P2: CI — valida estrutura do JSON gerado | Design | Done |
| FUS-17 | P3: Testes unitários — pytest passa | Design | Done |
| FUS-18 | P3: Testes unitários — score_medio correto | Design | Done |
| FUS-19 | P3: Testes unitários — nivel_mais_critico correto | Design | Done |

---

## Success Criteria

- [ ] `python main.py --video tests/fixtures/test_video.mp4` gera relatório válido em < 5 min em CPU
- [ ] CI passa verde no branch `main`
- [ ] `pytest tests/test_fusion.py` passa com 100% dos testes (≥ 6 casos)
- [ ] Adicionar `AudioAdapter` de stub não requer mudança em `fusion.py` core
