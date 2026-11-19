"""Trata, valida e carrega os dados coletados no banco DuckDB.

Etapas:
1. Lê o JSON original de dados/brutos/ (o arquivo não é alterado).
2. Monta um DataFrame do pandas e padroniza os nomes das colunas.
3. Converte datas e números para os tipos corretos.
4. Valida: quantidade de registros, cobertura do período, datas duplicadas,
   valores ausentes e valores incoerentes.
5. Grava a base tratada em CSV e um relatório de validação em texto.
6. Carrega a tabela clima_diario no DuckDB.

A data é a chave primária da tabela e a carga usa INSERT OR REPLACE.
Rodar o script várias vezes atualiza as mesmas linhas e não cria duplicados.

Uso:
    python src/banco.py
"""

import json
import sys

import duckdb
import pandas as pd

import config

# Faixas de valores plausíveis para o Rio de Janeiro, usadas só como alerta
FAIXA_TEMPERATURA_C = (0.0, 45.0)
FAIXA_PRECIPITACAO_MM = (0.0, 300.0)


def ler_json() -> dict:
    if not config.ARQUIVO_JSON.exists():
        print("JSON da coleta não encontrado. Rode antes: python src/coleta.py")
        sys.exit(1)
    return json.loads(config.ARQUIVO_JSON.read_text(encoding="utf-8"))


def ler_data_coleta() -> str | None:
    if config.ARQUIVO_METADADOS.exists():
        meta = json.loads(config.ARQUIVO_METADADOS.read_text(encoding="utf-8"))
        return meta.get("coletado_em")
    return None


def montar_dataframe(bruto: dict) -> pd.DataFrame:
    df = pd.DataFrame(bruto["daily"])

    # Padroniza nomes: "time" vira "data" e as variáveis ganham nome com unidade
    df = df.rename(columns={"time": "data", **config.VARIAVEIS})
    colunas = ["data", *config.VARIAVEIS.values()]
    df = df[colunas]

    # Tipos: data como datetime; variáveis como número (texto inválido vira NaN)
    df["data"] = pd.to_datetime(df["data"], format="%Y-%m-%d", errors="coerce")
    for coluna in config.VARIAVEIS.values():
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    # Colunas de contexto: de onde veio cada linha
    df["localidade"] = config.LOCALIDADE
    df["latitude_grade"] = bruto.get("latitude")
    df["longitude_grade"] = bruto.get("longitude")
    df["fonte"] = config.FONTE
    df["coletado_em"] = ler_data_coleta()
    return df


def validar(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Valida e devolve o DataFrame pronto para a carga + as linhas do relatório."""
    log = []
    log.append(f"Fonte: {config.FONTE}")
    log.append(f"Localidade: {config.LOCALIDADE}")
    log.append(f"Coordenadas pedidas: {config.LATITUDE}, {config.LONGITUDE}")
    log.append(
        f"Ponto de grade devolvido pela API: {df['latitude_grade'].iloc[0]}, "
        f"{df['longitude_grade'].iloc[0]}"
    )
    log.append(f"Período pedido: {config.DATA_INICIO} a {config.DATA_FIM}")
    log.append(f"Coleta feita em: {df['coletado_em'].iloc[0]}")
    log.append("")

    # 1. Datas inválidas
    datas_invalidas = int(df["data"].isna().sum())
    log.append(f"[1] Datas que não puderam ser convertidas: {datas_invalidas}")
    if datas_invalidas:
        df = df.dropna(subset=["data"])
        log.append("    Decisão: linhas sem data válida foram descartadas.")

    # 2. Duplicidades
    duplicadas = int(df["data"].duplicated().sum())
    log.append(f"[2] Datas duplicadas: {duplicadas}")
    if duplicadas:
        df = df.drop_duplicates(subset=["data"], keep="first")
        log.append("    Decisão: mantida a primeira ocorrência de cada data.")

    # 3. Quantidade de registros e cobertura do período
    esperadas = pd.date_range(config.DATA_INICIO, config.DATA_FIM, freq="D")
    faltando = esperadas.difference(df["data"])
    fora = df.loc[~df["data"].isin(esperadas), "data"]
    log.append(
        f"[3] Registros: {len(df)} (esperados: {config.DIAS_ESPERADOS}); "
        f"de {df['data'].min().date()} a {df['data'].max().date()}"
    )
    log.append(f"    Datas do período sem registro: {len(faltando)}")
    for d in faltando:
        log.append(f"      - {d.date()}")
    log.append(f"    Datas fora do período: {len(fora)}")
    if len(fora):
        df = df[df["data"].isin(esperadas)]
        log.append("    Decisão: datas fora do período foram descartadas.")

    # 4. Valores ausentes (não são trocados por zero)
    log.append("[4] Valores ausentes por variável:")
    for coluna in config.VARIAVEIS.values():
        ausentes = df.loc[df[coluna].isna(), "data"]
        log.append(f"    {coluna}: {len(ausentes)}")
        for d in ausentes:
            log.append(f"      - {d.date()}")
    if df[list(config.VARIAVEIS.values())].isna().any().any():
        log.append(
            "    Decisão: ausentes ficam como NULL no banco. Trocar por zero "
            "inventaria um valor (0 mm de chuva ou 0 °C) que não foi medido."
        )

    # 5. Inconsistências
    invertidas = df.loc[df["temp_max_c"] < df["temp_min_c"], "data"]
    log.append(f"[5] Dias com temperatura máxima menor que a mínima: {len(invertidas)}")
    for d in invertidas:
        log.append(f"      - {d.date()}")
    negativas = df.loc[df["precipitacao_mm"] < 0, "data"]
    log.append(f"    Dias com precipitação negativa: {len(negativas)}")
    for d in negativas:
        log.append(f"      - {d.date()}")

    tmin, tmax = FAIXA_TEMPERATURA_C
    pmin, pmax = FAIXA_PRECIPITACAO_MM
    fora_faixa = df[
        ~df["temp_max_c"].between(tmin, tmax) & df["temp_max_c"].notna()
        | ~df["temp_min_c"].between(tmin, tmax) & df["temp_min_c"].notna()
        | ~df["precipitacao_mm"].between(pmin, pmax) & df["precipitacao_mm"].notna()
    ]
    log.append(
        f"    Dias com valor fora da faixa plausível "
        f"(temperatura {tmin} a {tmax} °C, chuva {pmin} a {pmax} mm): {len(fora_faixa)}"
    )
    if len(invertidas) or len(negativas) or len(fora_faixa):
        log.append(
            "    Decisão: os registros foram mantidos e listados acima para "
            "conferência manual antes da análise."
        )

    log.append("")
    situacao = (
        "OK"
        if len(df) == config.DIAS_ESPERADOS
        and len(faltando) == 0
        and not df[list(config.VARIAVEIS.values())].isna().any().any()
        and len(invertidas) == 0
        and len(negativas) == 0
        else "COM PENDÊNCIAS (ver itens acima)"
    )
    log.append(f"Situação final: {situacao}")
    return df.sort_values("data").reset_index(drop=True), log


def carregar(df: pd.DataFrame) -> None:
    con = duckdb.connect(str(config.ARQUIVO_BANCO))
    con.sql(
        """
        CREATE TABLE IF NOT EXISTS clima_diario (
            data             DATE PRIMARY KEY,
            temp_max_c       DOUBLE,
            temp_min_c       DOUBLE,
            precipitacao_mm  DOUBLE,
            localidade       VARCHAR NOT NULL,
            latitude_grade   DOUBLE,
            longitude_grade  DOUBLE,
            fonte            VARCHAR NOT NULL,
            coletado_em      VARCHAR
        )
        """
    )
    antes = con.sql("SELECT COUNT(*) FROM clima_diario").fetchall()[0][0]

    carga = df.copy()
    carga["data"] = carga["data"].dt.date
    con.register("carga", carga)
    con.sql(
        """
        INSERT OR REPLACE INTO clima_diario
        SELECT data, temp_max_c, temp_min_c, precipitacao_mm, localidade,
               latitude_grade, longitude_grade, fonte, coletado_em
        FROM carga
        """
    )
    depois = con.sql("SELECT COUNT(*) FROM clima_diario").fetchall()[0][0]
    con.unregister("carga")
    con.close()

    print(f"Linhas na tabela clima_diario antes da carga: {antes}")
    print(f"Linhas na tabela clima_diario depois da carga: {depois}")


def main() -> None:
    bruto = ler_json()
    df = montar_dataframe(bruto)
    df, log = validar(df)

    config.PASTA_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.ARQUIVO_CSV, index=False, date_format="%Y-%m-%d")
    config.ARQUIVO_VALIDACAO.write_text("\n".join(log) + "\n", encoding="utf-8")

    print("\n".join(log))
    print()
    print(f"Base tratada: {config.ARQUIVO_CSV.relative_to(config.RAIZ)}")
    print(f"Relatório de validação: {config.ARQUIVO_VALIDACAO.relative_to(config.RAIZ)}")

    carregar(df)
    print(f"Banco: {config.ARQUIVO_BANCO.relative_to(config.RAIZ)}")


if __name__ == "__main__":
    main()
