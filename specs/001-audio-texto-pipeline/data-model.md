# Data Model: Pipeline de Audio - `audio_texto`

## Overview

O modelo representa uma unica invocacao do pipeline para uma unica gravacao. A saida publica e sempre um `AudioAlert` valido quando o processamento e concluido com sucesso; entradas invalidas devem falhar antes da geracao do alerta.

## Entity: AudioProcessingRequest

Representa a entrada validada do modulo.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `patient_id` | string | yes | Nao vazio; deve representar identificador anonimizado ou id de amostra. |
| `audio_path` | string/path | yes | Arquivo existente com extensao `.wav` ou `.mp3`. |
| `language` | string | no | Default `pt-BR`; outros idiomas fora do escopo do MVP. |
| `source` | enum | no | `pt_br_demo`, `coswara`, `manual`, `unknown`. |
| `max_duration_seconds` | integer | no | Default `600`; deve ser `> 0`. |
| `max_size_mb` | integer | no | Default `50`; deve ser `> 0`. |

### Rules

- `patient_id` ausente ou vazio invalida a entrada.
- Arquivos fora de WAV/MP3, vazios, corrompidos, maiores que 50 MB ou com duracao maior que 10 minutos devem ser rejeitados explicitamente.
- `patient_id` pode aparecer em saidas e logs apenas como identificador anonimo/referencia; audio, transcricao e termos clinicos nao entram em logs.

## Entity: AudioMetadata

Representa propriedades tecnicas derivadas do arquivo de audio.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `duration_seconds` | float | yes | `0 < duration_seconds <= 600`. |
| `size_mb` | float | yes | `0 < size_mb <= 50`. |
| `format` | enum | yes | `wav` ou `mp3`. |
| `sample_rate_hz` | integer/null | no | Informativo; quando presente deve ser `> 0`. |
| `channels` | integer/null | no | Informativo; quando presente deve ser `>= 1`. |

## Entity: TranscriptionResult

Representa o resultado da Camada A de transcricao.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `text` | string | yes | Pode ser vazio quando nao houver fala compreensivel. |
| `confidence` | float | yes | Normalizado para `[0.0, 1.0]`. |
| `language` | string | yes | Default `pt-BR`. |
| `provider` | string | yes | Valor fixo `azure_speech_to_text`. |
| `status` | enum | yes | `success`, `no_speech`, `low_confidence`, `failed`. |

### Rules

- Confiança retornada em escala diferente deve ser normalizada no adaptador Azure antes de chegar ao dominio.
- `failed` deve encerrar a etapa de transcricao, mas nao necessariamente o pipeline se houver sinais acusticos suficientes e o erro nao for de entrada invalida.
- O texto transcrito pode ser persistido em `data/processed/` para auditoria, mas nunca deve ser logado.

## Entity: AcousticFeatures

Representa os sinais da Camada B minima.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `rms` | float/null | no | `>= 0.0` quando presente. |
| `peak_amplitude` | float/null | no | Normalizado para `[0.0, 1.0]` quando possivel. |
| `silence_ratio` | float/null | no | `[0.0, 1.0]`; proporcao de silencio/pausas. |
| `long_pause_count` | integer | yes | `>= 0`. |
| `cough_or_breathing_indicator` | enum | no | `none`, `possible`, `strong`. |
| `score_acustico` | float | yes | `[0.0, 1.0]`; `0.0` quando sem sinal de risco acustico. |
| `signals` | array[string] | yes | Lista sem conteudo sensivel; exemplos: `low_rms`, `long_pauses`, `strong_breathing_pattern`. |

### Scoring rules

- `score_acustico = 0.0` quando nenhum sinal acustico de risco for detectado.
- Indicadores acusticos simples devem produzir score proporcional, limitado a `[0.0, 1.0]`.
- MFCC, espectrograma completo e classificadores treinados nao fazem parte deste modelo no MVP.

## Entity: TextFindings

Representa achados derivados da transcricao pela Azure Text Analytics e regras locais.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `critical_terms` | array[string] | yes | Termos configurados encontrados; persistencia permitida, log proibido. |
| `sentiment` | enum | yes | `positive`, `neutral`, `negative`, `mixed`, `unknown`. |
| `sentiment_confidence` | float/null | no | `[0.0, 1.0]` quando presente. |
| `score_textual` | float | yes | `[0.0, 1.0]`. |
| `score_textual_efetivo` | float | yes | `[0.0, 1.0]`, apos ponderacao por confianca e piso de termo critico. |

### Scoring rules

- Sem termos criticos e sentimento neutro/positivo: `score_textual = 0.0`.
- Mais termos criticos distintos e sentimento negativo aumentam o score.
- Se houver ao menos um termo critico: `score_textual_efetivo = max(score_textual * confidence, 0.4)`.
- Se nao houver termo critico: `score_textual_efetivo = score_textual * confidence`.

## Entity: AudioAlert

Contrato publico final do modulo.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `patient_id` | string | yes | Mesmo identificador anonimizado da request. |
| `modulo` | literal | yes | Valor fixo `audio_texto`. |
| `tipo_anomalia` | enum/string | yes | `nenhuma`, `alteracao_respiratoria_vocal`, `termos_criticos`, `sinais_acusticos`, `baixa_confianca_transcricao` ou combinacoes documentadas. |
| `score_risco` | float | yes | `[0.0, 1.0]`. |
| `nivel_risco` | enum | yes | `baixo`, `moderado`, `alto`. |
| `descricao` | string | yes | Legivel e sem segredo; pode citar achados clinicos no arquivo de relatorio, mas nao em logs. |
| `recomendacao` | string | yes | Acao clinica coerente com o nivel de risco. |
| `evidencias` | object | no | Scores e sinais resumidos para auditoria; sem audio bruto. |

### Risk classification

| Condition | `nivel_risco` |
|---|---|
| `score_risco < 0.4` | `baixo` |
| `0.4 <= score_risco < 0.7` | `moderado` |
| `score_risco >= 0.7` | `alto` |

### Combination rule

`score_risco = max(score_acustico, score_textual_efetivo)`

Nenhuma fonte de sinal pode reduzir o risco identificado pela outra.

## State Transitions

```text
received
  -> input_validated
  -> audio_preprocessed
  -> transcribed | transcription_unavailable
  -> text_analyzed | text_analysis_skipped
  -> acoustic_analyzed
  -> scored
  -> alert_generated
  -> persisted
```

### Failure states

```text
received
  -> rejected_invalid_patient_id
  -> rejected_invalid_audio_file
  -> rejected_unsupported_format
  -> rejected_duration_or_size_limit
```

Falhas de entrada nao geram `AudioAlert`. Falhas parciais de servico externo devem ser representadas no processamento e podem gerar alerta apenas quando ainda houver base valida suficiente, especialmente sinais acusticos para FR-012.

## Relationships

- `AudioProcessingRequest` 1:1 `AudioMetadata`
- `AudioProcessingRequest` 1:0..1 `TranscriptionResult`
- `AudioProcessingRequest` 1:1 `AcousticFeatures`
- `TranscriptionResult` 1:0..1 `TextFindings`
- `AcousticFeatures` + `TextFindings` 1:1 `AudioAlert`

## Persistence

- `data/processed/`: metadados tecnicos, transcricao e resultados intermediarios controlados.
- `data/reports/`: um JSON final por gravacao processada com sucesso.
- Logs: somente etapa, duracao, status, identificador anonimizado e score; sem audio, transcricao ou termos clinicos.
