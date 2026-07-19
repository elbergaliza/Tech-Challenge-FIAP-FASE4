# Python API Contract: `src.audio.audio_pipeline`

## Public import

```python
from src.audio.audio_pipeline import process_audio_recording
from src.audio.audio_schemas import AudioAlert, AudioProcessingRequest
```

## Function: `process_audio_recording`

```python
def process_audio_recording(request: AudioProcessingRequest) -> AudioAlert:
    ...
```

## Purpose

Processar uma unica gravacao local e retornar o alerta padronizado do modulo `audio_texto`, sem depender de video, texto/documentos, fusao multimodal, banco de dados ou framework web.

## Input contract

`request` deve seguir `contracts/audio-input.schema.json` e ser validado por Pydantic v2.

Regras obrigatorias:

- `patient_id` nao pode ser vazio.
- `audio_path` deve apontar para arquivo local WAV ou MP3.
- Tamanho maximo padrao: 50 MB.
- Duracao maxima padrao: 600 segundos.
- Idioma padrao: `pt-BR`.

## Output contract

Retorna `AudioAlert`, validado por Pydantic v2 e serializavel conforme `contracts/audio-alert.schema.json`.

Invariantes obrigatorias:

- `modulo == "audio_texto"`.
- `0.0 <= score_risco <= 1.0`.
- `nivel_risco` coerente com o score:
  - `baixo` quando `score_risco < 0.4`
  - `moderado` quando `0.4 <= score_risco < 0.7`
  - `alto` quando `score_risco >= 0.7`
- `score_risco = max(score_acustico, score_textual_efetivo)`.
- Se houver termo critico, `score_textual_efetivo >= 0.4`.

## Expected exceptions

Implementacao deve expor excecoes especificas ou uma excecao base com codigo de erro estavel:

| Error code | Condition |
|---|---|
| `invalid_patient_id` | `patient_id` ausente ou vazio. |
| `unsupported_format` | Arquivo diferente de WAV/MP3. |
| `file_not_found` | Caminho inexistente. |
| `file_too_large` | Arquivo acima do limite configurado. |
| `duration_too_long` | Duracao acima do limite configurado. |
| `corrupted_audio` | Arquivo vazio/corrompido ou ilegivel. |
| `missing_azure_configuration` | Variaveis de ambiente obrigatorias ausentes. |

Falhas parciais de transcricao/text analytics nao devem vazar credenciais nem conteudo clinico em excecoes ou logs.

## Side effects

- Pode gravar artefatos intermediarios em `data/audio/processed/`.
- Pode gravar o alerta final em `data/audio/reports/` quando chamado via CLI ou quando configurado explicitamente.
- Deve emitir logs estruturados por etapa com duracao, status e `patient_id` anonimizado/referencia.
- Nao deve logar audio bruto, transcricao ou termos criticos.
- Deve medir a duracao total do pipeline e comparar com `request.timeout_seconds` (default `60`, NFR-001). Exceder o limite NAO aborta o processamento nem gera excecao; MUST apenas marcar `AudioAlert.evidencias.excedeu_limite_latencia = true` e emitir log de falha de performance observavel (SC-007).

## Test doubles

Para testes, adaptadores Azure devem ser injetaveis ou mockaveis, permitindo validar:

- transcricao bem-sucedida de amostra PT-BR;
- baixa confianca de transcricao;
- ausencia de fala compreensivel;
- termos criticos com piso de score;
- falha parcial Azure com fallback acustico quando aplicavel.
