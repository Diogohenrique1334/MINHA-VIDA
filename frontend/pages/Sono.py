import pandas as pd
from PIL import Image
from pathlib import Path
import streamlit as st

from utils.tratamente_dados import preparar_df
from utils.dados import carregar_dados as _carregar_dados
from utils.filtros import render_filtros
from utils.estilos import inject_css, cabecalho_secao, linha_kpis

from baltazar.graficos.graficos_streamlit.graficos import (
    violino, barras_empilhadas_horizontais, grefico_calendario,
)
from baltazar.graficos.graficos_streamlit.transformadores import (
    serie_temporal_dia_semana_complexo, serei_semana_mes_complexo,
    serei_mes_ano_options,
)

ACCENT = "#18990b"
META_SONO_H = 7  # abaixo disso é considerado noite com déficit


@st.cache_data(ttl=600)
def carregar_dados():
    return _carregar_dados()


@st.cache_data(ttl=600)
def dados_tratados(_df):
    return preparar_df(_df)


df = dados_tratados(carregar_dados())

imagem = Image.open(Path(__file__).parent.parent / "foto_diogo.jpg")

st.set_page_config(layout="wide", page_title='Sono')
inject_css()

df_filtrado, usuario = render_filtros(df, key_prefix="sono_", imagem=imagem)
st.success(f"Análise de Sono - {usuario}")

# - Preparação dos dados de sono -----------------------

sono = df_filtrado.reset_index()[['Data', 'Tempo de sono']].dropna(subset=['Tempo de sono'])
sono = sono.rename(columns={'Tempo de sono': 'value'})
sono['value'] = pd.to_numeric(sono['value'], errors='coerce')
sono = sono.dropna(subset=['value'])
sono['variable'] = 'Tempo de sono'

# - KPIs do topo --------------------------------

with st.container(border=True):
    if sono.empty:
        linha_kpis([{"label": "Sem dados", "valor": "-", "sub": None}])
    else:
        media = sono['value'].mean()
        maxima = sono['value'].max()
        deficit = (sono['value'] < META_SONO_H).mean() * 100
        n = len(sono)
        serie_sem = sono.set_index('Data')['value'].resample('W').mean().dropna()
        linha_kpis([
            {"label": "Sono médio", "valor": f"{media:0.1f}h", "sub": None, "serie": serie_sem.tolist()},
            {"label": "Noite mais longa", "valor": f"{maxima:0.1f}h", "sub": None},
            {"label": f"Noites com déficit (<{META_SONO_H}h)", "valor": f"{deficit:0.0f}%", "sub": None},
            {"label": "Registros", "valor": str(n), "sub": None},
        ])

# - Distribuição + dia da semana -----------------------

with st.container(border=True, height=380):
    col1, col2 = st.columns([1, 3])

    with col1.container(border=True, height=330):
        violino(sono, 'value', cor=ACCENT, rotulo="Horas de sono", tamanho=300)

    with col2.container(border=True, height=330):
        barras_empilhadas_horizontais(
            *serie_temporal_dia_semana_complexo(sono, 'Data', 'value', 'variable', 'mean'),
            "280px"
        )

# - Por semana e mês -----------------------------

with st.container(border=True, height=350):
    col1, col2 = st.columns(2)

    with col1.container(border=True, height=300):
        barras_empilhadas_horizontais(
            *serei_semana_mes_complexo(sono, 'Data', 'value', 'variable', 'mean'),
            "250px"
        )

    with col2.container(border=True, height=300):
        barras_empilhadas_horizontais(
            *serei_mes_ano_options(sono, 'Data', 'value', 'variable', 'mean'),
            "250px"
        )

# - Calendário ---------------------------------

with st.container(border=True):
    cabecalho_secao('Horas de sono por dia')
    grefico_calendario(sono[['Data', 'value']])
