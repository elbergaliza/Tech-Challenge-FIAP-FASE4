# Progresso do Tech Challenge FIAP — Fase 4

Última atualização: 2026-07-18

---

## Módulos e funcionalidades

| Área | Status | Observações |
|------|--------|-------------|
| Detecção de anomalias clínicas (eICU) | ✅ Funcional | Isolation Forest; alertas em JSON/CSV |
| Análise de vídeo / fisioterapia | ✅ Funcional | MediaPipe Pose + YOLOv8 opcional; alertas de movimento |
| Fusão multimodal | ✅ Funcional | `main.py` orquestra clínico + vídeo; relatório unificado em JSON |
| Adaptadores (adapters) | ✅ Implementados | ClinicalAdapter, VideoAdapter, AudioAdapter stub |
| Testes unitários | ✅ Passando | 18 testes via `pytest tests/` |
| Testes E2E mockados | ✅ Passando | `python main.py` com fixtures funciona |
| CI GitHub Actions | ✅ Configurado | `.github/workflows/fusion.yml` com dados mockados |
| Módulo de áudio + texto | ⏸️ Próxima fase | Apenas stub; requer Azure Cognitive Services |
| Azure Cognitive Services | ⏸️ Próxima fase | Não integrado |

---

## Decisões pendentes de alinhamento

| # | Tópico | Onde impacta | Status |
|---|--------|-----------|--------|
| 1 | Faixas de risco inconsistentes | `eicu-anomaly-detection`, `modulo_video`, `fusion/core/schema` | Aguardando definição do grupo |
| 2 | Alertas de nível "baixo" no relatório | `main.py`, `fusion/core/fusion.py` | Aguardando definição do grupo |

---

## Commits recentes

```text
32f2df3 docs: corrige README e estrutura do projeto para refletir estado atual
e59f39b ci: adicionar workflow de fusão multimodal com dados mockados
```

---

## Próximos passos

1. Alinhar faixas de risco entre clínico, vídeo e fusão.
2. Decidir se alertas de nível "baixo" devem constar no relatório final.
3. Implementar módulo de áudio real (`adapters/audio/adapter.py`).
4. Integrar Azure Cognitive Services (Speech to Text + Text Analytics).
5. Criar vídeo de demonstração de até 15 minutos.
