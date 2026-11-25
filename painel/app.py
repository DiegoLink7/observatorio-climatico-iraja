"""Painel do Observatório Climático Local (Irajá, RJ).

O painel só lê o banco DuckDB. Ele não chama a API nem recria o banco, porque o
Streamlit reexecuta o script inteiro a cada interação. Antes de abrir o painel,
rode na raiz do repositório:

    python src/coleta.py
    python src/banco.py

Para abrir:

    streamlit run painel/app.py
"""

from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_BANCO = RAIZ / "dados" / "processados" / "observatorio.duckdb"
LIMIAR_CHUVA_MM = 1.0
DIAS_DO_PERIODO = 30

st.set_page_config(page_title="Observatório Climático Local: Irajá (RJ)", layout="wide")


def numero(valor, casas: int = 1) -> str:
    """Formata no padrão brasileiro (vírgula decimal)."""
    return f"{valor:.{casas}f}".replace(".", ",")


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    con = duckdb.connect(str(ARQUIVO_BANCO), read_only=True)
    df = con.sql(
        """
        SELECT data, temp_max_c, temp_min_c, precipitacao_mm, dia_com_chuva,
               localidade, fonte, coletado_em
        FROM clima_diario
        ORDER BY data
        """
    ).df()
    con.close()
    df["data"] = pd.to_datetime(df["data"])
    return df


# ---------------------------------------------------------------- dados
if not ARQUIVO_BANCO.exists():
    st.error(
        "Banco não encontrado em dados/processados/observatorio.duckdb. "
        "Rode antes, na raiz do repositório: python src/coleta.py e python src/banco.py"
    )
    st.stop()

dados = carregar_dados()
if dados.empty:
    st.error("A tabela clima_diario está vazia. Rode python src/banco.py e abra o painel de novo.")
    st.stop()

inicio, fim = dados["data"].min(), dados["data"].max()
coletado_em = pd.to_datetime(dados["coletado_em"].iloc[0])

# ---------------------------------------------------------------- barra lateral
st.sidebar.header("Filtros")
intervalo = st.sidebar.date_input(
    "Intervalo de datas (gráficos e tabela)",
    value=(inicio.date(), fim.date()),
    min_value=inicio.date(),
    max_value=fim.date(),
    format="DD/MM/YYYY",
)
so_chuva = st.sidebar.checkbox("Mostrar na tabela só dias com chuva")
st.sidebar.caption(
    "Os filtros mudam só os gráficos e a tabela. Os três indicadores do topo "
    "valem sempre para o período inteiro."
)
st.sidebar.header("Sobre os dados")
st.sidebar.markdown(
    "- Fonte: Open-Meteo (API histórica)\n"
    "- Dado de modelo meteorológico, não de estação em Irajá\n"
    "- Unidades: °C e mm\n"
    f"- Coleta: {coletado_em:%d/%m/%Y às %H:%M}"
)

if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
    de, ate = pd.Timestamp(intervalo[0]), pd.Timestamp(intervalo[1])
else:
    de, ate = inicio, fim
filtrado = dados[(dados["data"] >= de) & (dados["data"] <= ate)]

# ---------------------------------------------------------------- título e contexto
st.title("Observatório Climático Local: Irajá (RJ)")
st.markdown(
    f"Como foram o calor e a chuva em Irajá, Zona Norte do Rio de Janeiro, "
    f"entre **{inicio:%d/%m/%Y}** e **{fim:%d/%m/%Y}** ({len(dados)} dias)."
)

# ---------------------------------------------------------------- indicadores
dias_tmax = int(dados["temp_max_c"].notna().sum())
dias_chuva_dado = int(dados["precipitacao_mm"].notna().sum())
col1, col2, col3 = st.columns(3)

if dias_tmax:
    linha_max = dados.loc[dados["temp_max_c"].idxmax()]
    nota = "" if dias_tmax == DIAS_DO_PERIODO else f" · calculado com {dias_tmax} de {DIAS_DO_PERIODO} dias"
    col1.metric(
        "Maior temperatura máxima",
        f"{numero(linha_max['temp_max_c'])} °C",
        help="Maior valor de temperatura máxima diária no período (KPI 1).",
    )
    col1.caption(f"em {linha_max['data']:%d/%m/%Y}{nota}")
else:
    col1.metric("Maior temperatura máxima", "sem dado")

if dias_chuva_dado:
    nota = "" if dias_chuva_dado == DIAS_DO_PERIODO else f" · {dias_chuva_dado} de {DIAS_DO_PERIODO} dias com dado"
    col2.metric(
        "Chuva acumulada",
        f"{numero(dados['precipitacao_mm'].sum())} mm",
        help="Soma da chuva diária dos dias com dado (KPI 2). Dia sem dado não conta como zero.",
    )
    col2.caption(f"soma de todos os dias{nota}")

    dias_com_chuva = int(dados["dia_com_chuva"].fillna(False).astype(bool).sum())
    sem_dado = int(dados["dia_com_chuva"].isna().sum())
    col3.metric(
        "Dias com chuva",
        f"{dias_com_chuva} dias",
        help="Dias com 1,0 mm de chuva ou mais (KPI 3).",
    )
    col3.caption(
        f"com 1,0 mm ou mais · {len(dados) - dias_com_chuva - sem_dado} dias sem chuva"
        + (f" · {sem_dado} sem dado" if sem_dado else "")
    )
else:
    col2.metric("Chuva acumulada", "sem dado")
    col3.metric("Dias com chuva", "sem dado")

st.divider()

# ---------------------------------------------------------------- gráficos
g1, g2 = st.columns(2)

temperaturas = filtrado.melt(
    id_vars="data",
    value_vars=["temp_max_c", "temp_min_c"],
    var_name="serie",
    value_name="valor",
).dropna(subset=["valor"])
temperaturas["serie"] = temperaturas["serie"].map(
    {"temp_max_c": "Máxima (°C)", "temp_min_c": "Mínima (°C)"}
)
grafico_temp = (
    alt.Chart(temperaturas)
    .mark_line(point=True)
    .encode(
        x=alt.X("data:T", title="Data", axis=alt.Axis(format="%d/%m")),
        y=alt.Y("valor:Q", title="Temperatura (°C)", scale=alt.Scale(zero=False)),
        color=alt.Color(
            "serie:N",
            title=None,
            scale=alt.Scale(domain=["Máxima (°C)", "Mínima (°C)"], range=["#c0504d", "#4a6fa5"]),
            legend=alt.Legend(orient="top"),
        ),
        strokeDash=alt.StrokeDash(
            "serie:N",
            scale=alt.Scale(domain=["Máxima (°C)", "Mínima (°C)"], range=[[1, 0], [6, 3]]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("data:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip("serie:N", title="Série"),
            alt.Tooltip("valor:Q", title="°C", format=".1f"),
        ],
    )
    .properties(height=320)
)
with g1:
    st.subheader("Temperatura máxima e mínima por dia")
    st.altair_chart(grafico_temp, width="stretch")

chuva = filtrado.dropna(subset=["precipitacao_mm"]).copy()
chuva["tipo"] = chuva["dia_com_chuva"].map(
    {True: "Com chuva", False: "Sem chuva"}
)
barras = (
    alt.Chart(chuva)
    .mark_bar()
    .encode(
        x=alt.X("data:T", title="Data", axis=alt.Axis(format="%d/%m")),
        y=alt.Y("precipitacao_mm:Q", title="Chuva no dia (mm)"),
        color=alt.Color(
            "tipo:N",
            title=None,
            scale=alt.Scale(
                domain=["Com chuva", "Sem chuva"],
                range=["#4a6fa5", "#b9c7da"],
            ),
            legend=alt.Legend(orient="top"),
        ),
        tooltip=[
            alt.Tooltip("data:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip("precipitacao_mm:Q", title="mm", format=".1f"),
        ],
    )
)
limiar = (
    alt.Chart(pd.DataFrame({"y": [LIMIAR_CHUVA_MM]}))
    .mark_rule(color="#b04a00", strokeDash=[5, 4])
    .encode(y="y:Q")
)
with g2:
    st.subheader("Chuva por dia")
    st.altair_chart((barras + limiar).properties(height=320), width="stretch")
    st.caption("A linha tracejada marca 1,0 mm. Conta como dia com chuva aquele que chegou a esse valor ou passou dele.")

# ---------------------------------------------------------------- tabela
st.subheader("Dados dia a dia")
tabela = filtrado.copy()
if so_chuva:
    tabela = tabela[tabela["dia_com_chuva"].fillna(False).astype(bool)]
tabela = pd.DataFrame(
    {
        "Data": tabela["data"].dt.strftime("%d/%m/%Y"),
        "Máxima (°C)": tabela["temp_max_c"].map(lambda v: "" if pd.isna(v) else numero(v)),
        "Mínima (°C)": tabela["temp_min_c"].map(lambda v: "" if pd.isna(v) else numero(v)),
        "Chuva (mm)": tabela["precipitacao_mm"].map(lambda v: "" if pd.isna(v) else numero(v)),
        "Dia com chuva": tabela["dia_com_chuva"].map({True: "sim", False: "não"}).fillna("sem dado"),
    }
)
st.dataframe(
    tabela,
    hide_index=True,
    width="stretch",
)
st.caption(f"{len(tabela)} dias exibidos. Campo vazio quer dizer dado ausente, nunca zero.")

# ---------------------------------------------------------------- como ler e limitações
with st.expander("Como ler estes números e quais são os limites"):
    st.markdown(
        """
- **Maior temperatura máxima:** o dia mais quente do período e quando ele aconteceu.
- **Chuva acumulada:** quanto choveu somando todos os dias. Compare com o gráfico de chuva
  para ver se ela veio espalhada ou concentrada em poucos dias.
- **Dias com chuva:** quantos dias tiveram 1,0 mm de chuva ou mais.

Limites desta análise:

- Mostra dias que **já passaram**. Não é previsão do tempo e não substitui os alertas da Defesa Civil.
- Os dados vêm de um **modelo meteorológico** do Open-Meteo, calculado para um ponto a cerca
  de 3 km do centro de Irajá. Não são medições de uma estação no bairro e podem diferir do que
  um termômetro ou pluviômetro na rua marcaria.
- **30 dias** mostram um retrato do período. Não servem para falar em tendência climática.
- Os gráficos mostram o que aconteceu junto, não o que causou o quê.
        """
    )

# ---------------------------------------------------------------- rodapé
st.divider()
st.caption(
    "Fonte: Open-Meteo Historical Weather API · temperatura em °C a 2 m do solo · "
    "chuva em mm por dia · código e dados: github.com/DiegoLink7/observatorio-climatico-iraja"
)
