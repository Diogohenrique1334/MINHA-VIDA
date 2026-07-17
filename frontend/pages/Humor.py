from PIL import Image
from pathlib import Path
import streamlit as st

from utils.tratamente_dados import preparar_df
from utils.dados import carregar_dados as _carregar_dados
from utils.filtros import render_filtros
from utils.estilos import inject_css, cabecalho_secao, linha_kpis

from baltazar.graficos.graficos_streamlit.graficos import (
    liquid_fill, barras_empilhadas_horizontais, grefico_calendario,
)
from baltazar.graficos.graficos_streamlit.transformadores import (
    serie_temporal_dia_semana_complexo, serei_semana_mes_complexo,
    serei_mes_ano_options, get_delta,
)

_DIA_COMPLETO = {'Seg': 'Segunda', 'Ter': 'Terça', 'Qua': 'Quarta', 'Qui': 'Quinta',
                 'Sex': 'Sexta', 'Sab': 'Sábado', 'Dom': 'Domingo'}


@st.cache_data(ttl=600)
def carregar_dados():
    return _carregar_dados()


@st.cache_data(ttl=600)
def dados_tratados(_df):
    return preparar_df(_df)


df = dados_tratados(carregar_dados())

imagem = Image.open(Path(__file__).parent.parent / "foto_diogo.jpg")

st.set_page_config(layout="wide", page_title='Humor')
inject_css()

df_filtrado, usuario = render_filtros(df, key_prefix="humor_", imagem=imagem)
st.success(f"Análise de Humor - {usuario}")

# - Preparação dos dados de humor -----------------------

humor_df = df_filtrado.reset_index()[['Data', 'Humor', 'Dia da semana']].dropna(subset=['Humor'])

humor = humor_df[['Data', 'Humor']].rename(columns={'Humor': 'value'})
humor['variable'] = 'Humor'

# - KPIs do topo --------------------------------

with st.container(border=True):
    if humor_df.empty:
        linha_kpis([{"label": "Sem dados", "valor": "-", "sub": None}])
    else:
        media = humor_df['Humor'].mean()
        n = len(humor_df)
        por_dia = humor_df.groupby('Dia da semana', observed=True)['Humor'].mean()
        melhor_dia = _DIA_COMPLETO.get(por_dia.idxmax(), str(por_dia.idxmax()))
        serie_sem = humor_df.set_index('Data')['Humor'].resample('W').mean().dropna()
        sub = get_delta(serie_sem.iloc[-1], serie_sem.mean()) if len(serie_sem) else None
        linha_kpis([
            {"label": "Humor médio", "valor": f"{media:0.1f}", "sub": None},
            {"label": "Melhor dia", "valor": melhor_dia, "sub": None},
            {"label": "Tendência (semana)", "valor": f"{serie_sem.iloc[-1]:0.1f}" if len(serie_sem) else "-", "sub": sub, "serie": serie_sem.tolist()},
            {"label": "Registros", "valor": str(n), "sub": None},
        ])

# - Visão geral --------------------------------

with st.container(border=True, height=380):
    col1, col2 = st.columns([1, 3])

    with col1.container(border=True, height=330):
        liquid_fill(valor=[humor['value'].mean() / 10], tamanho="280px")

    with col2.container(border=True, height=330):
        barras_empilhadas_horizontais(
            *serie_temporal_dia_semana_complexo(humor, 'Data', 'value', 'variable', 'mean'),
            "280px"
        )

# - Aderência por período ---------------------------

with st.container(border=True, height=350):
    col1, col2 = st.columns(2)

    with col1.container(border=True, height=300):
        barras_empilhadas_horizontais(
            *serei_semana_mes_complexo(humor, 'Data', 'value', 'variable', 'mean'),
            "250px"
        )

    with col2.container(border=True, height=300):
        barras_empilhadas_horizontais(
            *serei_mes_ano_options(humor, 'Data', 'value', 'variable', 'mean'),
            "250px"
        )

# - Calendário ---------------------------------

with st.container(border=True):
    cabecalho_secao('Nota de humor por dia')
    grefico_calendario(humor[['Data', 'value']])
