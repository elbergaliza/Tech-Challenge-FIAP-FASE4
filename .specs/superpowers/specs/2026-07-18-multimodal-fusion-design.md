# Spec: Fusão Multimodal e Alerta Consolidado

**Data:** 2026-07-18  
**Projeto:** Tech Challenge FIAP — Fase 4 (Grupo 57)  
**Escopo:** Módulo de fusão dos alertas clínico e de vídeo com geração de relatório consolidado

---

## 1. Contexto

O projeto é um sistema multimodal de monitoramento preventivo de pacientes composto por módulos independentes:

- **Módulo Clínico** (`eicu-anomaly-detection/`) — Isolation Forest sobre dados eICU. Gera `alerts.json` com alertas por internação.
- **Módulo Vídeo** (`modulo_video/`) — MediaPipe Pose + YOLOv8. Gera alerta JSON por sessão de vídeo.
- **Módulo Áudio** (branch `001-audio-texto-pipeline`, WIP) — Não incluído nesta fase. Arquitetura deve permitir integração futura sem mudança na lógica central.

O `src/fusion.py` atual tem um rascunho que:
- Faz média simples dos scores (dilui risco crítico)
- Tem `case_id` hardcoded
- Não distingue IDs entre módulos
- Não executa os módulos — apenas lê JSONs

---

## 2. Objetivos

1. Criar `fusion.py` na raiz com lógica de fusão correta (baseada em adaptadores extensíveis)
2. Criar `main.py` na raiz que executa os módulos e orquestra a fusão
3. Remover `src/` da raiz (era apenas um `fusion.py` solto)
4. Gerar `outputs/final_multimodal_report.json` com resumo + lista de alertas
5. Suportar CI com dados reais leves (eICU Demo + MP4 curto)

---

## 3. Estrutura de Arquivos

### Antes

```
Tech-Challenge-FIAP-FASE4/
├── eicu-anomaly-detection/
├── modulo_video/
├── src/
│   └── fusion.py          ← rascunho
├── README.md
└── requirements.txt
```

### Depois

```
Tech-Challenge-FIAP-FASE4/
├── eicu-anomaly-detection/    (não muda)
├── modulo_video/              (não muda)
├── fusion.py                  (NOVO — lógica de fusão + adaptadores)
├── main.py                    (NOVO — CLI, orquestra tudo)
├── outputs/                   (NOVO — relatório final)
│   └── final_multimodal_report.json
├── docs/
├── README.md                  (atualizar seção de integração)
└── requirements.txt
```

`src/` é removida da raiz.

---

## 4. Arquitetura: Adaptadores por Módulo

A fusão é baseada em **adaptadores**. Cada módulo tem um adaptador que:
1. Executa o pipeline do módulo (ou lê o JSON se já executado)
2. Normaliza o identificador local (`sample_id` / `patient_id`) → `module_id`
3. Retorna lista de alertas em schema interno unificado

Isso garante extensibilidade: adicionar o módulo de áudio = criar `AudioAdapter` e registrá-lo. Zero mudança na lógica central de fusão.

### Adaptadores previstos

| Adaptador | Módulo | ID de origem | Executa pipeline |
|-----------|--------|-------------|-----------------|
| `ClinicalAdapter` | `eicu-anomaly-detection` | `sample_id` | Sim — chama `train.main()` |
| `VideoAdapter` | `modulo_video` | `patient_id` | Sim — chama `processar_video()` |
| `AudioAdapter` | (futuro) | `patient_id` | Sim — chama `process_audio_recording()` |

### Schema interno unificado (entre adaptador e fusão)

```python
@dataclass
class AlertaNormalizado:
    module_id: str       # ID normalizado (era sample_id ou patient_id)
    modulo: str          # ex: "anomalias_clinicas_uti", "video_fisioterapia"
    tipo_anomalia: str
    score_risco: float   # 0.0 a 1.0
    nivel_risco: str     # "baixo" | "moderado" | "alto"
    descricao: str
    recomendacao: str
```

---

## 5. Lógica de Fusão

### Score do resumo

```
score_medio = média(score_risco de cada módulo com alertas)
```

O score do resumo é um **indicador agregado** da situação geral do paciente — não substitui os alertas individuais. O médico usa o score médio para ter uma visão geral e os alertas individuais para entender o detalhe de cada módulo.

### Recomendação geral

A `recomendacao_geral` é derivada do **pior alerta individual** (não da média), para garantir que um risco crítico em qualquer módulo seja sempre comunicado:

```
nivel_mais_critico = nivel_risco do alerta com maior score_risco
recomendacao_geral = baseada em nivel_mais_critico
```

Dessa forma o resumo mostra a média como indicador geral, mas a recomendação sempre reflete o caso mais grave.

### Faixas de risco (unificadas entre módulos)

| Nível    | Score        |
|----------|-------------|
| baixo    | 0.00 – 0.39  |
| moderado | 0.40 – 0.69  |
| alto     | 0.70 – 1.00  |

Alinhado com o módulo de áudio (spec mais formalizada com Pydantic).

### Recomendação geral

Derivada do `nivel_mais_critico`:

| Nível    | Recomendação |
|----------|-------------|
| alto     | Acionar equipe médica para reavaliação imediata do paciente. |
| moderado | Manter paciente em observação e repetir avaliação clínica. |
| baixo    | Continuar monitoramento preventivo. |

---

## 6. Schema do Relatório Final

Arquivo: `outputs/final_multimodal_report.json`

```json
{
  "gerado_em": "2026-07-18T14:30:22",
  "resumo": {
    "total_alertas": 5,
    "score_medio": 0.51,
    "nivel_mais_critico": "alto",
    "modulos_analisados": ["anomalias_clinicas_uti", "video_fisioterapia"],
    "modulos_com_alerta": ["anomalias_clinicas_uti"],
    "recomendacao_geral": "Acionar equipe médica para reavaliação imediata do paciente."
  },
  "alertas": [
    {
      "module_id": "141765",
      "modulo": "anomalias_clinicas_uti",
      "tipo_anomalia": "sinais_vitais",
      "score_risco": 0.91,
      "nivel_risco": "alto",
      "descricao": "Paciente apresentou frequência cardíaca máxima elevada, queda de oxigenação.",
      "recomendacao": "Reavaliar paciente e acionar equipe médica se necessário."
    },
    {
      "module_id": "video_001",
      "modulo": "video_fisioterapia",
      "tipo_anomalia": "movimento",
      "score_risco": 0.42,
      "nivel_risco": "moderado",
      "descricao": "Assimetria de passada entre as pernas (28%).",
      "recomendacao": "Revisar o exercício de fisioterapia."
    }
  ]
}
```

---

## 7. CLI — `main.py`

### Uso

```bash
# Executa clínico + vídeo e faz a fusão
python main.py --video modulo_video/data/entrada/sessao01.mp4 --patient-id paciente_001

# Sem YOLOv8 (máquina fraca)
python main.py --video sessao.mp4 --patient-id p001 --sem-objetos

# Modo sequencial (padrão — mais seguro em CPU)
python main.py --video sessao.mp4 --patient-id p001

# Salvar em path alternativo
python main.py --video sessao.mp4 --patient-id p001 --saida outputs/meu_relatorio.json
```

### Argumentos

| Argumento | Obrigatório | Padrão | Descrição |
|-----------|-------------|--------|-----------|
| `--video` | Sim | — | Caminho do vídeo MP4 para o módulo de vídeo |
| `--patient-id` | Não | `video_001` | ID da sessão de vídeo |
| `--saida` | Não | `outputs/final_multimodal_report.json` | Path do relatório final |
| `--sem-objetos` | Não | False | Desativa YOLOv8 no módulo de vídeo |
| `--silencioso` | Não | False | Suprime logs dos módulos |

### Comportamento

1. Executa `ClinicalAdapter.run()` — carrega eICU Demo, treina, gera alertas
2. Executa `VideoAdapter.run(video, patient_id)` — processa vídeo, gera alerta
3. `MultimodalFusion.fuse([alertas_clinicos, alerta_video])` — consolida
4. Salva `outputs/final_multimodal_report.json`
5. Imprime relatório formatado no terminal

Os módulos rodam **sequencialmente** por padrão (CPU, sem overhead de threading). A arquitetura permite paralelismo futuro via `ThreadPoolExecutor` caso os módulos sejam migrados para serviços remotos.

---

## 8. Extensibilidade — Módulo de Áudio

Para integrar o módulo de áudio (branch `001-audio-texto-pipeline`) quando estiver pronto:

1. Criar `AudioAdapter` em `fusion.py`:
   ```python
   class AudioAdapter:
       def run(self, audio_path: str, patient_id: str) -> list[AlertaNormalizado]:
           from src.audio.audio_pipeline import process_audio_recording
           from src.audio.audio_schemas import AudioProcessingRequest
           request = AudioProcessingRequest(patient_id=patient_id, audio_path=audio_path)
           alert = process_audio_recording(request)
           return [_normalizar_audio(alert)]
   ```
2. Adicionar `--audio` ao `main.py`
3. Registrar `AudioAdapter` na lista de adaptadores do `MultimodalFusion`

Zero mudança na lógica de fusão central.

---

## 9. Ambientes de Execução

| Ambiente | Dados | GPU | Propósito |
|----------|-------|-----|-----------|
| **Local** | Reais leves (eICU Demo + MP4 curto) | Não (CPU) | Desenvolvimento e validação |
| **CI (GitHub Actions)** | Reais leves (mesmos dados) | Não (CPU) | Verificar que pipeline não quebra |
| **Colab** | Reais completos | Opcional | Demonstração à banca, vídeos longos |

### Pré-requisitos locais e CI

```bash
# eICU Demo: baixar de https://physionet.org/content/eicu-crd-demo/2.0.1/
# Colocar em: eicu-anomaly-detection/modulo_anomalias/data/raw/
#   vitalPeriodic.csv.gz
#   lab.csv.gz
#   medication.csv.gz

# Vídeo: qualquer MP4 curto (10-30s), ex: sessao.mp4
```

### CI — GitHub Actions

- Workflow `fusion.yml` disparado em push/PR no `main`
- Baixa eICU Demo via `wget` com credencial PhysioNet armazenada em GitHub Secrets (`PHYSIONET_USER` / `PHYSIONET_PASSWORD`) — **pré-condição**: secrets devem ser configurados no repositório antes de ativar o CI
- Usa MP4 de teste leve em `tests/fixtures/test_video.mp4` — **este arquivo deve ser criado como parte da implementação** (vídeo curto de domínio público, < 2MB, incluso no repo)
- Roda `python main.py --video tests/fixtures/test_video.mp4 --patient-id ci_test`
- Valida que `outputs/final_multimodal_report.json` é gerado e tem estrutura correta

> **Nota:** O relatório final conterá `module_id` de origens distintas — IDs do eICU (todos os pacientes da execução clínica) e o ID da sessão de vídeo. Isso é esperado e documentado: a fusão é uma demonstração arquitetural, não um join por paciente real.

---

## 10. Testes

### Unitários (`tests/test_fusion.py`)

Testam a lógica de fusão com fixtures JSON:

- `test_score_maximo`: score final = max dos alertas (não média)
- `test_nivel_critico_preservado`: se um módulo é alto, resultado é alto
- `test_sem_alertas`: fusão com 0 alertas retorna relatório vazio válido
- `test_normalizar_sample_id`: `sample_id` é mapeado para `module_id`
- `test_normalizar_patient_id`: `patient_id` é mapeado para `module_id`
- `test_faixas_risco_unificadas`: classificação correta nas faixas 0.39/0.69/0.70

### End-to-end (Colab)

Notebook `colab_fusao.ipynb` que:
1. Instala dependências
2. Baixa eICU Demo + faz upload de vídeo
3. Roda `python main.py`
4. Exibe o `final_multimodal_report.json`

---

## 11. Mudanças nos Módulos Existentes

Os módulos **não são alterados**. A fusão adapta os schemas de saída existentes:

| Campo original | Módulo | Mapeamento |
|---------------|--------|-----------|
| `sample_id` | Clínico | → `module_id` no adaptador |
| `patient_id` | Vídeo | → `module_id` no adaptador |

As faixas de risco dos módulos individuais também não mudam — apenas o relatório consolidado usa as faixas unificadas.

---

## 12. O Que Não Está no Escopo

- Módulo de áudio (WIP — integração posterior)
- Interface web ou dashboard
- Banco de dados — saída apenas em arquivo JSON
- Streaming ou monitoramento em tempo real
- Validação clínica profissional

---

## 13. Decisões e Justificativas

| Decisão | Alternativa descartada | Justificativa |
|---------|----------------------|---------------|
| `score_medio` no resumo + `recomendacao_geral` baseada no pior alerta | Só score máximo | Score médio dá visão geral agregada; recomendação baseada no pior garante que risco crítico nunca é silenciado |
| Adaptadores por módulo | Lógica inline no `main.py` | Extensibilidade: adicionar áudio = criar um adaptador |
| `module_id` como campo unificado | `patient_id` ou `sample_id` | Os IDs vêm de datasets diferentes e não representam o mesmo paciente real |
| `fusion.py` + `main.py` na raiz | `modulo_fusao/` ou `src/fusion.py` | A fusão é o integrador do projeto, não um módulo do problema |
| Execução sequencial por padrão | Paralelo com ThreadPoolExecutor | CPU local; paralelismo pode ser adicionado quando módulos forem serviços remotos |
