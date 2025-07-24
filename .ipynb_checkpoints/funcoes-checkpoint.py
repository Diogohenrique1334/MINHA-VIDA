
import datetime as dt
import pandas as pd
import baltazar as btz
import numpy as np
from sklearn.preprocessing import MinMaxScaler

#variaveis globais
scaler = MinMaxScaler()

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
        lambda x: (dt.datetime.strptime(str(x), '%H:%M:%S') + dt.timedelta(days = 1)) 
        if dt.datetime.strptime(str(x), '%H:%M:%S').hour in range(10) 
        else (dt.datetime.strptime(str(x), '%H:%M:%S'))
        )
        
        table['Horario que eu fui dormir'] = \
        table.apply(lambda x: x['Data'] + dt.timedelta(days = (x['Horario que eu fui dormir'].day) - 1, 
                                                hours = x['Horario que eu fui dormir'].hour, 
                                                minutes = x['Horario que eu fui dormir'].minute), axis=1)
        
        table['Hora que eu acordei'] = table['Hora que eu acordei'].fillna('00:00:00').map(lambda x: dt.datetime.strptime(str(x),'%H:%M:%S'))
        
        table['Hora que eu acordei'] = \
        table.apply(lambda x: x['Data'] + dt.timedelta(hours = x['Hora que eu acordei'].hour, 
                                                minutes = x['Hora que eu acordei'].minute), axis=1)
        
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

        table['Horas dormindo'] = table['Horas dormindo'].apply(btz.funcoes_data_frame().substituir_outliers())
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
