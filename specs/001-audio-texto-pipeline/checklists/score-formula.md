# Score Formula Checklist: Pipeline de Áudio — Alerta Padronizado (módulo `audio_texto`)

**Purpose**: Validate score formula requirements quality before proceeding to /speckit-plan
**Created**: 2026-07-12
**Feature**: [spec.md](../spec.md)
**Gate**: Pré-implementação — todos os itens MUST estar resolvidos antes de iniciar o plano técnico

---

## Requirement Completeness

- [x] CHK001 - É `score_textual` (o score bruto do texto *antes* da ponderação pela confiança em FR-003) definido com seu método de cálculo e faixa de valores esperada? [Gap, Spec §FR-003] → **RESOLVIDO 2026-07-12**: faixa [0.0,1.0] e invariantes definidas em FR-005; mapeamento detalhado delegado ao `/speckit-plan`
- [x] CHK002 - É `score_acústico` definido com seu método de cálculo e faixa de entrada esperada (0.0–1.0)? O spec delega a extração de características acústicas ao FR-004, mas não define como essas características se convertem em um único score numérico. [Gap, Spec §FR-004, FR-007] → **RESOLVIDO 2026-07-12**: faixa [0.0,1.0] e invariantes definidas em FR-004; mapeamento detalhado delegado ao `/speckit-plan`
- [x] CHK003 - A origem de `confiança_transcrição` está documentada? É o campo de confiança retornado pelo serviço de transcrição, uma média por palavra, um valor único por chamada, ou outro? [Completeness, Spec §FR-003] → **RESOLVIDO 2026-07-13** (remediação `/speckit-analyze`): documentado em [`contracts/transcription.json`](../contracts/transcription.json) — valor único por chamada (`NBest[0].Confidence` do resultado detalhado do Azure Speech SDK), nativamente em `[0.0, 1.0]`, sem uso de média por palavra nesta versão. Referenciado em `data-model.md` (Entity TranscriptionResult).

---

## Requirement Clarity

- [x] CHK004 - A fórmula `score_textual_efetivo = score_textual × confiança_transcrição` em FR-003 especifica explicitamente que ambos os operandos devem estar no intervalo [0.0, 1.0] para garantir que `score_textual_efetivo` também permaneça em [0.0, 1.0]? [Clarity, Spec §FR-003] → **RESOLVIDO 2026-07-12**: FR-003 recebeu invariante de normalização explícita: ambos os operandos MUST estar em [0.0, 1.0] antes da operação
- [x] CHK005 - FR-007 define claramente que `score_acústico` e `score_textual_efetivo` devem ser individualmente normalizados para [0.0, 1.0] antes da operação `max()`? Ou pode existir um caso onde `max()` retorne valor fora desse intervalo? [Ambiguity, Spec §FR-007] → **RESOLVIDO 2026-07-12**: coberto pela invariante de FR-003 (score_textual_efetivo ∈ [0.0,1.0]) e pela invariante de FR-004 (score_acústico ∈ [0.0,1.0]); max() sobre dois valores em [0,1] sempre retorna valor em [0,1]
- [x] CHK006 - Os valores de fronteira de FR-008 são inequívocos quanto à atribuição? Por exemplo, `score = 0.4` pertence a "moderado" (0.4 ≤ score < 0.7) e `score = 0.7` pertence a "alto" (score ≥ 0.7), mas isso está explicitado sem necessidade de inferência? [Clarity, Spec §FR-008] → **RESOLVIDO 2026-07-12**: Assumptions atualizado com declaração explícita dos pisos inclusivos: 0.4 → "moderado", 0.7 → "alto"

---

## Edge Case Coverage

- [x] CHK007 - O comportamento quando `confiança_transcrição = 0.0` está especificado? Pela fórmula de FR-003, isso resulta em `score_textual_efetivo = 0.0` independentemente do conteúdo textual — mesmo que a transcrição contenha termos críticos. É este o comportamento desejado, ou existe um piso mínimo para `score_textual_efetivo`? [Edge Case, Spec §FR-003] → **RESOLVIDO 2026-07-12**: coberto pela regra de piso de FR-003 — com `confiança = 0.0` e termos críticos presentes, `score_textual_efetivo = max(0, 0.4) = 0.4`; sem termos críticos, `= 0.0` (intencional)
- [x] CHK008 - O comportamento quando `score_acústico = 0.0` *e* `score_textual_efetivo = 0.0` simultaneamente está especificado? O resultado `score_risco = 0.0` é consistente com a expectativa de SC-006 (nível de risco "baixo" + `tipo_anomalia = "nenhuma"`)? [Edge Case, Spec §FR-007, SC-006] → **RESOLVIDO 2026-07-12**: edge case adicionado explicitamente na seção Edge Cases da spec — `score_risco = 0.0` → `nivel_risco = "baixo"` + `tipo_anomalia = "nenhuma"`, consistente com SC-006
- [x] CHK009 - O comportamento para sinais conflitantes de *grau extremo* está definido? Por exemplo: `score_acústico = 0.9` (sinal acústico de alto risco) e `score_textual_efetivo = 0.0` (conteúdo verbal sem queixas)? O spec deve confirmar que `max(0.9, 0.0) = 0.9` é o resultado intencional, e que a descrição do alerta reflete esse conflito de forma rastreável. [Edge Case, Spec §FR-007, FR-009] → **RESOLVIDO 2026-07-12**: edge case de conflito extremo adicionado na spec com resultado determinístico explícito; FR-009 reforçado com obrigação de citar a fonte do score na descrição

---

## Acceptance Criteria Measurability

- [x] CHK010 - SC-002 ("100% dos scores dentro de 0.0–1.0") é verificável sem conhecer a implementação de `score_acústico` e `score_textual`? Estão todos os scores intermediários com intervalo de saída documentado nos requisitos? [Measurability, Spec §SC-002] → **RESOLVIDO 2026-07-12**: todos os scores intermediários agora têm faixa [0.0,1.0] documentada: `score_acústico` em FR-004, `score_textual` em FR-005, `score_textual_efetivo` em FR-003; SC-002 é verificável por invariante de spec, não dependendo de implementação
- [x] CHK011 - SC-003 ("ao menos um termo crítico → `nivel_risco ≥ moderado`") é consistente com a fórmula de FR-003? Se `confiança_transcrição` for muito baixa (ex.: 0.1) e `score_textual = 0.5` (termo crítico presente), então `score_textual_efetivo = 0.05` → `nivel_risco = "baixo"`, violando SC-003. Esse conflito está resolvido no spec? [Conflict, Spec §SC-003, FR-003] → **RESOLVIDO 2026-07-12**: FR-003 atualizado com regra de piso — `score_textual_efetivo = max(score_textual × confiança, 0.4)` quando `termos_críticos ≥ 1`, garantindo `nivel_risco ≥ "moderado"` em todos os casos com termo crítico detectado
- [x] CHK012 - Os limiares de FR-008 (baixo < 0.4, moderado ≥ 0.4) são compatíveis com SC-003? Está documentado qual valor mínimo de `score_textual` garante `score_textual_efetivo ≥ 0.4` mesmo com confiança parcial? [Consistency, Spec §FR-008, SC-003] → **RESOLVIDO 2026-07-12**: coberto pelo piso de FR-003 — com termos críticos presentes, `score_textual_efetivo ≥ 0.4` é garantido independentemente de `score_textual` ou `confiança`; não é necessário documentar um valor mínimo de `score_textual` porque o piso torna a questão irrelevante

---

## Consistency

- [x] CHK013 - A seção Clarifications (2026-07-12) registra a fórmula como `score_risco = max(score_acústico, score_textual)`, mas FR-007 usa `max(score_acústico, score_textual_efetivo)`. Esse divergência entre as Clarifications e o requisito formal está resolvida e o texto canônico é único? [Conflict, Spec §FR-007, §Clarifications] → **RESOLVIDO 2026-07-12**: Clarifications atualizado para usar `score_textual_efetivo` com referência explícita a FR-003; texto canônico único
- [x] CHK014 - O Acceptance Scenario 1 de User Story 1 afirma que o alerta indica "nível de risco 'alto' (ou 'moderado', conforme intensidade combinada dos sinais)". Essa ambiguidade — "alto ou moderado" — é intencional, ou os critérios de FR-008 tornam o resultado determinístico para um dado score? O scenario deveria especificar o resultado esperado sem alternativas abertas. [Consistency, Spec §US-1, FR-008] → **RESOLVIDO 2026-07-12**: US-1 Scenario 1 corrigido — resultado determinístico declarado como "alto" com justificativa (dois termos críticos → `score_textual_efetivo ≥ 0.7`); ambiguidade "alto ou moderado" removida

---

## Dependencies & Assumptions

- [x] CHK015 - A dependência de `confiança_transcrição` em relação ao formato e à escala retornados pelo serviço de transcrição escolhido está documentada como assunção ou requisito de interface? Uma mudança de serviço que retorne confiança em outra escala (ex.: 0–100 em vez de 0.0–1.0) alteraria o comportamento da fórmula sem aviso. [Dependency, Spec §FR-003] → **RESOLVIDO 2026-07-12**: Assumptions atualizado — normalização para [0.0,1.0] é responsabilidade do adaptador do serviço; qualquer serviço com escala diferente MUST normalizar antes de chegar a FR-003; definição detalhada do adaptador fica para `/speckit-plan`
- [x] CHK016 - A assunção de que `score_textual ∈ [0.0, 1.0]` está explicitamente documentada, garantindo que `score_textual_efetivo` jamais exceda 1.0? Ou pode haver casos em que o cálculo do score textual (ex.: contagem de termos críticos sem normalização) produza valores > 1.0? [Assumption, Spec §FR-003, FR-007] → **RESOLVIDO 2026-07-12**: FR-005 já define `score_textual ∈ [0.0, 1.0]` como invariante; FR-003 reforça que ambos os operandos MUST estar em [0.0,1.0] antes da operação

---

## Notes

- Checklist gerado como gate pré-implementação, antes de `/speckit-plan`
- Foco: qualidade dos requisitos das fórmulas de score (FR-003, FR-007, FR-008)
- Audiência: autor da spec (auto-revisão)
- **Gate status (2026-07-13)**: 16/16 itens resolvidos. CHK003 resolvido via remediação de `/speckit-analyze` com criação de `contracts/transcription.json`. Nenhuma pendência aberta neste checklist.
