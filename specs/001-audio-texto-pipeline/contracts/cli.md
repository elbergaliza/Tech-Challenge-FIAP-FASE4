# CLI Contract: `audio_texto`

## Command

```text
uv run python -m src.audio_cli process --patient-id <id> --audio-path <path> [--output-dir data/reports] [--processed-dir data/processed]
```

## Purpose

Processar uma unica gravacao WAV/MP3 e gerar um alerta JSON padronizado do modulo `audio_texto`.

## Inputs

| Option | Required | Description |
|---|---:|---|
| `--patient-id` | yes | Identificador anonimizado do paciente/amostra. |
| `--audio-path` | yes | Caminho local para arquivo `.wav` ou `.mp3`. |
| `--language` | no | Default `pt-BR`; outros idiomas fora do escopo. |
| `--output-dir` | no | Diretorio para alerta final; default `data/reports`. |
| `--processed-dir` | no | Diretorio para artefatos intermediarios; default `data/processed`. |
| `--max-duration-seconds` | no | Default `600`. |
| `--max-size-mb` | no | Default `50`. |
| `--timeout-seconds` | no | Default `60`. Limite de latencia parametrizavel de NFR-001; excedido nao aborta o processamento, mas marca `evidencias.excedeu_limite_latencia=true` no alerta e gera log de falha de performance (SC-007). |

## Environment

As credenciais Azure devem ser lidas exclusivamente de variaveis de ambiente carregadas pelo processo ou por `.env` local nao versionado:

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `AZURE_TEXT_ANALYTICS_KEY`
- `AZURE_TEXT_ANALYTICS_ENDPOINT`

O comando nao aceita chaves de API por argumento.

## Outputs

Em sucesso:

- Cria exatamente um arquivo JSON em `data/reports/` ou no diretorio definido por `--output-dir`.
- Imprime somente o caminho do relatorio e um status resumido.
- Nao imprime audio, transcricao, termos criticos nem credenciais.

Formato do JSON: `contracts/audio-alert.schema.json`.

Em erro de entrada:

- Retorna codigo de saida diferente de zero.
- Exibe mensagem curta com categoria de erro (`invalid_patient_id`, `unsupported_format`, `file_too_large`, `duration_too_long`, `corrupted_audio`).
- Nao gera alerta final.

Em erro parcial de servico externo:

- O pipeline pode continuar quando houver base valida por sinais acusticos.
- A descricao do alerta deve indicar incerteza operacional de forma segura, sem expor conteudo clinico sensivel em log.

## Non-Goals

- Nao expor endpoint HTTP.
- Nao aceitar multiplos arquivos por chamada.
- Nao autenticar usuario final.
- Nao substituir Azure por Whisper, Google Speech ou Comprehend.
