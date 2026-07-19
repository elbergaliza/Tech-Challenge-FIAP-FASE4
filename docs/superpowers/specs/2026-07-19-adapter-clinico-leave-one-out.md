# Especificação: Separar Treino e Predição no Adapter Clínico

## Contexto

O `fusion/adapters/clinical/adapter.py` executa treinamento e predição sobre os mesmos dados, dentro do próprio adapter. Isso causa data leakage e concentra responsabilidade que deveria estar no módulo clínico.

## Objetivo

Alterar **apenas** o adapter clínico para separar treino e predição usando leave-one-out, controlável por variável de ambiente, e adicionar testes que comparem as duas abordagens.

## Requisitos

1. Manter o fluxo atual do adapter (carregar dados, features, detector, alertas).
2. Adicionar suporte à variável de ambiente `ADAPTER_CLINICAL_LEAVE_ONE_OUT`:
   - Se `true`/`1`/`yes` (case-insensitive): quando `patient_id` for informado, treinar com todos os pacientes **exceto** o alvo e predizer apenas o alvo.
   - Se ausente/`false`/`0`/`no`/string vazia: manter o comportimento atual (treinar e predizer com todos os dados, aplicando o filtro por `patient_id` após a geração de alertas).
3. Quando `patient_id` não for informado, sempre usar modo batch (treinar e predizer com todos).
4. Se `patient_id` for informado, leave-one-out ativo, e o paciente não existir nos dados: levantar `ValueError`.
5. Se após o leave-one-out o conjunto de treino ficar vazio: levantar `ValueError`.
6. Não alterar `eicu-anomaly-detection/src/train.py` nem criar novos arquivos no módulo clínico.

## Decisões de Design

- Escopo deliberadamente reduzido: apenas adapter.
- Variável de ambiente permite comparar resultados das duas abordagens sem alterar código.
- No modo batch desligado, `_filtrar_alertas` continua sendo usado para preservar comportimento externo.
- No modo leave-one-out, a predição já está restrita ao alvo, então `_filtrar_alertas` pode ser chamado normalmente.

## Arquivos Afetados

- Modificar: `fusion/adapters/clinical/adapter.py`
- Modificar: `tests/fusion/test_adapters.py`

## Critérios de Aceitação

- Todos os testes existentes continuam passando.
- Testes comparam alertas gerados com e sem `ADAPTER_CLINICAL_LEAVE_ONE_OUT=true`.
- E2E gera relatório em ambos os modos (batch e leave-one-out).
- Nenhum arquivo fora do adapter e de seus testes é alterado.
- Nenhum commit ou push é executado sem aprovação explícita do usuário.
