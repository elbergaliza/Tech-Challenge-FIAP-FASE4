# Tech-Challenge-FIAP-FASE4
Repo do Tech-Challenge-FIAP-FASE4 do grupo 57
# Módulo de Detecção de Anomalias Clínicas em UTI

Este módulo corresponde à parte de **detecção de anomalias clínicas** do Tech Challenge.

A proposta é utilizar o dataset **eICU-CRD Demo** para simular o monitoramento preventivo de pacientes em UTI, identificando padrões anormais em sinais vitais, exames laboratoriais e medicações.

## Objetivo

Detectar possíveis anomalias clínicas em pacientes de UTI a partir de dados estruturados, gerando alertas automáticos com:

* score de risco;
* nível de risco;
* tipo de anomalia;
* descrição do problema identificado;
* recomendação para a equipe médica.

## Dataset utilizado

Dataset: **eICU Collaborative Research Database Demo v2.0.1**

# Dataset

Esta pasta deve conter os arquivos do eICU-CRD Demo.

Baixe o dataset oficial em:

https://physionet.org/content/eicu-crd-demo/2.0.1/

Para executar o módulo de anomalias clínicas, coloque nesta pasta pelo menos:

- vitalPeriodic.csv.gz
- lab.csv.gz
- medication.csv.gz

Estrutura esperada:

data/raw/vitalPeriodic.csv.gz  
data/raw/lab.csv.gz  
data/raw/medication.csv.gz

## Como instalar as dependências

Criar o ambiente virtual:

```bash
python -m venv venv
```

Ativar o ambiente no Windows:

```bash
venv\Scripts\activate
```

Instalar as dependências:

```bash
pip install -r requirements.txt
```

## Como testar o carregamento dos dados

Para verificar se o dataset está certo, rodar:

```bash
python -m src.data_loader
```

Esse comando testa a leitura dos arquivos do eICU.

Resultado esperado:

```text
Arquivo vitalPeriodic carregado com sucesso!
Quantidade de linhas: ...
Quantidade de colunas: ...
Colunas encontradas:
...
```

Se esse teste funcionar, significa que o projeto está encontrando e lendo corretamente os arquivos do dataset.

## Como testar a criação das features

Depois de confirmar que os dados carregam, rodar:

```bash
python -m src.feature_builder
```

Esse comando transforma os dados brutos em variáveis agregadas por internação/paciente.

Exemplo de features criadas:

```text
heartrate_mean
heartrate_min
heartrate_max
sao2_mean
sao2_min
respiration_max
temperature_max
lab_creatinine_max
medication_vasoactive_count
medication_antibiotic_count
```

Essas features são usadas pelo modelo de detecção de anomalias.

## Como treinar o modelo

Para rodar o pipeline completo de treinamento:

```bash
python -m src.train
```

Esse comando executa as seguintes etapas:

1. carrega os dados do eICU;
2. cria features clínicas;
3. treina o modelo de detecção de anomalias;
4. gera predições;
5. gera alertas automáticos;
6. salva os resultados na pasta `outputs/`.

O modelo utilizado nesta versão é o **Isolation Forest**, aplicado sobre dados tabulares de sinais vitais, exames e medicações.

## Arquivos gerados

Após rodar o treinamento, os principais arquivos gerados são:

```text
data/processed/clinical_features.csv
models/clinical_anomaly_detector.joblib
outputs/predictions.csv
outputs/alerts.csv
outputs/alerts.json
```

Descrição dos arquivos:

```text
clinical_features.csv
Tabela com as variáveis clínicas criadas a partir dos dados brutos.

clinical_anomaly_detector.joblib
Modelo treinado de detecção de anomalias.

predictions.csv
Resultado do modelo para cada internação/paciente.

alerts.csv
Alertas gerados em formato CSV.

alerts.json
Alertas gerados em formato JSON, já no padrão esperado para integração futura.
```

## Como testar os resultados gerados

Depois de rodar o treinamento, é possível testar a saída com:

```bash
python -m src.test_output
```

Esse comando mostra:

* total de internações processadas;
* total de predições geradas;
* total de alertas gerados;
* distribuição dos níveis de risco;
* exemplos de alertas em CSV/JSON.

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

## Como interpretar a saída

O campo `score_risco` varia de 0 a 1:

```text
0.00 a 0.44 → baixo risco
0.45 a 0.74 → risco moderado
0.75 a 1.00 → alto risco
```

O campo `nivel_risco` classifica o alerta em:

```text
baixo
moderado
alto
```

O campo `descricao` explica os principais fatores associados à anomalia detectada.

O campo `recomendacao` apresenta uma sugestão de ação para a equipe médica.

## Integração futura com os outros módulos

Neste momento, este módulo funciona de forma independente.

Posteriormente, ele será integrado aos módulos de:

* vídeo/fisioterapia/postura;
* áudio/voz/respiração/texto.

A integração será feita no nível dos alertas e scores de risco.

Cada módulo deverá gerar uma saída padronizada contendo:

```json
{
  "sample_id": "identificador_da_amostra",
  "modulo": "nome_do_modulo",
  "tipo_anomalia": "tipo_de_anomalia_detectada",
  "score_risco": 0.0,
  "nivel_risco": "baixo/moderado/alto",
  "descricao": "descrição da anomalia detectada",
  "recomendacao": "ação sugerida"
}
```

Depois, os alertas dos módulos serão combinados em uma etapa de fusão multimodal para gerar um relatório final de monitoramento preventivo.

## Observação importante

Este projeto tem finalidade acadêmica e demonstrativa. Os alertas gerados pelo modelo não devem ser usados como recomendação médica real sem validação clínica especializada.
