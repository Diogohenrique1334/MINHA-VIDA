import pandas as pd
import numpy as np
import datetime as dt

# Máximo plausível de horas de sono num dia. Valores >= isto são erro de
# anotação (outlier) e viram NaN, sem apagar o resto do registro do dia.
LIMITE_SONO_H = 12


def preparar_df(df, limite_sono_h=LIMITE_SONO_H):
    """Prepara o DataFrame wide para o dashboard (todos os usuários).

    Não filtra por usuário - a seleção Diogo/Michele acontece na camada de
    filtros (utils/filtros.py). Fills de média são feitos por usuário para não
    misturar as estatísticas de um com o outro.
    """

    def Humor(table):

        table['Humor'] = table.apply(lambda x: (x['Nota do humor'] + x['Nota do humor fim do dia']) / 2, axis = 1)

        return table

    usuario = {'5511959536031':"Diogo",'5511991422452':"Michele"}

    # Apenas as métricas precisam ser renomeadas - os hábitos já chegam com o
    # nome de exibição (vêm de habitos.nome no novo modelo relacional).
    Colunas_tratadas = {'data':'Data',
                        'nota_humor':'Nota do humor',
                        'Nota_humor_fim_dia':'Nota do humor fim do dia',
                        'data_hora_acordei':'Hora que eu acordei',
                        'data_hora_dormi':'Horario que eu fui dormir'
                    }

    # Garante que a coluna 'data' é do tipo datetime e ajusta para o fuso horário correto
    df['data'] = pd.to_datetime(df['data'].dt.date)

    # Criação das colunas de data/hora a partir da coluna 'data'
    df['Dia da semana'] = df['data'].dt.weekday.map({6:'Dom',0:'Seg',1:'Ter',2:'Qua',3:'Qui',4:'Sex',5:'Sab'})
    df['mes'] = df["data"].dt.strftime('%m - %Y')
    df['mes_ordenacao'] = pd.to_datetime(df['data']).dt.to_period('M')
    df['mes'] = pd.Categorical(df['mes'], categories=df.sort_values('mes_ordenacao')['mes'].unique(), ordered=True)
    df = df.drop(columns=['mes_ordenacao','Diario_e_fixacao','Atencao_plena','status_conversa'], errors='ignore').rename(columns = Colunas_tratadas)
    df['Dia da semana'] = pd.Categorical(df['Dia da semana'], categories=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'], ordered=True)
    df['user_phone_number'] = df['user_phone_number'].map(usuario).astype('category')

    # Fills de média POR USUÁRIO (não misturar estatísticas de Diogo e Michele).
    df['Nota do humor'] = df.groupby('user_phone_number', observed=True)['Nota do humor'].transform(lambda s: s.fillna(s.mean()))
    df['Horario que eu fui dormir'] = df.groupby('user_phone_number', observed=True)['Horario que eu fui dormir'].transform(lambda s: s.fillna(s.mean()))

    # Converte colunas booleanas para 0 e 1 para cálculos
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype('bool').astype(int)

    df.sort_values('Data', inplace=True)

    mask = ~df['Horario que eu fui dormir'].isnull()

    df['Tempo de sono'] = None

    df.loc[mask,'Tempo de sono'] = (df.loc[mask,'Hora que eu acordei'] - df.loc[mask,'Horario que eu fui dormir']).map(
    lambda x: ((x - dt.timedelta(days = int(str(x).split(" ")[0]))).total_seconds() / 60) / 60 if pd.notna(x) else x)

    # Cap anti-outlier: sono >= limite (default 12h) é erro de anotação -> NaN.
    df['Tempo de sono'] = pd.to_numeric(df['Tempo de sono'], errors='coerce')
    df.loc[df['Tempo de sono'] >= limite_sono_h, 'Tempo de sono'] = np.nan

    return Humor(df)
