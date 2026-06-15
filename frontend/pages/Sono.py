import pandas as pd
from PIL import Image
from pathlib import Path
import plotly.express as px
from utils.graficos import barras_empilhadas_horizontais, grefico_calendario
from utils.transformadores import serie_temporal_dia_semana_complexo, serei_semana_mes_complexo, serei_mes_ano_options
from utils.tratamente_dados import preparar_df
import streamlit as st
from utils.dados import carregar_dados as _carregar_dados

@st.cache_data
def carregar_dados():
    return _carregar_dados()

@st.cache_data
def dados_tratados(_df):
    return preparar_df(_df)

df = dados_tratados(carregar_dados())
df = df[df.user_phone_number == 'Diogo'].reset_index(drop=True)

imagem = Image.open(Path(__file__).parent.parent / "foto_diogo.jpg")

st.set_page_config(layout="wide", page_title='Sono')
st.success("Análise de Sono")
st.sidebar.title('Painel de filtros')
st.sidebar.image(imagem, caption='-------------------------------------')

month = st.sidebar.multiselect('Selecione os meses', df["Data"].dt.strftime('%m - %Y').unique())
df_filtrado = df[df['mes'].isin(month)].set_index('Data') if month else df.set_index('Data')

Horario_despertar = st.sidebar.multiselect(
    'Selecione a hora do despertar',
    sorted(df_filtrado[df_filtrado['Hora que eu acordei'].dt.hour != 0]['Hora que eu acordei'].dt.hour.unique())
)
if Horario_despertar:
    df_filtrado = df_filtrado[df_filtrado['Hora que eu acordei'].dt.hour.isin(Horario_despertar)]

# ── Preparação dos dados de sono ──────────────────────────────────────────────

sono = df_filtrado.reset_index()[['Data', 'Tempo de sono']].dropna(subset=['Tempo de sono'])
sono = sono.rename(columns={'Tempo de sono': 'value'})
sono['value'] = pd.to_numeric(sono['value'], errors='coerce')
sono = sono.dropna(subset=['value'])
sono['variable'] = 'Tempo de sono'

# ── Distribuição + dia da semana ──────────────────────────────────────────────

with st.container(border=True, height=380):
    col1, col2 = st.columns([1, 3])

    with col1.container(border=True, height=330):
        st.plotly_chart(
            px.violin(sono, y="value", box=True, color_discrete_sequence=['#18990b'],
                      labels={"value": "Horas de sono"}),
            use_container_width=True
        )

    with col2.container(border=True, height=330):
        barras_empilhadas_horizontais(
            *serie_temporal_dia_semana_complexo(sono, 'Data', 'value', 'variable', 'mean'),
            "280px"
        )

# ── Por semana e mês ──────────────────────────────────────────────────────────

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

# ── Calendário ─────────────────────────────────────────────────────────────────

with st.container(border=True):
    st.subheader('Horas de sono por dia')
    grefico_calendario(sono[['Data', 'value']])
