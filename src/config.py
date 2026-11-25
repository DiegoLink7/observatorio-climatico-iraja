"""Parâmetros do recorte do projeto, definidos na AE1.

Para mudar a localidade, o período ou as variáveis, altere só este arquivo.
"""

from pathlib import Path

# Localidade
CIDADE_ID = "iraja-rj"  # identificador fixo da localidade; faz parte da chave primária
LOCALIDADE = "Irajá, Rio de Janeiro (RJ)"
LATITUDE = -22.8344
LONGITUDE = -43.3272
FUSO_HORARIO = "America/Sao_Paulo"

# Período: 30 dias consecutivos (datas inclusivas)
DATA_INICIO = "2026-10-15"
DATA_FIM = "2026-11-13"
DIAS_ESPERADOS = 30

# Variáveis diárias da API Open-Meteo e o nome que cada uma recebe na tabela
VARIAVEIS = {
    "temperature_2m_max": "temp_max_c",
    "temperature_2m_min": "temp_min_c",
    "precipitation_sum": "precipitacao_mm",
}

# Unidade esperada para cada variável na resposta (bloco daily_units)
UNIDADES_ESPERADAS = {
    "temperature_2m_max": "°C",
    "temperature_2m_min": "°C",
    "precipitation_sum": "mm",
}

# Faixas plausíveis para o Rio de Janeiro, usadas como alerta (ver plano de qualidade)
FAIXA_TEMPERATURA_C = (0.0, 45.0)
FAIXA_PRECIPITACAO_MM = (0.0, 350.0)

# Fonte
URL_API = "https://archive-api.open-meteo.com/v1/archive"
FONTE = "Open-Meteo Historical Weather API"

# Critério de "dia com chuva" usado nas análises (mm)
LIMIAR_CHUVA_MM = 1.0

# Caminhos (sempre relativos à raiz do repositório)
RAIZ = Path(__file__).resolve().parent.parent
PASTA_BRUTOS = RAIZ / "dados" / "brutos"
PASTA_PROCESSADOS = RAIZ / "dados" / "processados"
ARQUIVO_JSON = PASTA_BRUTOS / f"openmeteo_iraja_{DATA_INICIO}_{DATA_FIM}.json"
ARQUIVO_METADADOS = PASTA_BRUTOS / f"coleta_metadados_{DATA_INICIO}_{DATA_FIM}.json"
ARQUIVO_CSV = PASTA_PROCESSADOS / "clima_diario.csv"
ARQUIVO_VALIDACAO = PASTA_PROCESSADOS / "relatorio_validacao.txt"
ARQUIVO_BANCO = PASTA_PROCESSADOS / "observatorio.duckdb"
ARQUIVO_SQL = RAIZ / "sql" / "consultas.sql"
