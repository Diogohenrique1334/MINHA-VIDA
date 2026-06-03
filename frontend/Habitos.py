import pandas as pd
from PIL import Image
from pathlib import Path
from streamlit_echarts import st_echarts
from utils.tratamente_dados import preparar_df
from utils.graficos import liquid_fill, barras_simples, barras_drilldown, barras_empilhadas_horizontais, mapa_correlacao
from utils.transformadores import serei_semana_mes_complexo, dados_grafico_barras, get_delta, serie_temporal_dia_semana_complexo, serei_mes_ano_options, top_10_categorias
from utils.graficos import grefico_calendario
import streamlit as st
import os
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

@st.cache_data
def carregar_dados():
    engine = create_engine(os.getenv("DATABASE_URL"))
    return pd.read_sql_table('minha_vida', engine, index_col='id')

@st.cache_data
def dados_tratados(_df):
    return preparar_df(_df)

df = dados_tratados(carregar_dados())
df = df[df.user_phone_number == 'Diogo'].reset_index(drop=True)

categorias1 = df[[
    'secreto', 'Estudar', 'Leitura', 'Exercício aeróbico',
    'Alimentação saudável', 'Consumo de água', 'Academia', 'Atividade sexual'
]].melt()['variable'].unique()

Hiper_categoria = {
    'secreto': 'Lazer', 'Estudar': 'Evolução pessoal', 'Leitura': 'Evolução pessoal',
    'Exercício aeróbico': 'Saúde do corpo', 'Alimentação saudável': 'Saúde do corpo',
    'Consumo de água': 'Saúde do corpo', 'Atenção plena': 'Saúde da mente',
    'Academia': 'Saúde do corpo', 'Atividade sexual': 'Lazer'
}

imagem = Image.open(Path(__file__).parent / "foto_diogo.jpg")

st.set_page_config(layout="wide", page_title='Análise da vida')
st.success("Análise da vida de Diogo")
st.sidebar.title('Painel de filtros')
st.sidebar.image(imagem, caption='-------------------------------------')

month = st.sidebar.multiselect('Selecione os meses de análise', df["Data"].dt.strftime('%m - %Y').unique())
df_filtrado = df[df['mes'].isin(month)].set_index('Data') if month else df.set_index('Data')

Horario_despertar = st.sidebar.multiselect(
    'Selecione a hora do despertar',
    sorted(df_filtrado[df_filtrado['Hora que eu acordei'].dt.hour != 0]['Hora que eu acordei'].dt.hour.unique())
)
if Horario_despertar:
    df_filtrado = df_filtrado[df_filtrado['Hora que eu acordei'].dt.hour.isin(Horario_despertar)]

categoria = st.sidebar.multiselect('Selecione as categorias da análise', categorias1)
categorias = categoria if categoria else categorias1

Hcategoria = st.sidebar.multiselect('Selecione a hiper categoria', df_filtrado[categorias].rename(columns=Hiper_categoria).columns.unique())
if Hcategoria:
    categorias = {k: v for k, v in Hiper_categoria.items() if v in Hcategoria}.keys()

# ── Métricas ──────────────────────────────────────────────────────────────────

with st.container(border=True, height=250):
    total, saude_corpo, lazer, evolucao = st.columns(4)

    serie_temporal = df_filtrado[categorias1].reset_index().melt("Data")
    serie_temporal_total = df_filtrado[categorias].reset_index().melt("Data")

    def _agg_semanal(df_melted):
        return df_melted.pivot_table(
            index=[df_melted.Data.dt.isocalendar()['year'], df_melted.Data.dt.isocalendar()['week']],
            values='value', aggfunc='mean'
        )

    with total:
        _t = _agg_semanal(serie_temporal_total)
        val = _t.value.mean()
        st.metric("Aderencia Total", f"{val:0,.0%}", delta=get_delta(_t.tail(1).value.values[0], val),
                  border=True, chart_data=_t.value.tolist(), chart_type="area")

    with saude_corpo:
        _sc = serie_temporal[serie_temporal.variable.map(Hiper_categoria) == "Saúde do corpo"]
        _sc = _agg_semanal(_sc)
        val = _sc.value.mean()
        st.metric("Saúde do corpo", f"{val:0,.0%}", delta=get_delta(_sc.tail(1).value.values[0], val),
                  border=True, chart_data=_sc.value.tolist(), chart_type="area")

    with lazer:
        _lz = serie_temporal[serie_temporal.variable.map(Hiper_categoria) == "Lazer"]
        _lz = _agg_semanal(_lz)
        val = _lz.value.mean()
        st.metric("Lazer", f"{val:0,.0%}", delta=get_delta(_lz.tail(1).value.values[0], val),
                  border=True, chart_data=_lz.value.tolist(), chart_type="area")

    with evolucao:
        _ep = serie_temporal[serie_temporal.variable.map(Hiper_categoria) == "Evolução pessoal"]
        _ep = _agg_semanal(_ep)
        val = _ep.value.mean()
        st.metric("Evolução pessoal", f"{val:0,.0%}", delta=get_delta(_ep.tail(1).value.values[0], val),
                  border=True, chart_data=_ep.value.tolist(), chart_type="area")

# ── Visão geral ────────────────────────────────────────────────────────────────

with st.container(border=True, height=380):
    pcol1, pcol2 = st.columns([2, 5])

    with pcol1.container(border=True, height=350):
        liquid_fill(valor=dados_grafico_barras(df_filtrado[categorias].melt(), 'variable', 'value', _agg="mean")[1], tamanho="300px")

    with pcol2.container(border=True, height=350):
        barras_simples(*dados_grafico_barras(df_filtrado[categorias].melt(), 'variable', 'value', _agg="mean"))

    with st.container(border=True, height=350):
        _st = df_filtrado[categorias].reset_index().melt("Data")
        _st['Hiper_categoria'] = _st.variable.map(Hiper_categoria)
        barras_drilldown(*top_10_categorias(_st, "Hiper_categoria", 'variable', 'value', 'mean'))

# ── Aderência por período ──────────────────────────────────────────────────────

with st.container(border=True, height=540):
    st.subheader('Aderência acumulada por categoria')
    col1, col2 = st.columns(2)

    with col1.container(border=True, height=450):
        barras_empilhadas_horizontais(*serie_temporal_dia_semana_complexo(serie_temporal_total, 'Data', 'value', 'variable', 'mean'), "400px")

    with col2.container(border=True, height=450):
        barras_empilhadas_horizontais(*serei_semana_mes_complexo(serie_temporal_total, 'Data', 'value', 'variable', 'mean'), "400px")

    with st.container(border=True, height=350):
        barras_empilhadas_horizontais(*serei_mes_ano_options(serie_temporal_total, 'Data', 'value', 'variable', 'mean'), "300px")

# ── Correlação ─────────────────────────────────────────────────────────────────

with st.container(border=True, height=450):
    st.subheader('Correlação de Pearson das minhas tarefas')
    mapa_correlacao(df_filtrado, categorias=categorias, tamanho="400px")

# ── Calendário ─────────────────────────────────────────────────────────────────

with st.container(border=True, height=600):
    st.subheader('Atividades realizadas por dia')
    cal_data = df_filtrado[list(categorias)].reset_index().melt("Data").dropna(subset=['value'])
    cal_data = cal_data.groupby('Data')['value'].sum().reset_index()
    grefico_calendario(cal_data, ano_2=2025, ano_3=2026)
