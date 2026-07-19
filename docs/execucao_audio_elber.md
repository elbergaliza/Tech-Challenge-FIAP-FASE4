
********************************************************************************************************


****************************DOCUMENTACAO DO MODULO DE AUDIO****************************
Lista objetiva para o colega que vai **orquestrar no sistema total** e **documentar a integração**.

**Atenção:** não compartilhe [`docs/execucao_audio_elber.txt`](docs/execucao_audio_elber.txt) como documentação — há chaves Azure/API em texto claro. Use só `.env` / [`docs/spec/CONFIGURACAO_AZURE.md`](docs/spec/CONFIGURACAO_AZURE.md) sem segredos.

---

## Ordem de leitura (prioridade)

### 1. Contratos de integração (obrigatório)

| Arquivo | Por quê |
|---|---|
| [`specs/001-audio-texto-pipeline/contracts/python-api.md`](specs/001-audio-texto-pipeline/contracts/python-api.md) | **API pública**: `process_audio_recording(request) -> AudioAlert`, erros, side effects |
| [`specs/001-audio-texto-pipeline/contracts/audio-alert.schema.json`](specs/001-audio-texto-pipeline/contracts/audio-alert.schema.json) | Formato do alerta que a fusão/orquestração deve consumir |
| [`specs/001-audio-texto-pipeline/contracts/audio-input.schema.json`](specs/001-audio-texto-pipeline/contracts/audio-input.schema.json) | Entrada esperada (`patient_id`, `audio_path`, limites) |
| [`specs/001-audio-texto-pipeline/contracts/cli.md`](specs/001-audio-texto-pipeline/contracts/cli.md) | Como rodar via CLI e variáveis Azure |

### 2. Modelo e visão do módulo

| Arquivo | Por quê |
|---|---|
| [`specs/001-audio-texto-pipeline/data-model.md`](specs/001-audio-texto-pipeline/data-model.md) | Entidades (`AudioProcessingRequest`, `AudioAlert`, scores) |
| [`specs/001-audio-texto-pipeline/plan.md`](specs/001-audio-texto-pipeline/plan.md) | Fronteira: módulo **desacoplado** de video/fusion; pastas `processed/` e `reports/` |
| [`specs/001-audio-texto-pipeline/quickstart.md`](specs/001-audio-texto-pipeline/quickstart.md) | Setup, `.env`, exemplo de chamada Python |

### 3. Código que ele realmente importa/chama

| Arquivo | Por quê |
|---|---|
| [`src/audio/audio_pipeline.py`](src/audio/audio_pipeline.py) | Função pública de orquestração |
| [`src/audio/audio_schemas.py`](src/audio/audio_schemas.py) | Tipos Pydantic de entrada/saída |
| [`src/audio/audio_cli.py`](src/audio/audio_cli.py) | Entrypoint CLI (smoke test) |
| [`src/audio/audio_storage.py`](src/audio/audio_storage.py) | Onde os JSONs são gravados (efeito colateral) |

Os outros (`audio_azure`, `audio_acoustics`, `audio_scoring`) são internos — ler só se precisar explicar o pipeline, não para “plugar” no módulo total.

### 4. Operação / Azure (sem segredos)

| Arquivo | Por quê |
|---|---|
| [`.env.example`](.env.example) | Nomes das 4 variáveis |
| [`docs/spec/CONFIGURACAO_AZURE.md`](docs/spec/CONFIGURACAO_AZURE.md) | Como obter credenciais no Azure |

---

## O que colocar na documentação de integração

Sugestão de seções mínimas:

1. **Contrato de chamada** — import + `AudioProcessingRequest` → `AudioAlert` (trecho de `python-api.md` / quickstart).
2. **Schema de saída** — campos que a fusão usa: `modulo`, `score_risco`, `nivel_risco`, `tipo_anomalia`, `evidencias` (`audio-alert.schema.json`).
3. **Pré-requisitos** — 4 vars Azure; áudio local WAV/MP3; `uv sync`.
4. **Artefatos** — `data/audio/reports/*_alert.json` (oficial); `processed/` (auditoria, opcional para o orquestrador).
5. **Erros** — códigos de `python-api.md` (`missing_azure_configuration`, `file_not_found`, etc.).
6. **Fronteira** — o módulo de áudio **não** depende de video/fusion; o orquestrador chama e consome o `AudioAlert`.

---

## Leitura opcional (só se precisar de contexto)

- [`specs/001-audio-texto-pipeline/spec.md`](specs/001-audio-texto-pipeline/spec.md) — requisitos funcionais  
- [`specs/001-audio-texto-pipeline/tasks.md`](specs/001-audio-texto-pipeline/tasks.md) — muito longo; não para integração  

**Mínimo vital:** `python-api.md` + `audio-alert.schema.json` + `audio_pipeline.py` + `audio_schemas.py` + quickstart.


********************************************************************************************************
********************************************************************************************************
********************************************************************************************************
********************************************************************************************************

**************************************
*******************EXECUCAO*******************
**************************************

uv run python -m src.audio.audio_cli `
--patient-id 0dfJArS4xbNhay72hpzOvlHkpIj2_amostra_001 `
--audio-path C:\WORKSPACES\workspace-PYTHON\Tech-Challenge-FIAP-FASE4\data\raw\coswara\20210816\0dfJArS4xbNhay72hpzOvlHkpIj2\breathing-deep.wav

Saída: JSON em data/audio/reports/ e artefatos em data/audio/processed/.

process --> esssa opção nao existe

 
------PARA TESTAR --> esse funcionou
import httpx

resp = httpx.post(
    "https://api.brainiall.com/v1/nlp/toxicity",
    headers={"Authorization": "Bearer brnl-c56575def1d7e2828e43a097f9613debbf256361a5dc3e31"},
    json={"text": "Hello world"},
)
print(resp.json())
# {"is_toxic": false, "score": 0.001, "label": "not_toxic"}


**************************************
*******************WARNING NA EXECUCAO*******************
**************************************
É um **aviso**, não um erro fatal. A execução continua (e no segundo comando até deu `status=success`).

## O que significa

```
RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
```

A biblioteca **pydub** (usada em `src/audio/audio_pipeline.py` e `src/audio/audio_acoustics.py` para ler o áudio) procurou o programa **ffmpeg** (ou **avconv**) no PATH do Windows e **não encontrou**.

Sem isso, pydub avisa que pode falhar em formatos que precisam de conversão externa (MP3, etc.).

## Por que aparece

1. O pipeline importa `pydub` ao carregar o áudio.
2. No import/uso, o pydub verifica se `ffmpeg` está instalado.
3. No seu ambiente ele não está no PATH → emite o `RuntimeWarning`.

## Por que ainda funcionou

No seu caso o arquivo é **`.wav`**. WAV costuma ser lido pelo pydub **sem** depender do ffmpeg. Por isso o aviso aparece, mas o processamento segue.

Se no futuro você passar **MP3** ou outro formato comprimido, aí a ausência do ffmpeg pode virar falha real de leitura.

**Resumo:** avisando que falta `ffmpeg` no sistema; com WAV Coswara isso normalmente é inofensivo.


---------SAIDA DO PROCESSAMENTO
São as **3 saídas de uma execução** do pipeline de áudio. O sufixo no nome (`…_alert.json`, `…_processed.json`, `…_transcription.json`) indica o papel; o timestamp no meio é só o horário UTC da gravação.

## O que cada um é

| Arquivo | Papel | Conteúdo (no seu run) |
|---|---|---|
| `…_alert.json` em `reports/` | **Saída oficial** do pipeline | Alerta de risco: `score_risco` 0.35, `nivel_risco` baixo, sinais acústicos |
| `…_processed.json` em `processed/` | **Artefato intermediário** completo | Metadados + transcrição + achados de texto + features acústicas |
| `…_transcription.json` em `processed/` | **Auditoria da transcrição** (FR-017) | Só o resultado do Speech: aqui `status: failed`, texto vazio |

No seu caso (respiração Coswara, sem fala), a transcrição falhou e o risco veio só da camada acústica — coerente com o alerta.

## Estão na especificação?

**Sim, no essencial** — pastas e papéis estão descritos; o contrato rígido existe sobretudo para o alerta.

- **`_alert.json`** — bem especificado: contrato [`contracts/audio-alert.schema.json`](specs/001-audio-texto-pipeline/contracts/audio-alert.schema.json), entidade `AudioAlert` em [`data-model.md`](specs/001-audio-texto-pipeline/data-model.md), CLI em [`contracts/cli.md`](specs/001-audio-texto-pipeline/contracts/cli.md).
- **`_processed.json`** — previsto como artefato intermediário em `data/audio/processed/` ([`plan.md`](specs/001-audio-texto-pipeline/plan.md), [`data-model.md`](specs/001-audio-texto-pipeline/data-model.md), quickstart). Não há um schema JSON separado só para esse arquivo; o conteúdo segue as entidades do data-model.
- **`_transcription.json`** — previsto por **FR-017** (preservar texto transcrito para auditoria) e pela task T020 (`save_transcription`). O arquivo [`contracts/transcription.json`](specs/001-audio-texto-pipeline/contracts/transcription.json) documenta a **confiança** do Azure, não o layout completo do ficheiro salvo em disco.

Nomeação `{patient_id}_{timestamp}_*.json` vem da implementação em [`src/audio/audio_storage.py`](src/audio/audio_storage.py), alinhada ao plano (persistência local JSON), sem ser um contrato formal de nome de ficheiro na spec.