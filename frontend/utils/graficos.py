import datetime as dt
import plotly.express as px
import pandas as pd
import numpy as np
from streamlit_echarts import st_echarts,Map, JsCode
import json
import requests
import streamlit as st

def liquid_fill(liquidfill_option = None, valor = 0.40, tamanho = "300px"):

    if liquidfill_option is None:
        liquidfill_option = {
            "title": {
                "text": "Top aderencias",
                "left": "center",
                "textStyle": {
                    "fontSize": 20,
                    "fontWeight": "bold",
                    "color": "#ffffff"
                }
            },
            "series": [{
                "type": 'liquidFill',
                "data": valor,
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

    return st_echarts(options=liquidfill_option,height=tamanho)

def barras_laterais_sum_qtd(data, tamanho = "500px"):

    options1 = {
                "dataset": {
                    "source": data
                },
                "grid": {"containLabel": True},
                "xAxis": {"name": "amount"},
                "yAxis": {"type": "category"},
                "visualMap": {
                    "orient": "horizontal",
                    "left": "center",
                    "min": 10,
                    "max": 100,
                    "text": ["Muitas utilizações", "Poucas utilizações"],
                    "dimension": 0,
                    "inRange": {"color": ["#65B581", "#FFCE34", "#FD665F"]},
                },
                "series": [{"type": "bar", "encode": {"x": "amount", "y": "product"}}],
            }
    return st_echarts(options=options1, height=tamanho)

def grafico_rosca(data, tamanho = "500px"):

    options = {
        "tooltip": {"trigger": "item"},
        "legend": {"top": "5%", "left": "center"},
        "series": [
            {
                "name": "Access From",
                "type": "pie",
                "radius": ["40%", "70%"],
                "avoidLabelOverlap": False,
                "padAngle": 5,
                "itemStyle": {"borderRadius": 10},
                "label": {"show": False, "position": "center"},
                "emphasis": {
                    "label": {"show": True, "fontSize": 40, "fontWeight": "bold"}
                },
                "labelLine": {"show": False},
                "data": data
                ,
            }
        ],
    }
    st_echarts(options=options, height=tamanho)

def meia_rosca(data,tamanho = "300px"):

    options = {
        "tooltip": {"trigger": "item"},
        "legend": {"top": "5%", "left": "center"},
        "series": [
            {
                "name": "Access From",
                "type": "pie",
                "radius": ["40%", "70%"],
                "center": ["50%", "70%"],
                "startAngle": 180,
                "endAngle": 360,
                "data": data,
            }
        ],
    }
    return st_echarts(options=options, height=tamanho)

def grefico_calendario(df, anos=None, tamanho=None, cores=None):
    """
    Heatmap de calendário ECharts. Anos detectados automaticamente se não informados.

    df     : DataFrame com colunas 'Data' (datetime) e 'value' (numeric)
    anos   : lista de int com os anos a exibir. Se None, detecta pelos dados.
    tamanho: altura do gráfico (ex: "500px"). Se None, calcula pelo nº de anos.
    cores  : paleta do visualMap [cor_min, cor_max]. Default: ["#cac2c2", "#99251F"]
    """
    cores = cores or ["#cac2c2", "#99251F"]

    df = df.copy()
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    datas = (
        df.dropna(subset=['Data'])
        .pivot_table(index='Data', values='value', aggfunc='sum')
        .sort_index()
    )

    if anos is None:
        anos = sorted(datas.index.year.unique().tolist()) if not datas.empty else []

    if not anos:
        return

    def _to_date_str(idx):
        return idx.strftime("%Y-%m-%d")

    def _to_native_val(x):
        return None if pd.isna(x) else int(x)

    def _build_year(y):
        if datas.empty:
            return []
        return [
            [_to_date_str(idx), _to_native_val(val)]
            for idx, val in zip(datas.index, datas['value'].values)
            if isinstance(idx, pd.Timestamp) and not pd.isna(idx) and idx.year == y
        ]

    n = len(anos)
    # posição vertical: distribui os n calendários entre 5% e 95%
    spacing = 90 / n
    tops = [f"{5 + i * spacing:.0f}%" for i in range(n)]

    vmax_native = 1.0
    if not datas.empty:
        vmax = pd.to_numeric(datas['value'], errors='coerce').max()
        vmax_native = float(vmax) if pd.notna(vmax) else 1.0

    option = {
        "tooltip": {"position": "top"},
        "visualMap": {
            "min": 0, "max": vmax_native,
            "calculable": True, "orient": "horizontal", "left": "center",
            "inRange": {"color": cores},
        },
        "calendar": [
            {
                "range": str(ano),
                "cellSize": ["auto", 14],
                "top": tops[i],
                "splitLine": {"lineStyle": {"color": "#000000"}},
                "itemStyle": {"color": "#ffffff"},
                "dayLabel": {"color": "#ffffff"},
                "monthLabel": {"color": "#ffffff"},
                "yearLabel": {"color": "#cac2c2"},
            }
            for i, ano in enumerate(anos)
        ],
        "series": [
            {
                "type": "heatmap",
                "coordinateSystem": "calendar",
                "calendarIndex": i,
                "data": _build_year(ano),
            }
            for i, ano in enumerate(anos)
        ],
    }

    if tamanho is None:
        tamanho = f"{max(300, n * 175)}px"

    def to_native(obj):
        from datetime import datetime
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, (pd.Timestamp, datetime)): return obj.isoformat()
        if obj is pd.NaT: return None
        if isinstance(obj, np.ndarray): return [to_native(x) for x in obj.tolist()]
        if isinstance(obj, (list, tuple, set)): return [to_native(x) for x in obj]
        if isinstance(obj, dict): return {str(k): to_native(v) for k, v in obj.items()}
        return obj

    return st_echarts(options=to_native(option), height=tamanho)

def mapa_brasil(dados_estados = None):


    if dados_estados is None:
        dados_estados = [
            {"name": "São Paulo", "value": 46649132},
            {"name": "Minas Gerais", "value": 21411923},
            {"name": "Rio de Janeiro", "value": 17366189},
            {"name": "Bahia", "value": 14985284},
            {"name": "Paraná", "value": 11835379},
            {"name": "Rio Grande do Sul", "value": 11466630},
            {"name": "Pernambuco", "value": 9674793},
            {"name": "Ceará", "value": 9240580},
            {"name": "Pará", "value": 8777124},
            {"name": "Santa Catarina", "value": 7610361},
            {"name": "Goiás", "value": 7206589},
            {"name": "Maranhão", "value": 6775805},
            {"name": "Amazonas", "value": 4269995},
            {"name": "Espírito Santo", "value": 4108508},
            {"name": "Paraíba", "value": 4059905},
            {"name": "Rio Grande do Norte", "value": 3560903},
            {"name": "Mato Grosso", "value": 3658813},
            {"name": "Alagoas", "value": 3365351},
            {"name": "Piauí", "value": 3281480},
            {"name": "Distrito Federal", "value": 3094325},
            {"name": "Mato Grosso do Sul", "value": 2839188},
            {"name": "Sergipe", "value": 2338474},
            {"name": "Rondônia", "value": 1815278},
            {"name": "Tocantins", "value": 1607363},
            {"name": "Acre", "value": 906876},
            {"name": "Amapá", "value": 877613},
            {"name": "Roraima", "value": 652713},
        ]

    formatter = JsCode(
        """
        function (params) {
            return params.seriesName + '<br/>' +
                params.name + ': ' +
                params.value.toLocaleString('pt-BR');
        }
    """
    ).js_code

    # GeoJSON do Brasil
    url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    geo_json = requests.get(url).json()

    # Cria o mapa
    map = Map(
        "Brazil",
        geo_json,
    )

    options = {
        "title": {
            "text": "População dos Estados Brasileiros",
            "subtext": "Dados exemplo",
            "left": "right",
        },
        "tooltip": {
            "trigger": "item",
            "formatter": formatter,
        },
        "visualMap": {
            "min": 500000,
            "max": 50000000,
            "left": "left",
            "top": "bottom",
            "text": ["Maior", "Menor"],
            "calculable": True,
            "inRange": {
                "color": [
                    "#E0F3F8",
                    "#ABD9E9",
                    "#74ADD1",
                    "#4575B4",
                    "#313695",
                ]
            },
        },
        "toolbox": {
            "show": True,
            "orient": "vertical",
            "left": "right",
            "top": "center",
            "feature": {
                "dataView": {"readOnly": False},
                "restore": {},
                "saveAsImage": {},
            },
        },
        "series": [
            {
                "name": "População",
                "type": "map",
                "map": "Brazil",
                "roam": True,
                "emphasis": {
                    "label": {
                        "show": True
                    }
                },
                "data": dados_estados,
            }
        ],
    }

    st_echarts(options=options, map=map, height="700px")

def barras_empilhadas(raw_data = None, series_names = None, eixo_x = None, tamanho = "500px"):


    if raw_data is None:
        raw_data = [
            [100, 302, 301, 334, 390, 330, 320],
            [320, 132, 101, 134, 90, 230, 210],
            [220, 182, 191, 234, 290, 330, 310],
            [150, 212, 201, 154, 190, 330, 410],
            [820, 832, 901, 934, 1290, 1330, 1320],
        ]

    if series_names is None:
        series_names = ["Direct", "Mail Ad", "Affiliate Ad", "Video Ad", "Search Engine"]

    if eixo_x is None:

        eixo_x = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    total_data = []
    for i in range(len(raw_data[0])):
        sum_val = 0
        for j in range(len(raw_data)):
            sum_val += raw_data[j][i]
        total_data.append(sum_val)


    series = []
    for sid, name in enumerate(series_names):
        series.append(
            {
                "name": name,
                "type": "bar",
                "stack": "total",
                "barWidth": "60%",
                "label": {
                    "show": True,
                    "formatter": JsCode(
                        "function(params) { return Math.round(params.value * 1000) / 10 + '%'; }"
                    ).js_code,
                },
                "data": [
                    (0 if total_data[did] <= 0 else d / total_data[did])
                    for did, d in enumerate(raw_data[sid])
                ],
            }
        )

    options = {
        "legend": {"selectedMode": False},
        "yAxis": {"type": "value"},
        "xAxis": {
            "type": "category",
            "data": eixo_x,
        },
        "series": series,
    }

    return st_echarts(options=options, height=tamanho)

def barras_empilhadas_laterais(raw_data = None, series_names = None, eixo = None, tamanho = "500px"):

    options = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {
            "data": series_names},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "value"},
        "yAxis": {
            "type": "category",
            "data": eixo,
        },
        "series": raw_data,
    }

    return st_echarts(options=options, height=tamanho)

def barras_empilhadas_horizontais(raw_data=None, series_names=None, eixo=None, tamanho="500px"):
    options = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {
            "data": series_names,
            "top": 0,
            "type": "scroll",
            "textStyle": {
                "color": "#ffffff",
                "fontSize": 11,
            }},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "15%", "containLabel": True},
        "xAxis": {"type": "category", "data": eixo},
        "yAxis": {"type": "value"},
        "series": raw_data,
    }

    return st_echarts(options=options, height=tamanho)

def barras_drilldown(drilldown_data,categorias,dados_principais,tamanho ="300px" ):

    if "bar_drilldown_group" not in st.session_state:
        st.session_state.bar_drilldown_group = None

    group = st.session_state.bar_drilldown_group

    if group is None:
        options = {
            "xAxis": {"data": categorias},
            "yAxis": {},
            "animationDurationUpdate": 500,
            "series": {
                "type": "bar",
                "id": "sales",
                "data": dados_principais,
                "universalTransition": {"enabled": True, "divideShape": "clone"},
            },
        }
    else:
        sub_data = drilldown_data[group]
        options = {
            "xAxis": {"data": [item[0] for item in sub_data]},
            "axisLabel": {
                "interval": 0,
                "rotate": 30,
                "overflow": "break",
                },
            "yAxis": {},
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
                },
            "animationDurationUpdate": 500,
            "series": {
                "type": "bar",
                "id": "sales",
                "dataGroupId": group,
                "data": [item[1] for item in sub_data],
                "universalTransition": {"enabled": True, "divideShape": "clone"},
            },
        }

    events = {
        "click": "function(params) { return params.data && params.data.groupId ? params.data.groupId : null }",
    }

    if group is not None:
        if st.button("Back", key="bar_drilldown_back"):
            st.session_state.bar_drilldown_group = None
            st.rerun()

    result = st_echarts(
        options=options,
        events=events,
        height=tamanho,
        key="render_bar_drilldown",
    )

    group_id = result.get("groupId") if isinstance(result, dict) else result
    if group_id and isinstance(group_id, str) and group_id in drilldown_data and st.session_state.bar_drilldown_group != group_id:
        st.session_state.bar_drilldown_group = group_id
        st.rerun()

def barras_simples(categorias,valores, tamanho = "300px"):

    options = {
        "title": {"text": "Análise de Gastos"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "toolbox": {"feature": {"saveAsImage": {}, "restore": {}, "dataView": {}}},
        "xAxis": {"type": "category", "data": categorias},
        "yAxis": {"type": "value"},
        "series": [{
            "name": "Gastos",
            "data": valores,
            "type": "bar",
            "markLine": {"data": [{"type": "average", "name": "Média"}]},
            "color":['#18990b']
        }],
    }
    return st_echarts(options=options, height=tamanho)

def mapa_correlacao(table,categorias, tamanho = "500px"):

    corr = table[np.append([x for x in categorias],['Tempo de sono','Humor'])].squeeze().resample('W').mean().asfreq('W').corr()

    data_serialized = corr.fillna(0).round(2).reset_index().melt(id_vars='index').values.tolist()


    option = {
        "tooltip": {"position": "top"},
        "grid": {"height": "50%", "top": "13%"},
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
                        "color": "#000000",
                        "borderColor": "#000000",
                        "borderWidth": 2,
                        "borderType": "solid",
                        "shadowOffsetX": 5,
                        "shadowOffsetY": 5,
                        "opacity": 0.8
                    }
                },
            }
        ],
    }

    return st_echarts(options=option,height=tamanho)
