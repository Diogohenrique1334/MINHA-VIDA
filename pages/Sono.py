import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from PIL import Image
from streamlit_echarts import st_echarts
import random
import datetime as dt
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import ppscore as pps
from sklearn.metrics import r2_score
from sklearn.linear_model import LinearRegression
from funcoes import ajustes_variaveis as fc
from funcoes import graficos
import re

#Importando o dataset
df = pd.read_excel('planilha da vida.xlsx')
#Add atributos
df['Dia da semana'] = df['Data'].dt.weekday.map({6:'Dom',0:'Seg',1:'Ter',2:'Qua',3:'Qui',4:'Sex',5:'Sab'})
df['mes'] = df["Data"].dt.strftime('%m - %Y')
df['Dia da semana'] = pd.Categorical(df['Dia da semana'], categories=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'], ordered=True)
#variaveis
categorias1 = df[
    [
        'secreto', 
        'Estudar', 
        'Leitura',
        'Exercício aeróbico', 
        'Alimentação saudável',
        'Consumo de água',
        'Atenção plena', 
        'Academia',
        'Atividade sexual'
    ]
    ].melt()['variable'].unique()

Hiper_categoria = {'secreto':'Lazer', 'Estudar':'Evolução pessoal', 'Leitura':'Evolução pessoal','Exercício aeróbico':'Saúde do corpo', 
    'Alimentação saudável':'Saúde do corpo', 'Consumo de água':'Saúde do corpo','Atenção plena':'Saúde da mente', 'Academia':'Saúde do corpo',
    'Atividade sexual':'Lazer'}

#Ajustes variáveis
df = fc(fc(fc(df).tratamento_hora()).tempo_sono_n()).Humor()
#df = fc(df).tratamento_hora()

#df = fc(df).tempo_sono_n()

#imagem do painel de filtros
imagem = Image.open("foto_diogo.jpg")

#-----------------------------------Inicio do app---------------------------------------------

st.set_page_config(layout="wide", page_title='Análise da vida')


st.success("Análise da vida")

st.sidebar.title('Painel de filtros')
st.sidebar.image(imagem,caption='-------------------------------------')

#----------------------------------Filtros do app------------------------------------------------

month = st.sidebar.multiselect('Selecione os meses de análise', df["Data"].dt.strftime('%m - %Y').unique())
if month != []:
    df_filtrado = df[df['mes'].isin(month)].set_index('Data')
else:
    df_filtrado = df.set_index('Data')


Horario_despertar = st.sidebar.multiselect('Selecione a hora do despertar', sorted(df_filtrado[df_filtrado['Hora que eu acordei'].dt.hour != 0]\
['Hora que eu acordei'].dt.hour.unique())) 


if Horario_despertar != []:
    df_filtrado = df_filtrado[df_filtrado['Hora que eu acordei'].dt.hour.isin(Horario_despertar)]


categoria = st.sidebar.multiselect('Selecione as categorias da análise', categorias1)


if categoria != []:
    categorias = [x for x in categorias1 if x in categoria]
else:
    categorias = categorias1


Hcategoria = st.sidebar.multiselect('Selecione a hiper categoria',df_filtrado[categorias].rename(columns=Hiper_categoria).columns.unique())


if Hcategoria != []:
    categorias = {chave: valor for chave, valor in Hiper_categoria.items() if valor in Hcategoria }.keys()

#-------------------------------------graficos do app -------------------------------------

with st.container(border = True, height = 400):
    st.subheader('Horas de sono por dia')
    #st_echarts(graficos(table=df_filtrado).grefico_calendario(categorias='Horas dormindo'), height="300px", key="echarts")

#teste = df_filtrado['Horas dormindo'].dt.hour.melt(id_vars=['Data']).dropna(axis=0).pivot_table(index ='Data', values='value', aggfunc='sum')


teste = df.Data.dt.month.values
teste
df_filtrado
