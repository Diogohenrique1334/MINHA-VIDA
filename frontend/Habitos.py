from PIL import Image
from pathlib import Path
import streamlit as st
import numpy as np

from utils.tratamente_dados import preparar_df
from utils.dados import carregar_dados as _carregar_dados, carregar_habitos_meta
from utils.filtros import render_filtros, USUARIO_PARA_TELEFONE
from utils.estilos import inject_css, cabecalho_secao, linha_kpis

# Gráficos e transformadores vêm do Baltazar (fonte única).
from baltazar.graficos.graficos_streamlit.graficos import (
    liquid_fill, barras_simples, barras_drilldown,
    barras_empilhadas_horizontais, mapa_correlacao, grefico_calendario,
)
from baltazar.graficos.graficos_streamlit.transformadores import (
    serei_semana_mes_complexo, dados_grafico_barras, get_delta,
    serie_temporal_dia_semana_complexo, serei_mes_ano_options, top_10_categorias,
)

ACCENT = "#18990b"


@st.cache_data(ttl=600)
def carregar_dados():
    return _carregar_dados()


@st.cache_data(ttl=600)
def carregar_meta():
    return carregar_habitos_meta()


@st.cache_data(ttl=600)
def dados_tratados(_df):
    return preparar_df(_df)


df = dados_tratados(carregar_dados())

imagem = Image.open(Path(__file__).parent / "foto_diogo.jpg")

st.set_page_config(layout="wide", page_title='Análise da vida')
inject_css()

# - Filtros (usuário / mês / hora) -----------------------
df_filtrado, usuario = render_filtros(df, key_prefix="main_", imagem=imagem)
st.success(f"Análise da vida de {usuario}")

# Categorias e hipercategorias vêm do banco (tabela habitos), do usuário selecionado.
meta = carregar_meta()
telefone = USUARIO_PARA_TELEFONE.get(usuario)
meta_user = meta[meta.user_phone_number == telefone].sort_values('ordem')
Hiper_categoria = dict(zip(meta_user['nome'], meta_user['categoria']))
categorias1 = np.array([nome for nome in meta_user['nome'] if nome in df_filtrado.columns])

categoria = st.sidebar.multiselect('Selecione as categorias da análise', categorias1, key="main_cat")
categorias = categoria if categoria else categorias1

Hcategoria = st.sidebar.multiselect(
    'Selecione a hiper categoria',
    df_filtrado[categorias].rename(columns=Hiper_categoria).columns.unique(),
    key="main_hcat",
)
if Hcategoria:
    categorias = {k: v for k, v in Hiper_categoria.items() if v in Hcategoria}.keys()

# - Métricas (KPIs estilizados) -------------------------

serie_temporal = df_filtrado[categorias1].reset_index().melt("Data")
serie_temporal_total = df_filtrado[categorias].reset_index().melt("Data")


def _agg_semanal(df_melted):
    return df_melted.pivot_table(
        index=[df_melted.Data.dt.isocalendar()['year'], df_melted.Data.dt.isocalendar()['week']],
        values='value', aggfunc='mean'
    )


def _kpi(df_melted, label):
    _t = _agg_semanal(df_melted)
    if _t.empty:
        return {"label": label, "valor": "-", "sub": None}
    val = _t.value.mean()
    sub = get_delta(_t.tail(1).value.values[0], val)
    # série semanal alimenta a mini timeline (sparkline) do box
    return {"label": label, "valor": f"{val:0,.0%}", "sub": sub, "serie": _t.value.tolist()}


_por_hiper = serie_temporal[serie_temporal.variable.map(Hiper_categoria) == "Saúde do corpo"]
_lazer = serie_temporal[serie_temporal.variable.map(Hiper_categoria) == "Lazer"]
_evolucao = serie_temporal[serie_temporal.variable.map(Hiper_categoria) == "Evolução pessoal"]

with st.container(border=True):
    linha_kpis([
        _kpi(serie_temporal_total, "Aderência Total"),
        _kpi(_por_hiper, "Saúde do corpo"),
        _kpi(_lazer, "Lazer"),
        _kpi(_evolucao, "Evolução pessoal"),
    ])

# - Visão geral --------------------------------

with st.container(border=True, height=380):
    pcol1, pcol2 = st.columns([2, 5])

    with pcol1.container(border=True, height=350):
        liquid_fill(valor=dados_grafico_barras(df_filtrado[categorias].melt(), 'variable', 'value', _agg="mean")[1], tamanho="300px")

    with pcol2.container(border=True, height=350):
        barras_simples(*dados_grafico_barras(df_filtrado[categorias].melt(), 'variable', 'value', _agg="mean"), cor=ACCENT)

    with st.container(border=True, height=350):
        _st = df_filtrado[categorias].reset_index().melt("Data")
        _st['Hiper_categoria'] = _st.variable.map(Hiper_categoria)
        barras_drilldown(*top_10_categorias(_st, "Hiper_categoria", 'variable', 'value', 'mean'))

# - Aderência por período ---------------------------

with st.container(border=True, height=540):
    cabecalho_secao('Aderência acumulada por categoria')
    col1, col2 = st.columns(2)

    with col1.container(border=True, height=450):
        barras_empilhadas_horizontais(*serie_temporal_dia_semana_complexo(serie_temporal_total, 'Data', 'value', 'variable', 'mean'), "400px")

    with col2.container(border=True, height=450):
        barras_empilhadas_horizontais(*serei_semana_mes_complexo(serie_temporal_total, 'Data', 'value', 'variable', 'mean'), "400px")

    with st.container(border=True, height=350):
        barras_empilhadas_horizontais(*serei_mes_ano_options(serie_temporal_total, 'Data', 'value', 'variable', 'mean'), "300px")

# - Correlação ---------------------------------

with st.container(border=True, height=450):
    cabecalho_secao('Correlação de Pearson das minhas tarefas')
    mapa_correlacao(df_filtrado, categorias=categorias, tamanho="400px")

# - Calendário ---------------------------------

with st.container(border=True):
    cabecalho_secao('Atividades realizadas por dia')
    cal_data = df_filtrado[list(categorias)].reset_index().melt("Data").dropna(subset=['value'])
    cal_data = cal_data.groupby('Data')['value'].sum().reset_index()
    grefico_calendario(cal_data)
