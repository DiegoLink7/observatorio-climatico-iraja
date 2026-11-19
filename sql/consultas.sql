-- Consultas do Observatório Climático Local (Irajá, RJ)
-- Banco: dados/processados/observatorio.duckdb | Tabela: clima_diario
-- Critério de dia com chuva: precipitação diária >= 1,0 mm
-- Para rodar todas: python src/analise.py

-- [Q0] Conferência da tabela: registros, período coberto e ausentes
SELECT
    COUNT(*)                                  AS registros,
    COUNT(DISTINCT data)                      AS datas_distintas,
    MIN(data)                                 AS primeira_data,
    MAX(data)                                 AS ultima_data,
    COUNT(*) - COUNT(temp_max_c)              AS ausentes_temp_max,
    COUNT(*) - COUNT(temp_min_c)              AS ausentes_temp_min,
    COUNT(*) - COUNT(precipitacao_mm)         AS ausentes_precipitacao
FROM clima_diario;

-- [P1] Qual foi a maior temperatura máxima do período e em que dia ela ocorreu?
-- KPI 1: temperatura máxima absoluta (°C)
SELECT
    data,
    temp_max_c AS temperatura_maxima_absoluta_c
FROM clima_diario
WHERE temp_max_c = (SELECT MAX(temp_max_c) FROM clima_diario)
ORDER BY data;

-- [P2a] Quanto choveu no total no período?
-- KPI 2: precipitação acumulada (mm)
SELECT
    ROUND(SUM(precipitacao_mm), 1) AS precipitacao_acumulada_mm,
    COUNT(precipitacao_mm)         AS dias_com_dado
FROM clima_diario;

-- [P2b] Quais foram os 5 dias mais chuvosos?
SELECT
    RANK() OVER (ORDER BY precipitacao_mm DESC) AS posicao,
    data,
    precipitacao_mm
FROM clima_diario
WHERE precipitacao_mm IS NOT NULL
ORDER BY precipitacao_mm DESC, data
LIMIT 5;

-- [P3a] Quantos dias tiveram chuva (>= 1,0 mm)?
-- KPI 3: número de dias com chuva (dias)
SELECT
    COUNT(*) FILTER (WHERE precipitacao_mm >= 1.0) AS dias_com_chuva,
    COUNT(*) FILTER (WHERE precipitacao_mm < 1.0)  AS dias_sem_chuva,
    COUNT(*) FILTER (WHERE precipitacao_mm IS NULL) AS dias_sem_dado
FROM clima_diario;

-- [P3b] A temperatura máxima média foi diferente entre dias com e sem chuva?
SELECT
    CASE WHEN precipitacao_mm >= 1.0 THEN 'com chuva (>= 1,0 mm)'
         ELSE 'sem chuva (< 1,0 mm)' END   AS grupo,
    COUNT(*)                               AS dias,
    ROUND(AVG(temp_max_c), 1)              AS media_temp_max_c,
    ROUND(AVG(temp_min_c), 1)              AS media_temp_min_c
FROM clima_diario
WHERE precipitacao_mm IS NOT NULL
GROUP BY grupo
ORDER BY grupo;

-- [R1] Resumo dos indicadores para o relatório e o painel
SELECT
    MAX(temp_max_c)                                  AS kpi1_temp_max_absoluta_c,
    ROUND(SUM(precipitacao_mm), 1)                   AS kpi2_precipitacao_acumulada_mm,
    COUNT(*) FILTER (WHERE precipitacao_mm >= 1.0)   AS kpi3_dias_com_chuva,
    MIN(temp_min_c)                                  AS menor_temp_min_c,
    ROUND(AVG(temp_max_c - temp_min_c), 1)           AS amplitude_termica_media_c
FROM clima_diario;
