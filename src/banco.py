"""Trata, valida e carrega os dados coletados no banco DuckDB.

Segue o dicionário de dados, o modelo lógico e o plano de qualidade da AE2-2
(docs/escopo-1/AE2-2). Os códigos Q1 a Q12 nas mensagens são as checagens do plano.

Etapas:
1. Lê o JSON original de dados/brutos/ (o arquivo não é alterado).
2. Confere a estrutura e as unidades da resposta (Q1).
3. Monta um DataFrame do pandas, padroniza nomes e converte tipos.
4. Roda as checagens de qualidade e grava o relatório de validação.
5. Grava a base tratada em CSV.
6. Carrega a tabela clima_diario no DuckDB.

A chave primária é (cidade_id, data) e a carga usa INSERT OR REPLACE.
Rodar o script várias vezes atualiza as mesmas linhas e não cria duplicados.

Uso:
    python src/banco.py
"""

import json
import sys

import duckdb
import pandas as pd

import config

COLUNAS_TABELA = [
    "cidade_id",
    "data",
    "localidade",
    "latitude_grade",
    "longitude_grade",
    "temp_max_c",
    "temp_min_c",
    "precipitacao_mm",
    "dia_com_chuva",
    "fonte",
    "coletado_em",
]
OBRIGATORIOS = ["cidade_id", "data", "localidade", "fonte", "coletado_em"]
VARIAVEIS = list(config.VARIAVEIS.values())


def ler_json() -> dict:
    if not config.ARQUIVO_JSON.exists():
        print("JSON da coleta não encontrado. Rode antes: python src/coleta.py")
        sys.exit(1)
    return json.loads(config.ARQUIVO_JSON.read_text(encoding="utf-8"))


def ler_data_coleta():
    if config.ARQUIVO_METADADOS.exists():
        meta = json.loads(config.ARQUIVO_METADADOS.read_text(encoding="utf-8"))
        return meta.get("coletado_em")
    return None


def checar_estrutura(bruto: dict) -> list[str]:
    """Q1: a resposta tem o bloco daily, todas as variáveis e as unidades esperadas."""
    problemas = []
    diario = bruto.get("daily", {})
    unidades = bruto.get("daily_units", {})
    for campo in ["time", *config.VARIAVEIS.keys()]:
        if campo not in diario:
            problemas.append(f"campo '{campo}' ausente no bloco daily")
    for campo, esperada in config.UNIDADES_ESPERADAS.items():
        recebida = unidades.get(campo)
        if recebida != esperada:
            problemas.append(f"unidade de '{campo}': esperada {esperada}, recebida {recebida}")
    return problemas


def montar_dataframe(bruto: dict) -> pd.DataFrame:
    df = pd.DataFrame(bruto["daily"])

    # Padroniza nomes: "time" vira "data" e as variáveis ganham nome com unidade
    df = df.rename(columns={"time": "data", **config.VARIAVEIS})
    df = df[["data", *VARIAVEIS]]

    # Tipos: data como datetime; variáveis como número (texto inválido vira NaN)
    df["data_texto"] = df["data"]
    df["data"] = pd.to_datetime(df["data"], format="%Y-%m-%d", errors="coerce")
    for coluna in VARIAVEIS:
        df[f"{coluna}_texto"] = df[coluna]
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    # Campos de configuração e da resposta
    df["cidade_id"] = config.CIDADE_ID
    df["localidade"] = config.LOCALIDADE
    df["latitude_grade"] = bruto.get("latitude")
    df["longitude_grade"] = bruto.get("longitude")
    df["fonte"] = config.FONTE

    # coletado_em: horário local de São Paulo, sem fuso, como TIMESTAMP
    coleta = ler_data_coleta()
    if coleta:
        momento = pd.Timestamp(coleta)
        if momento.tzinfo is not None:
            momento = momento.tz_convert(config.FUSO_HORARIO).tz_localize(None)
        df["coletado_em"] = momento
    else:
        df["coletado_em"] = pd.NaT

    # Campo calculado: dia com chuva (>= limiar). Fica vazio se a chuva estiver ausente.
    df["dia_com_chuva"] = (df["precipitacao_mm"] >= config.LIMIAR_CHUVA_MM).astype("boolean")
    df.loc[df["precipitacao_mm"].isna(), "dia_com_chuva"] = pd.NA
    return df


def listar(log: list[str], datas) -> None:
    for d in datas:
        log.append(f"      - {pd.Timestamp(d).date()}")


def validar(df: pd.DataFrame, bruto: dict) -> tuple[pd.DataFrame, list[str], bool]:
    """Roda as checagens Q2 a Q11. Devolve o DataFrame, o log e se a carga pode seguir."""
    log = []
    pode_carregar = True
    log.append(f"Fonte: {config.FONTE}")
    log.append(f"Localidade: {config.LOCALIDADE} (cidade_id = {config.CIDADE_ID})")
    log.append(f"Coordenadas pedidas: {config.LATITUDE}, {config.LONGITUDE}")
    log.append(
        f"Ponto de grade devolvido pela API: {bruto.get('latitude')}, {bruto.get('longitude')}"
    )
    log.append(f"Período pedido: {config.DATA_INICIO} a {config.DATA_FIM}")
    log.append(f"Coleta feita em: {ler_data_coleta()}")
    log.append("")
    log.append("[Q1] Estrutura e unidades da resposta: OK")

    # Q2. Campos obrigatórios
    vazios = {c: int(df[c].isna().sum()) for c in OBRIGATORIOS if c != "data"}
    log.append(f"[Q2] Campos obrigatórios vazios (exceto data): {vazios}")
    if any(vazios.values()):
        pode_carregar = False
        log.append("    Ação: carga interrompida. Corrigir a configuração ou os metadados da coleta.")

    # Q3. Datas válidas
    invalidas = df.loc[df["data"].isna(), "data_texto"].tolist()
    log.append(f"[Q3] Datas que não puderam ser convertidas: {len(invalidas)} {invalidas or ''}")
    if invalidas:
        df = df.dropna(subset=["data"])
        log.append("    Ação: linhas sem data válida descartadas.")

    # Q4. Datas dentro do recorte
    esperadas = pd.date_range(config.DATA_INICIO, config.DATA_FIM, freq="D")
    fora = df.loc[~df["data"].isin(esperadas), "data"]
    log.append(f"[Q4] Datas fora do período: {len(fora)}")
    listar(log, fora)
    if len(fora):
        df = df[df["data"].isin(esperadas)]
        log.append("    Ação: datas fora do período descartadas.")

    # Q5. Duplicidade de (cidade_id, data)
    dup = df.duplicated(subset=["cidade_id", "data"], keep="first")
    log.append(f"[Q5] Registros duplicados para a mesma cidade_id + data: {int(dup.sum())}")
    listar(log, df.loc[dup, "data"])
    if dup.any():
        df = df[~dup]
        log.append("    Ação: mantida a primeira ocorrência; investigar a origem antes da análise.")

    # Q6. Cobertura dos 30 dias consecutivos
    faltando = esperadas.difference(df["data"])
    log.append(
        f"[Q6] Registros: {len(df)} (esperados: {config.DIAS_ESPERADOS}); "
        f"datas do período sem registro: {len(faltando)}"
    )
    listar(log, faltando)
    if len(faltando):
        log.append("    Ação: nenhum dia é inventado. Avaliar nova coleta ou deslocar o período.")

    # Q7 e Q8. Ausências e tipos numéricos
    log.append("[Q7/Q8] Valores ausentes por variável (NULL, nunca zero):")
    for coluna in VARIAVEIS:
        ausentes = df[coluna].isna()
        texto_original = df.loc[ausentes, f"{coluna}_texto"]
        nao_numericos = texto_original.notna().sum()
        log.append(
            f"    {coluna}: {int(ausentes.sum())} ausentes "
            f"({int(nao_numericos)} por texto não numérico)"
        )
        listar(log, df.loc[ausentes, "data"])

    # Q9. Mínima não superior à máxima
    invertidas = df.loc[df["temp_min_c"] > df["temp_max_c"], "data"]
    log.append(f"[Q9] Dias com temperatura mínima maior que a máxima: {len(invertidas)}")
    listar(log, invertidas)

    # Q10. Precipitação não negativa
    negativas = df.loc[df["precipitacao_mm"] < 0, "data"]
    log.append(f"[Q10] Dias com precipitação negativa: {len(negativas)}")
    listar(log, negativas)

    # Q11. Faixas plausíveis
    tmin, tmax = config.FAIXA_TEMPERATURA_C
    pmin, pmax = config.FAIXA_PRECIPITACAO_MM
    fora_faixa = df[
        (df["temp_max_c"].notna() & ~df["temp_max_c"].between(tmin, tmax))
        | (df["temp_min_c"].notna() & ~df["temp_min_c"].between(tmin, tmax))
        | (df["precipitacao_mm"].notna() & ~df["precipitacao_mm"].between(pmin, pmax))
    ]
    log.append(
        f"[Q11] Dias fora da faixa plausível (temperatura {tmin} a {tmax} °C, "
        f"chuva {pmin} a {pmax} mm): {len(fora_faixa)}"
    )
    listar(log, fora_faixa["data"])
    if len(invertidas) or len(negativas) or len(fora_faixa):
        log.append(
            "    Ação: registros mantidos e listados para conferência no JSON original "
            "antes da análise."
        )

    log.append("")
    tudo_ok = (
        pode_carregar
        and len(df) == config.DIAS_ESPERADOS
        and len(faltando) == 0
        and not df[VARIAVEIS].isna().any().any()
        and len(invertidas) == 0
        and len(negativas) == 0
        and len(fora_faixa) == 0
    )
    log.append(f"Situação final: {'OK' if tudo_ok else 'COM PENDÊNCIAS (ver itens acima)'}")
    df = df.sort_values("data").reset_index(drop=True)[COLUNAS_TABELA]
    return df, log, pode_carregar


def criar_tabela(con: duckdb.DuckDBPyConnection) -> None:
    """Cria a tabela do modelo lógico v1. Recria se encontrar a versão antiga (sem cidade_id)."""
    existe = con.sql(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = 'clima_diario' AND column_name = 'cidade_id'"
    ).fetchall()[0][0]
    antiga = con.sql(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'clima_diario'"
    ).fetchall()[0][0]
    if antiga and not existe:
        print("Tabela clima_diario na versão antiga (sem cidade_id): recriando no modelo v1.")
        con.sql("DROP TABLE clima_diario")

    con.sql(
        """
        CREATE TABLE IF NOT EXISTS clima_diario (
            cidade_id        VARCHAR   NOT NULL,
            data             DATE      NOT NULL,
            localidade       VARCHAR   NOT NULL,
            latitude_grade   DOUBLE,
            longitude_grade  DOUBLE,
            temp_max_c       DOUBLE,
            temp_min_c       DOUBLE,
            precipitacao_mm  DOUBLE,
            dia_com_chuva    BOOLEAN,
            fonte            VARCHAR   NOT NULL,
            coletado_em      TIMESTAMP NOT NULL,
            PRIMARY KEY (cidade_id, data)
        )
        """
    )


def carregar(df: pd.DataFrame) -> None:
    con = duckdb.connect(str(config.ARQUIVO_BANCO))
    criar_tabela(con)
    antes = con.sql("SELECT COUNT(*) FROM clima_diario").fetchall()[0][0]

    carga = df.copy()
    carga["data"] = carga["data"].dt.date
    con.register("carga", carga)
    colunas = ", ".join(COLUNAS_TABELA)
    con.sql(f"INSERT OR REPLACE INTO clima_diario ({colunas}) SELECT {colunas} FROM carga")
    depois = con.sql("SELECT COUNT(*) FROM clima_diario").fetchall()[0][0]
    con.unregister("carga")
    con.close()

    # Q12. Carga sem duplicação
    print(f"[Q12] Linhas na tabela clima_diario antes da carga: {antes}")
    print(f"[Q12] Linhas na tabela clima_diario depois da carga: {depois}")


def main() -> None:
    bruto = ler_json()

    problemas = checar_estrutura(bruto)
    if problemas:
        print("[Q1] Estrutura ou unidades inesperadas. Nada foi carregado:")
        for p in problemas:
            print(f"    - {p}")
        sys.exit(1)

    df = montar_dataframe(bruto)
    df, log, pode_carregar = validar(df, bruto)

    config.PASTA_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    saida = df.copy()
    saida["data"] = saida["data"].dt.strftime("%Y-%m-%d")
    saida.to_csv(config.ARQUIVO_CSV, index=False)
    config.ARQUIVO_VALIDACAO.write_text("\n".join(log) + "\n", encoding="utf-8")

    print("\n".join(log))
    print()
    print(f"Base tratada: {config.ARQUIVO_CSV.relative_to(config.RAIZ)}")
    print(f"Relatório de validação: {config.ARQUIVO_VALIDACAO.relative_to(config.RAIZ)}")

    if not pode_carregar:
        print("Carga interrompida por falha em campo obrigatório (Q2).")
        sys.exit(1)
    carregar(df)
    print(f"Banco: {config.ARQUIVO_BANCO.relative_to(config.RAIZ)}")


if __name__ == "__main__":
    main()
