# Tech Challenge FIAP — Fase 4

Repositório do **Tech Challenge FIAP — Fase 4**, desenvolvido pelo Grupo 57.

O projeto propõe um sistema multimodal de monitoramento preventivo de pacientes, composto por módulos independentes de:

* análise de vídeo;
* análise de áudio e texto;
* detecção de anomalias clínicas;
* integração e fusão dos resultados.

---

# Execução local (fluxo completo)

Todos os comandos abaixo devem ser executados a partir da raiz do repositório.

## 1. Criar e ativar o ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

## 2. Instalar as dependências e registrar os pacotes internos

```bash
pip install -r requirements.txt
pip install -e .
```

> O projeto foi validado com Python 3.12. O `requirements.txt` unificado cobre o módulo clínico, o módulo de vídeo e os testes. O `pip install -e .` registra os pacotes internos (`eicu_anomaly_detection`, `modulo_video`, `fusion`) como editáveis.

## 3. Obter os dados

Você tem duas opções:

**Opção A — dados mockados (recomendado para testes locais):**

```bash
python tests/fixtures/generate_fixtures.py
```

Isso cria:

```text
tests/fixtures/
├── mock_eicu/
│   ├── patient.csv.gz
│   ├── vitalPeriodic.csv.gz
│   ├── vitalAperiodic.csv.gz
│   ├── lab.csv.gz
│   └── medication.csv.gz
└── test_video.mp4
```

**Opção B — dados reais do eICU Demo:**

Crie uma conta gratuita em https://physionet.org/, baixe os arquivos
`vitalPeriodic.csv.gz`, `lab.csv.gz` e `medication.csv.gz` do
[eICU Collaborative Research Database Demo v2.0.1](https://physionet.org/content/eicu-crd-demo/2.0.1/)
e coloque-os em:

```text
eicu-anomaly-detection/modulo_anomalias/data/raw/
```

## 4. Executar a fusão multimodal

Com os dados mockados:

```bash
python main.py \
  --video tests/fixtures/test_video.mp4 \
  --eicu-data tests/fixtures/mock_eicu \
  --video-patient-id local_test \
  --sem-objetos
```

Com dados eICU reais (sem filtro de paciente, processa todos):

```bash
python main.py \
  --video tests/fixtures/test_video.mp4 \
  --video-patient-id local_test \
  --sem-objetos
```

Com filtros opcionais:

```bash
python main.py --video sessao.mp4 \
  --clinical-patient-id 141765 \
  --video-patient-id p001 \
  --sem-objetos \
  --silencioso
```

### Evitando data leakage no adapter clínico

Por padrão, o `ClinicalAdapter` treina o detector com todos os pacientes do
`--eicu-data` e depois prediz sobre o mesmo conjunto. Isso pode elevar os
scores de risco do paciente solicitado, pois o modelo já "viu" esse paciente
durante o treinamento.

Para comparar com uma abordagem sem esse viés, ative o modo leave-one-out via
variável de ambiente:

```bash
ADAPTER_CLINICAL_LEAVE_ONE_OUT=1 python main.py \
  --video tests/fixtures/test_video.mp4 \
  --eicu-data tests/fixtures/mock_eicu \
  --clinical-patient-id 141761 \
  --video-patient-id local_test \
  --sem-objetos \
  --silencioso
```

Nesse modo, o detector é treinado com todos os pacientes **exceto** o
`--clinical-patient-id` informado, e a predição é feita apenas para esse
paciente. Atenção: sem ground truth médico, a escolha entre as abordagens
permanece uma questão de validação clínica.

## 5. Rodar os testes

```bash
pytest tests/ -v
```

> Os testes unitários não dependem das fixtures binárias. O teste E2E (`tests/test_e2e_mock.py`) gera as fixtures automaticamente na primeira execução, mas você pode gerá-las manualmente antes com `python tests/fixtures/generate_fixtures.py`.

---

# Módulos individuais

Cada módulo pode ser executado de forma isolada, sem passar pela fusão multimodal.

## Módulo clínico (`eicu-anomaly-detection`)

### Estrutura

```text
eicu-anomaly-detection/
├── src/                          # Pacote Python eicu_anomaly_detection
│   ├── __init__.py
│   ├── config.py
│   ├── data_loader.py
│   ├── feature_builder.py
│   ├── anomaly_detector.py
│   ├── alert_generator.py
│   ├── train.py
│   └── test_output.py
└── modulo_anomalias/
    ├── data/
    │   ├── raw/                  # Colocar os CSVs do eICU aqui
    │   └── processed/
    ├── models/
    └── outputs/
```

### Executar o pipeline completo

```bash
python -m eicu_anomaly_detection.train
```

Esse comando executa o pipeline completo:

1. carrega os sinais vitais, exames laboratoriais e medicações;
2. cria as features clínicas;
3. treina o modelo Isolation Forest;
4. gera predições, scores e níveis de risco;
5. gera alertas;
6. salva artefatos em `data/processed/`, `models/` e `outputs/`.

### Testar componentes isoladamente

Carregamento dos dados:

```bash
python -m eicu_anomaly_detection.data_loader
```

Criação das features:

```bash
python -m eicu_anomaly_detection.feature_builder
```

Geração de alertas a partir do treinamento:

```bash
python -m eicu_anomaly_detection.train
python -m eicu_anomaly_detection.test_output
```

### Usar como biblioteca Python

```python
from eicu_anomaly_detection.data_loader import EICUDataLoader
from eicu_anomaly_detection.feature_builder import ClinicalFeatureBuilder
from eicu_anomaly_detection.anomaly_detector import ClinicalAnomalyDetector
from eicu_anomaly_detection.alert_generator import AlertGenerator

loader = EICUDataLoader()
vital_df = loader.load_vital_periodic()

features = ClinicalFeatureBuilder().build_vital_features(vital_df)

detector = ClinicalAnomalyDetector()
detector.train(features)
predictions = detector.predict(features)

alerts = AlertGenerator().generate_alerts(predictions, features)
print(alerts)
```

## Módulo de vídeo (`modulo_video`)

### Executar o processamento de um vídeo

```bash
python -m modulo_video.pipeline tests/fixtures/test_video.mp4 --sem-objetos
```

Ou, via Python:

```python
from modulo_video.pipeline import processar_video

alerta = processar_video(
    video_path="tests/fixtures/test_video.mp4",
    usar_objetos=False,
)
print(alerta)
```

---

# Fusão Multimodal

A integração entre os módulos é feita pelo `main.py` na raiz. Ele executa os
adapters de cada módulo e consolida os alertas em um único relatório JSON.

## Estrutura da integração

```text
Tech-Challenge-FIAP-FASE4/
├── eicu-anomaly-detection/       # Módulo clínico (eICU)
│   ├── src/                      # Pacote Python eicu_anomaly_detection
│   └── modulo_anomalias/         # Dados, modelos e outputs do módulo
│
├── modulo_video/                 # Módulo de vídeo/fisioterapia
│   └── src/                      # Pacote Python modulo_video
│
├── fusion/                       # Motor de fusão multimodal
│   ├── adapters/                 # Adaptadores para os módulos externos
│   │   ├── base.py
│   │   ├── clinical/             # Adapter do módulo eICU
│   │   ├── video/                # Adapter do módulo de vídeo
│   │   └── audio/                # Adapter stub (futuro módulo de áudio)
│   ├── core/
│   │   ├── fusion.py
│   │   └── schema.py
│   └── io.py
│
├── tests/                        # Testes unitários e E2E
│   ├── fixtures/
│   ├── fusion/
│   └── test_e2e_mock.py
│
├── main.py                       # CLI de orquestração
├── outputs/                      # Relatório final gerado
└── requirements.txt
```

## Saída

O relatório final é salvo em:

```text
outputs/final_multimodal_report.json
```

Exemplo de resumo:

```json
{
  "gerado_em": "2026-07-18T14:30:22",
  "resumo": {
    "total_alertas": 5,
    "score_medio": 0.51,
    "nivel_mais_critico": "alto",
    "modulos_analisados": ["anomalias_clinicas_uti", "video_fisioterapia"],
    "modulos_com_alerta": ["anomalias_clinicas_uti", "video_fisioterapia"],
    "recomendacao_geral": "Acionar equipe médica para reavaliação imediata do paciente."
  },
  "alertas": [
    {
      "module_id": "141765",
      "modulo": "anomalias_clinicas_uti",
      "tipo_anomalia": "sinais_vitais",
      "score_risco": 0.91,
      "nivel_risco": "alto",
      "descricao": "...",
      "recomendacao": "..."
    }
  ]
}
```

### Regras de fusão

* `score_medio` = média dos `score_risco` de todos os alertas.
* `nivel_mais_critico` = nível do alerta com maior `score_risco`.
* `recomendacao_geral` = baseada no `nivel_mais_critico`.

### Extensibilidade

Adicionar o módulo de áudio (branch `001-audio-texto-pipeline`) exige apenas:

1. Implementar `AudioAdapter.run()` em `fusion/adapters/audio/adapter.py`.
2. Adicionar `--audio` no `main.py`.
3. Registrar `AudioAdapter` no `MultimodalFusion`.

Nenhuma mudança é necessária no motor de fusão em `fusion/core/fusion.py`.

## Integração futura

Como os módulos utilizam datasets diferentes, os identificadores (`module_id`)
não representam necessariamente o mesmo paciente real. A fusão é uma
demonstração arquitetural de como diferentes fontes podem alimentar um
sistema central de monitoramento preventivo.

---

# Execução no Google Colab

O jeito mais simples de executar o projeto com dados reais é usar o notebook `notebooks/TechChallenge_Colab_Completo.ipynb`.

## Passo a passo

1. **Abra o notebook no Colab**
   - Faça upload de `notebooks/TechChallenge_Colab_Completo.ipynb` no Google Colab, ou
   - Abra a partir da URL pública do repositório.

2. **Execute as células em ordem**
   1. **Clone e instalação**: faz `git clone`, instala as dependências e registra os pacotes editáveis com `pip install -e .`.
   2. **Dados reais do eICU Demo**: baixa automaticamente os arquivos `vitalPeriodic.csv.gz`, `lab.csv.gz` e `medication.csv.gz` do eICU Demo (PhysioNet).
   3. **Vídeo**: gera um vídeo de teste com OpenCV. Opcionalmente, você pode fazer upload de um vídeo próprio para `modulo_video/data/exemplos/` e ajustar o caminho na célula.
   4. **Fusão multimodal**: executa `main.py` usando os dados reais do eICU e o vídeo selecionado.
   5. **Relatório final**: exibe o JSON `outputs/final_multimodal_report.json` com os alertas unificados.

## Testar uma branch específica

Para testar alterações em desenvolvimento, defina a branch antes da primeira célula:

```python
import os
os.environ['NOTEBOOK_BRANCH'] = 'feat/fusao-multimodal'
```

O valor padrão é `main`.

> Atenção: o download do eICU Demo pode demorar alguns minutos. Os arquivos são públicos e não exigem login.

---

## Exemplo de alerta gerado

```json
{
  "sample_id": "141765",
  "modulo": "anomalias_clinicas_uti",
  "tipo_anomalia": "sinais_vitais",
  "score_risco": 0.87,
  "nivel_risco": "alto",
  "descricao": "Paciente apresentou frequência cardíaca máxima elevada, queda de oxigenação e uso de antibiótico.",
  "recomendacao": "Reavaliar paciente e acionar equipe médica se necessário."
}
```

---

## Interpretação da saída

O campo `score_risco` varia de 0 a 1.

Nesta implementação, foram adotadas as seguintes faixas:

```text
0.00 a 0.44 → baixo
0.45 a 0.74 → moderado
0.75 a 1.00 → alto
```

Essas faixas foram definidas para o protótipo acadêmico.

O `score_risco` representa o grau relativo de anomalia calculado pelo sistema. Ele não deve ser interpretado como uma probabilidade clínica calibrada.

### `nivel_risco`

Classifica o resultado em:

```text
baixo
moderado
alto
```

### `descricao`

Apresenta os principais fatores observados nos dados, como:

* frequência cardíaca elevada;
* baixa oxigenação;
* pressão arterial alterada;
* alteração de temperatura;
* resultado laboratorial fora do padrão;
* presença de grupos específicos de medicações.

### `recomendacao`

Apresenta uma sugestão de encaminhamento para a equipe médica.

---

## Dataset utilizado

Dataset:

**eICU Collaborative Research Database Demo v2.0.1**

Página oficial:

https://physionet.org/content/eicu-crd-demo/2.0.1/

Os arquivos brutos não são versionados no Git. Para executar o módulo, baixe pelo menos os seguintes arquivos:

```text
vitalPeriodic.csv.gz
lab.csv.gz
medication.csv.gz
```

Coloque-os dentro de:

```text
eicu-anomaly-detection/modulo_anomalias/data/raw/
```

A estrutura esperada é:

```text
eicu-anomaly-detection/modulo_anomalias/
└── data/
    └── raw/
        ├── vitalPeriodic.csv.gz
        ├── lab.csv.gz
        └── medication.csv.gz
```

---

## Limitações

* O eICU-CRD Demo é uma versão reduzida do dataset completo.
* O modelo é não supervisionado e não utiliza diagnóstico clínico como rótulo de treinamento.
* Um registro anômalo não representa necessariamente uma doença ou emergência.
* Os limites usados na descrição dos alertas têm finalidade acadêmica.
* O sistema ainda não foi validado por profissionais de saúde.
* O processamento atual é feito em lote, não em monitoramento hospitalar real.

---

## Observação importante

Este projeto tem finalidade exclusivamente acadêmica e demonstrativa.

Os alertas, scores e recomendações gerados pelo sistema não devem ser utilizados para diagnóstico, prescrição ou tomada de decisão médica sem validação clínica especializada.
