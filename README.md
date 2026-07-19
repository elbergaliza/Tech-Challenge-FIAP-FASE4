# Tech Challenge FIAP — Fase 4

Repositório do **Tech Challenge FIAP — Fase 4**, desenvolvido pelo Grupo 57.

O projeto propõe um sistema multimodal de monitoramento preventivo de pacientes, composto por módulos independentes de:

* análise de vídeo;
* análise de áudio e texto;
* detecção de anomalias clínicas;
* integração e fusão dos resultados.

---

# Módulo de Detecção de Anomalias Clínicas em UTI

O módulo está localizado na pasta:

```text
modulo_anomalias/
```

Ele corresponde à parte de **detecção de anomalias clínicas** do Tech Challenge.

A proposta é utilizar o dataset **eICU Collaborative Research Database Demo** para simular o monitoramento preventivo de pacientes em UTI, identificando padrões fora do comportamento esperado em:

* sinais vitais;
* exames laboratoriais;
* medicações;
* evolução clínica.

## Objetivo

Detectar possíveis anomalias clínicas em pacientes de UTI a partir de dados estruturados e gerar alertas automáticos contendo:

* score de risco;
* nível de risco;
* tipo de anomalia;
* descrição dos fatores encontrados;
* recomendação para a equipe médica.

---

## Estrutura do módulo

```text
Tech-Challenge-FIAP-FASE4/
│
├── adapters/                     # Adaptadores para fusão multimodal
│   ├── base.py
│   ├── clinical/                 # Adapter do módulo eICU
│   ├── video/                    # Adapter do módulo de vídeo
│   └── audio/                    # Adapter stub (futuro módulo de áudio)
│
├── eicu-anomaly-detection/       # Módulo clínico (eICU)
│   └── modulo_anomalias/
│       ├── data/
│       │   ├── raw/
│       │   └── processed/
│       ├── models/
│       ├── outputs/
│       └── src/
│           ├── config.py
│           ├── data_loader.py
│           ├── feature_builder.py
│           ├── anomaly_detector.py
│           ├── alert_generator.py
│           ├── train.py
│           └── test_output.py
│
├── fusion/                       # Motor de fusão multimodal
│   ├── core/
│   │   ├── fusion.py
│   │   └── schema.py
│   └── io.py
│
├── modulo_video/                 # Módulo de vídeo/fisioterapia
│   ├── src/
│   │   ├── pipeline.py
│   │   ├── pose_extractor.py
│   │   ├── biomechanics.py
│   │   ├── anomaly_detector.py
│   │   ├── risk_scoring.py
│   │   └── report.py
│   ├── config.py
│   └── data/
│       └── entrada/
│
├── main.py                       # CLI de orquestração
├── tests/                        # Testes unitários e E2E
│   ├── fixtures/
│   │   ├── mock_eicu/
│   │   └── test_video.mp4
│   ├── fusion/
│   └── test_e2e_mock.py
│
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

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

## Mock para testes locais e E2E

Para rodar a pipeline sem baixar o dataset real do PhysioNet, gere fixtures
sintéticas:

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

Depois execute a pipeline com os dados mockados:

```bash
python main.py \
  --video tests/fixtures/test_video.mp4 \
  --eicu-data tests/fixtures/mock_eicu \
  --video-patient-id local_test \
  --sem-objetos
```

Para rodar os testes E2E mockados:

```bash
pytest tests/test_e2e_mock.py -v
```

---

# Execução local

Os comandos abaixo devem ser executados a partir da raiz do repositório.

## 1. Criar o ambiente virtual

```bash
python -m venv venv
```

## 2. Ativar o ambiente virtual

No Windows:

```bash
venv\Scripts\activate
```

No Linux ou macOS:

```bash
source venv/bin/activate
```

## 3. Instalar as dependências

O `requirements.txt` na raiz contém as dependências unificadas para rodar a fusão multimodal (módulo clínico + vídeo + testes). O `pyproject.toml` registra os módulos internos como pacotes Python editáveis.

```bash
pip install -r requirements.txt
pip install -e .
```

> Se você for rodar apenas o módulo de vídeo de forma isolada, também é possível usar `pip install -r modulo_video/requirements.txt`. Para o módulo clínico isolado, basta o `requirements.txt` da raiz.

## 4. Entrar na pasta do módulo

```bash
cd eicu-anomaly-detection/modulo_anomalias
```

A partir deste ponto, os comandos devem ser executados dentro de `eicu-anomaly-detection/modulo_anomalias`.

---

## Testar o carregamento dos dados

Execute:

```bash
python -m src.data_loader
```

Esse comando verifica se os arquivos do eICU foram encontrados e se podem ser carregados corretamente.

Resultado esperado:

```text
Testando carregamento do eICU-CRD Demo...

Arquivo vitalPeriodic carregado com sucesso!
Quantidade de linhas: ...
Quantidade de colunas: ...

Colunas encontradas:
...
```

Se esse teste funcionar, significa que o módulo está encontrando e lendo corretamente os arquivos da pasta `data/raw/`.

---

## Testar a criação das features

Execute:

```bash
python -m src.feature_builder
```

Esse comando transforma os dados brutos em variáveis agregadas por internação, utilizando o identificador:

```text
patientunitstayid
```

Exemplos de features criadas:

```text
heartrate_mean
heartrate_min
heartrate_max
heartrate_std

sao2_mean
sao2_min
sao2_max

respiration_mean
respiration_max

temperature_mean
temperature_max

systemicsystolic_min

lab_creatinine_max
lab_glucose_max
lab_potassium_min

medication_total_count
medication_unique_count
medication_vasoactive_count
medication_antibiotic_count
medication_sedative_count
```

Essas features serão utilizadas pelo modelo de detecção de anomalias.

---

## Treinar o modelo

Execute:

```bash
python -m src.train
```

Esse comando executa o pipeline completo:

1. carrega os sinais vitais;
2. carrega os exames laboratoriais;
3. carrega os dados de medicação;
4. cria as features clínicas;
5. trata os valores ausentes;
6. treina o modelo de detecção de anomalias;
7. gera predições;
8. classifica os níveis de risco;
9. gera alertas automáticos;
10. salva os resultados.

O modelo utilizado nesta versão é o:

```text
Isolation Forest
```

O Isolation Forest é um algoritmo não supervisionado utilizado para encontrar registros com comportamento diferente do padrão predominante no conjunto de dados.

---

## Arquivos gerados

Após o treinamento, serão gerados:

```text
eicu-anomaly-detection/modulo_anomalias/data/processed/clinical_features.csv

eicu-anomaly-detection/modulo_anomalias/models/clinical_anomaly_detector.joblib

eicu-anomaly-detection/modulo_anomalias/outputs/predictions.csv
eicu-anomaly-detection/modulo_anomalias/outputs/alerts.csv
eicu-anomaly-detection/modulo_anomalias/outputs/alerts.json
```

### `clinical_features.csv`

Contém as variáveis clínicas criadas a partir dos dados brutos.

### `clinical_anomaly_detector.joblib`

Contém o modelo Isolation Forest treinado.

### `predictions.csv`

Contém o resultado do modelo para cada internação processada, incluindo:

* classificação normal ou anômala;
* score de risco;
* nível de risco.

### `alerts.csv`

Contém os alertas em formato tabular.

### `alerts.json`

Contém os alertas em formato JSON, preparado para integração futura com os outros módulos.

---

## Testar os resultados

Depois de executar o treinamento, rode:

```bash
python -m src.test_output
```

Esse comando apresenta:

* total de internações processadas;
* total de predições;
* total de alertas;
* distribuição dos níveis de risco;
* exemplos de alertas;
* exemplos da saída em JSON.

---

# Execução no Google Colab

No Colab, os comandos de terminal precisam começar com `!`.

Primeiro, entre na raiz do repositório:

```python
%cd /content/Tech-Challenge-FIAP-FASE4
```

Instale as dependências:

```python
!pip install -r requirements.txt
```

Depois, entre no módulo:

```python
%cd eicu-anomaly-detection/modulo_anomalias
```

Teste o carregamento:

```python
!python -m src.data_loader
```

Teste a criação das features:

```python
!python -m src.feature_builder
```

Treine o modelo:

```python
!python -m src.train
```

Visualize os resultados:

```python
!python -m src.test_output
```

> O caminho `/content/Tech-Challenge-FIAP-FASE4` deve ser adaptado caso o repositório tenha sido clonado com outro nome ou em outra localização.

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

# Fusão Multimodal

A integração entre os módulos é feita pelo `main.py` na raiz. Ele executa os
adapters de cada módulo e consolida os alertas em um único relatório JSON.

## Estrutura da integração

```text
Tech-Challenge-FIAP-FASE4/
├── adapters/
│   ├── clinical/          # adapter do módulo eICU
│   ├── video/             # adapter do módulo de vídeo
│   └── audio/             # adapter stub (futuro módulo de áudio)
├── fusion/
│   └── core/              # schema unificado + motor de fusão
├── main.py                # CLI de orquestração
├── tests/
│   └── fixtures/          # dados mockados para E2E
└── outputs/
    └── final_multimodal_report.json
```

## Como executar

### 1. Obter os dados

Você tem duas opções:

**Opção A — usar dados mockados (recomendado para testes locais):**

```bash
python tests/fixtures/generate_fixtures.py
```

Isso cria `tests/fixtures/mock_eicu/` e `tests/fixtures/test_video.mp4`.

**Opção B — baixar o eICU Demo real:**

Crie uma conta gratuita em https://physionet.org/, baixe os arquivos
`vitalPeriodic.csv.gz`, `lab.csv.gz` e `medication.csv.gz` do
[eICU Collaborative Research Database Demo v2.0.1](https://physionet.org/content/eicu-crd-demo/2.0.1/)
e coloque-os em:

```text
eicu-anomaly-detection/modulo_anomalias/data/raw/
```

### 2. Instalar as dependências

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

> O projeto foi validado com Python 3.12. O `requirements.txt` unificado cobre o módulo clínico, o módulo de vídeo e os testes. O `pip install -e .` registra os pacotes internos (`eicu_anomaly_detection`, `modulo_video`, `adapters`, `fusion`) como editáveis.

### 3. Gerar fixtures mockadas (dados de teste)

Para rodar a pipeline e os testes sem baixar o dataset real do PhysioNet:

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

### 4. Executar a fusão

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

### 5. Rodar os testes

```bash
pytest tests/ -v
```

> Os testes unitários não dependem das fixtures binárias. O teste E2E (`tests/test_e2e_mock.py`) gera as fixtures automaticamente na primeira execução, mas você pode gerá-las manualmente antes com `python tests/fixtures/generate_fixtures.py`.

### 6. Saída

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

1. Implementar `AudioAdapter.run()` em `adapters/audio/adapter.py`.
2. Adicionar `--audio` no `main.py`.
3. Registrar `AudioAdapter` no `MultimodalFusion`.

Nenhuma mudança é necessária no motor de fusão em `fusion/core/fusion.py`.

## Integração futura

Como os módulos utilizam datasets diferentes, os identificadores (`module_id`)
não representam necessariamente o mesmo paciente real. A fusão é uma
demonstração arquitetural de como diferentes fontes podem alimentar um
sistema central de monitoramento preventivo.

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
