
import datetime as dt
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import plotly.express as px
from streamlit_echarts import st_echarts

"""
Melhorias:
1° grafico por tarefas: usar a mesma funçao para mês e horas

2° grafico de calendário, selecionar os meses automáticamente
"""

#variaveis globais
scaler = MinMaxScaler()

#funcoes_globais
def substituir_outliers(valor):
    if pd.isna(valor):
        return valor
    # Definindo o limite de tempo de sono
    limite = pd.Timedelta(days=1)
    
    if valor > limite:
        return pd.NaT
    return valor

class ajustes_variaveis:

    def __init__(self,table):

        self.table = table


    def tratamento_hora(self,table = None):

        if table is None:
            table = self.table
        else:
            table
        
        table['Horario que eu fui dormir'] = \
        table['Horario que eu fui dormir'].fillna('00:00:00').map(
        lambda x: (dt.datetime.strptime(str(x).split(' ')[1], '%H:%M:%S') + dt.timedelta(days = 1)) 
        if dt.datetime.strptime(str(x), '%H:%M:%S').hour in range(10)
        else (dt.datetime.strptime(str(x), '%H:%M:%S'))
        )
        
        table['Horario que eu fui dormir'] = \
        table.apply(lambda x: x['Data'] + dt.timedelta(days = (x['Horario que eu fui dormir'].day) - 1, 
                                                hours = x['Horario que eu fui dormir'].hour, 
                                                minutes = x['Horario que eu fui dormir'].minute), axis=1)
        
#        table['Hora que eu acordei'] = table['Hora que eu acordei'].fillna('00:00:00').map(lambda x: dt.datetime.strptime(str(x).split(' ')[2],'%H:%M:%S'))
        
#        table['Hora que eu acordei'] = \
#        table.apply(lambda x: x['Data'] + dt.timedelta(hours = x['Hora que eu acordei'].hour, 
#                                                minutes = x['Hora que eu acordei'].minute), axis=1)
        
        acordou = table[table['Hora que eu acordei'].dt.hour != 0].reset_index()[['Hora que eu acordei','index']]
        dormiu = table[table['Hora que eu acordei'].dt.hour != 0].reset_index()[['Horario que eu fui dormir','index']]
        tempo_sono = pd.DataFrame()
        
        for x in range(len(dormiu)-1):
        
            tempo_sono = pd.concat(
                [pd.DataFrame({'chave':acordou['index'].loc[x+1],
                    "Horas dormindo":[acordou['Hora que eu acordei'].loc[x+1] - dormiu['Horario que eu fui dormir'].loc[x]]}),tempo_sono]
            )

        
        
        table = pd.merge(left=table,
                        right=tempo_sono,
                        left_index=True, 
                        right_on='chave', 
                        how='left').reset_index().drop(columns='index')

        return table

    def tempo_sono_n(self,table = None):

        if table is None:
            table = self.table
        else:
            table

        table['Horas dormindo'] = table['Horas dormindo'].apply(substituir_outliers)
        table['Tempo de sono'] = scaler.fit_transform(
            table['Horas dormindo'].fillna(table[table['Horas dormindo'].map(lambda x: str(x).split(' ')[0]) == '0' ]['Horas dormindo'].mean()
                                    ).values.reshape(-1,1)).flatten()
        
        table['Tempo de sono'] = table.apply(lambda x: np.nan if pd.isna(x['Horas dormindo']) else x['Tempo de sono'], axis = 1)

        return table

    def Humor(self,table = None):

        if table is None:
            table = self.table
        else:
            table

        table['Humor'] = scaler.fit_transform(
            (table['Nota do humor'] + table['Nota do humor fim do dia']).values.reshape(-1,1)
        ).flatten()

        return table

class graficos:

    def __init__(self,table = None, colunas = None):
        
        self.table = table
        self.colunas = colunas

    def aderencia_hora(self, categoria_x, categorias, titulo):
        self.table = self.table
        self.categoria_x = categoria_x
        self.categorias = categorias
        self.titulo = titulo

        aderencia_por_hora = px.bar(
            self.table[self.table[self.categoria_x].dt.hour != 0].pivot_table(index=self.table[self.categoria_x].dt.hour, values=self.categorias, aggfunc='mean')
            ,title=self.titulo)
        
        aderencia_por_hora.update_layout(yaxis_title='')
        
        return aderencia_por_hora
    
    def aderencia_mes(self, categoria_x, categorias, titulo):
        self.table = self.table
        self.categoria_x = categoria_x
        self.categorias = categorias
        self.titulo = titulo

        aderencia_por_hora = px.bar(
            self.table.pivot_table(index=self.categoria_x, values=self.categorias, aggfunc='mean')
            ,title=self.titulo
            
            )
        
        aderencia_por_hora.update_layout(yaxis_title='')
        
        return aderencia_por_hora
        
    
    def grafico_barras(self,titulo,cor = None, tamanho = 350):

        if cor is None:
            cor = ['#18990b']

        aderencia_categorias = px.bar(self.table, x=self.table.index, y=self.table.values, title=titulo,height=tamanho, color_discrete_sequence=cor)

        aderencia_categorias.update_layout(yaxis_title='',xaxis_title='')

        return aderencia_categorias
    
    def liquid_fill(self, valor):
        liquidfill_option = {
            "title": {
                "text": "Aderência total",
                "left": "center",
                "textStyle": {
                    "fontSize": 20,
                    "fontWeight": "bold",
                    "color": "#ffffff"
                }
            },
            "series": [{
                "type": 'liquidFill',
                "data": [valor],
                "center": ['50%', '50%'],
                "radius": '50%',
                "waveAnimation": True,
                "outline": {
                    "show": True,
                    "borderDistance": 8,
                    "itemStyle": {
                        "borderWidth": 4,
                        "borderColor": "#ffffff"
                    }
                },
                "backgroundStyle": {
                    "color": "#ffffff"
                },
                "label": {
                    "normal": {
                        
                        "textStyle": {
                            "fontSize": 20,
                            "color": '#18990b'
                        }
                    }
                },
                "color":['#18990b']
            }]
        }

        return liquidfill_option

    
    def grafico_linhas_tempo(self,coluna_data,categorias,titulo,cor = ['#18990b'],tamanho = 350 ):

        linha_tempo_aderencia = px.line(
            self.table.set_index(coluna_data)[categorias].squeeze().resample('m').mean().asfreq('m').reset_index().melt(coluna_data).dropna(subset = 'value').drop(columns ='variable').groupby(coluna_data)['value'].mean()
        , title=titulo,height=tamanho,color_discrete_sequence=cor)

        linha_tempo_aderencia.update_traces(mode='lines+markers')

        linha_tempo_aderencia.update_layout(
            showlegend=False,
            yaxis_title='Aderência',
            xaxis_title='Data',
            #title_x=0.5, # Centralizar o título
            #title_font=dict(size=20, family='Arial', color='#30509c'), # Personalizar fonte do título
            xaxis=dict(
                tickangle=-45, # Rotacionar rótulos do eixo x para melhor legibilidade
                showgrid=False, # Mostrar linhas de grade
                gridcolor='LightGray' # Personalizar cor da grade
            ),
            yaxis=dict(
                showgrid=True, # Mostrar linhas de grade
                gridcolor='LightGray' # Personalizar cor da grade
            ),
            plot_bgcolor='rgba(0,0,0,0)', # Definir cor de fundo do gráfico como transparente
            paper_bgcolor='rgba(0,0,0,0)' # Definir cor de fundo do papel como transparente
        )

        return linha_tempo_aderencia
    
    def grefico_calendario(self, categorias,ano_1,ano_2):

        datas = self.table[categorias].reset_index().melt(id_vars='Data').dropna(axis=0).pivot_table(index ='Data', values='value', aggfunc='sum')

        # Separar dados por ano
        data_1 = [[str(index.date()), int(row['value'])] for index, row in datas.iterrows() if index.year == ano_1]
        data_2 = [[str(index.date()), int(row['value'])] for index, row in datas.iterrows() if index.year == ano_2]

        option1 = {
            "tooltip": {"position": "top"},
            "visualMap": {
                "min": 0,
                "max": datas['value'].max() if not datas.empty else 1,  # Ajuste para máximo dos dados
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "low": "low",
                "color": ['#18990b', '#cac2c2'],
            },
            "calendar": [
                { # Calendário 2024
                    "range": str(ano_1),
                    "cellSize": ["auto", 14],
                    "top": "7%",
                    "splitLine": {"lineStyle": {"color": "#000000"}},
                    "itemStyle": {"color": "#ffffff"},
                    "dayLabel": {"color": "#ffffff"},
                    "monthLabel": {"color": "#ffffff"},
                    "yearLabel": {"color": "#cac2c2"}
                },
                { # Calendário 2025
                    "range": str(ano_2),
                    "cellSize": ["auto", 14],
                    "top": "50%",  # Posicionado abaixo do primeiro calendário
                    "splitLine": {"lineStyle": {"color": "#000000"}},
                    "itemStyle": {"color": "#ffffff"},
                    "dayLabel": {"color": "#ffffff"},
                    "monthLabel": {"color": "#ffffff"},
                    "yearLabel": {"color": "#cac2c2"}
                }
            ],
            "series": [
                { # Série para 2024
                    "type": "heatmap",
                    "coordinateSystem": "calendar",
                    "calendarIndex": 0,
                    "data": data_1
                },
                { # Série para 2025
                    "type": "heatmap",
                    "coordinateSystem": "calendar",
                    "calendarIndex": 1,
                    "data": data_2
                }
            ],
        }

        return option1
    

    #mapa de calor da correlação

    def mapa_valor(self, categorias):

        corr = self.table[np.append([x for x in categorias],['Tempo de sono','Humor'])].squeeze().resample('W').mean().asfreq('W').corr()

        data_serialized = corr.fillna(0).round(2).reset_index().melt(id_vars='index').values.tolist()


        option = {
            "tooltip": {"position": "top"},
            "grid": {"height": "50%", "top": "10%"},
            "xAxis": {"type": "category", "data": corr.columns.tolist(), "splitArea": {"show": True},"axisLabel": {"rotate": "20"}},
            "yAxis": {"type": "category", "data": corr.index.tolist(), "splitArea": {"show": True}},
            "visualMap": {
                "min": -1,
                "max": 1,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "top":"top",
                "bottom": "15%",
                "color": ['#18990b', '#cac2c2'],
            },
            "series": [
                {
                    "name": "Punch Card",
                    "type": "heatmap",
                    "data": data_serialized,
                    "label": {"show": True},
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0, 0, 0, 0.47)",
                            "color": "#000000",  # Cor do item
                            "borderColor": "#000000",  # Cor da borda
                            "borderWidth": 2,  # Largura da borda
                            "borderType": "solid",  # Tipo de borda
                            "shadowOffsetX": 5,  # Deslocamento horizontal da sombra
                            "shadowOffsetY": 5,  # Deslocamento vertical da sombra
                            "opacity": 0.8  # Opacidade do item
                        }
                    },
                }
            ],
        }

        return option
        
"""

options = {
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
    "legend": {
        "data": ["Direct", "Mail Ad", "Affiliate Ad", "Video Ad", "Search Engine"]
    },
    "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    "xAxis": {"type": "value"},
    "yAxis": {
        "type": "category",
        "data": ["seg", "ter", "quar", "quin", "sex", "sab", "don"],
    },
    "series": [
        {
            "name": "Direct",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": [320, 302, 301, 334, 390, 330, 320],
        },
        {
            "name": "Mail Ad",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": [120, 132, 101, 134, 90, 230, 210],
        },
        {
            "name": "Affiliate Ad",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": [220, 182, 191, 234, 290, 330, 310],
        },
        {
            "name": "Video Ad",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": [150, 212, 201, 154, 190, 330, 410],
        },
        {
            "name": "Search Engine",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": [820, 832, 901, 934, 1290, 1330, 1320],
        },
    ],
}
st_echarts(options=options, height="500px")
"""
    
