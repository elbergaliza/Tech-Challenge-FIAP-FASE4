# Quickstart: Pipeline de Audio - `audio_texto`

## 1. Preparar ambiente

Da raiz do repositorio:

```powershell
uv sync
```

Quando a implementacao iniciar, declarar as dependencias da feature com `uv`:

```powershell
uv add azure-cognitiveservices-speech azure-ai-textanalytics python-dotenv moviepy pydub librosa pydantic typer
uv add --dev pytest pytest-mock ruff pyright
```

`structlog` e opcional. Use apenas se a implementacao decidir emitir logs estruturados com essa biblioteca mantendo compatibilidade com `logging`.

## 2. Configurar Azure localmente

Configurar localmente, sem versionar segredos, as variaveis obrigatorias:

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `AZURE_TEXT_ANALYTICS_KEY`
- `AZURE_TEXT_ANALYTICS_ENDPOINT`

As credenciais podem ser carregadas pelo ambiente do sistema ou por `.env` local. O arquivo `.env` nao deve ser versionado.

## 3. Preparar dados de demo

Estrutura local sugerida:

```text
data/
├── raw/
│   ├── coswara/
│   └── pt-br/
├── processed/
└── reports/
```

Dados:

- Coswara: usar 20 a 50 participantes para tosse/respiracao e sinais acusticos minimos.
- PT-BR local: criar 2 a 3 WAV curtos para demonstrar Azure Speech to Text e Azure Text Analytics em portugues.

Nao versionar audio real de paciente ou dataset bruto.

## 4. Executar pipeline por CLI

Exemplo para uma amostra PT-BR local:

```powershell
uv run python -m src.audio_cli process --patient-id sample_ptbr_001 --audio-path data/raw/pt-br/sample_ptbr_001.wav
```

Resultado esperado:

- Um JSON final em `data/reports/`.
- Artefatos intermediarios em `data/processed/`, quando habilitados.
- Logs por etapa com duracao, status e `patient_id` de referencia.
- Nenhum log contendo audio bruto, transcricao completa, termos clinicos ou credenciais.

## 5. Executar via API Python

Contrato esperado:

```python
from src.audio_pipeline import process_audio_recording
from src.audio_schemas import AudioProcessingRequest

request = AudioProcessingRequest(
    patient_id="sample_ptbr_001",
    audio_path="data/raw/pt-br/sample_ptbr_001.wav",
)

alert = process_audio_recording(request)
print(alert.model_dump_json())
```

`alert` deve validar contra `specs/001-audio-texto-pipeline/contracts/audio-alert.schema.json`.

## 6. Validar qualidade

Comandos esperados para a feature:

```powershell
uv run pytest
uv run ruff check .
uv run pyright
```

Cobertura minima esperada:

- Score textual com termo critico e piso `0.4`.
- Score combinado por `max(score_acustico, score_textual_efetivo)`.
- Classificacao `baixo`, `moderado`, `alto` nas fronteiras `0.4` e `0.7`.
- Entrada invalida sem gerar alerta.
- Gravacao sem fala compreensivel gerando alerta valido por sinais acusticos.
- Mock de Azure Speech e Azure Text Analytics sem credenciais reais.

## 7. Fora de escopo neste quickstart

- Flask, FastAPI, UI web ou endpoint HTTP.
- Banco de dados, ORM ou storage cloud.
- Autenticacao/autorizacao de usuario final.
- Whisper, Google Speech, SpeechRecognition ou Comprehend como substitutos do Azure para audio.
- MFCC, espectrograma completo, modelos treinados, AudioSet, streaming ou lote massivo.
