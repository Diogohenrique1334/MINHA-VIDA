import datetime as dt
import pandas as pd
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import statsmodels.stats.api as sms
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.compat import lzip
from scipy.stats import shapiro
import statsmodels

class funcoes_data_frame:

    def __init__(self):

        pass
  

    def tratar_datas(self,x):

        x = str(x)
      
        #cose o formato esteja em data e hora
        if len(x.split(' ')) == 2:
            return pd.to_datetime(x.split(' ')[0])
        
        # Caso o formato seja 'yyyy-mm-dddd'
        elif len(x.split('-')) == 3:
            return dt.datetime(int(x.split('-')[0]),int(x.split('-')[1]), int(x.split('-')[2]))
        
        # Caso o formato seja 'dd-mm-yyyy'
        elif len(x.split('-')) == 3 and len(x.split('-')[0]) == 2:
            return dt.datetime(int(x.split('-')[2]),int(x.split('-')[1]), int(x.split('-')[0]))
        
        # Caso o formato seja 'DD-MM-YY'

        elif len(x.split('-')) == 3 and len(x.split('-')[2]) == 2:
            return dt.datetime( (2000 + int(x.split('-')[2])), int(x.split('-')[1]), int(x.split('-')[0]))
        
        # Caso o formato seja 'dias desde 1900'

        elif len(x.split('/')) == 1:
            return dt.datetime(1900, 1, 1) + dt.timedelta(days=int(x.split('.')[0])-2)

        # Caso o formato seja 'DD/MM/YY'

        elif len(x.split('/')) == 3 and int(x.split('/')[2]) < 2000:
            return dt.datetime( (2000 + int(x.split('/')[2])), int(x.split('/')[1]), int(x.split('/')[0]))

        # Caso o formato seja 'DD/MM/YYYY'

        elif len(x.split('/')) == 3:
            return dt.datetime(int(x.split('/')[2]),int(x.split('/')[1]), int(x.split('/')[0]))

        else:
            raise x

        return x
    
    # Função para checar a assimetria dos dados e então tratar valores ausentes
    def trata_valores_ausentes(df):
        
        # Lista de variáveis com assimetria alta
        assimetria_alta = []
        
        # Lista de variáveis com assimetria moderada
        assimetria_moderada = []
        
        # Loop
        for i, j in df.skew().items():
            
            # Condição para assimetria alta
            if (j < -1) or (j > 1):
                
                # Coloca o nome da variável na lista
                assimetria_alta.append(i)
                
                # Preenche valores ausentes com a mediana
                df[i].fillna(df[i].median(), inplace = True)
                
            # Condição para assimetria moderada
            elif (-1 > j > -0.5) or (0.5 < j <  1):
                
                # Coloca o nome da variável na lista
                assimetria_moderada.append(i)
                
                # Preenche valores ausentes com a média
                df[i].fillna(df[i].mean(), inplace = True)
            else:
                pass
            
        print("\nVariáveis com assimetria alta:\n")
        print(assimetria_alta)
        print("\nVariáveis com assimetria moderada:\n")
        print(assimetria_moderada)
        print("\nValores ausentes:\n")
        print(df.isnull().sum())

    def colunas_por_delimitadores(self, df,coluna,delimitador):
    
        novas_colunas = df[coluna].map(lambda x: str(x).split(delimitador)).apply(pd.Series)

        df_novo = pd.merge(df,novas_colunas, left_index=True, right_index=True)

        df_novo_expandido = pd.melt(df_novo, id_vars = [x for x in df_novo.columns if not isinstance(x, int)]).reset_index(drop='index')
        
        return df_novo_expandido.dropna(axis=0, how='any')
    

    def substituir_outliers(valor):
        if pd.isna(valor):
            return valor
        # Definindo o limite de tempo de sono
        limite = pd.Timedelta(days=1)
        
        if valor > limite:
            return pd.NaT
        return valor

class funcoes_dados_n_estruturados:

    def __init__(self,caminho_arquivo):

        self.caminho_arquivo = caminho_arquivo
        
class funcoes_graficos_estatistica:

    def __init__(self):
        pass

    # Função para o plot da matriz de correlação
    def Corr_limite_inferior(df, dropDuplicates = True, xrot = 70, yrot = 0, label = 'Variable'):

        # Excluir correlações duplicadas mascarando os valores superiores à direita
        if dropDuplicates:
            mask = np.zeros_like(df, dtype = np.bool_)
            mask[np.triu_indices_from(mask)] = True

        # Definir cor do plano de fundo / estilo do gráfico
        sns.set_style(style = 'dark')
        fig, ax = plt.subplots(figsize = (14, 12))

        # Adiciona mapa de cores do vermelho ao azul
        plt.title("Matriz de Correlação")

        # Desenha gráfico de correlação com ou sem duplicatas
        if dropDuplicates:
            sns.heatmap(df, mask = mask, square = True, linewidth = .5, cbar_kws = {"shrink": .5}, ax = ax, annot=True)
            plt.xlabel(label)
            plt.ylabel(label)
            plt.xticks(rotation=xrot)
            plt.yticks(rotation=yrot)

        else:
            sns.heatmap(df, square = True, linewidth = .5, cbar_kws = {"shrink": .5}, ax = ax, annot=True)
            plt.xlabel(label)
            plt.ylabel(label)
            plt.xticks(rotation = xrot)
            plt.yticks(rotation = yrot)
        return
        
    # Função para o plot da relação da variável alvo com alguns atributos
    def Alvo_vs_atributosSelecionados(data, alvo, atributos, n):
        
        # Grupos de linhas com 3 (n) gráficos por linha
        row_groups = [atributos[i:i+n] for i in range(0, len(atributos), n)]

        # Loop pelos grupos de linhas para criar cada pair plot
        for ind in row_groups:
            plot = sns.pairplot(x_vars = ind, y_vars = alvo, data = data, kind = "reg", height = 3)

        return
    
class validacao_suposicoes_regressao:

    def __init__(self,modelo):

        self.modelo = modelo

    def linearidade(self):
        
        # Aplica o linear_rainbow
        lin_p = sms.linear_rainbow(self.modelo, frac = 0.5)[1]
        
        print(lin_p)
        
        # Inicializa a variável com Falha
        result = "Rejeitamos a H0 (Hipótese Nula). Isso indica que há evidências de heterocedasticidade e que a regressão não é homocedástica. A suposição não pode ser satisfeita."
        
        # Testa o resultado
        if lin_p > 0.05:
            result = "Sucesso! Falhamos em rejeitar a H0 (Hipótese Nula). Isso indica que a regressão é provavelmente homocedástica e a suposição está satisfeita."
            
        # Retorno
        return np.transpose(pd.DataFrame([[lin_p], [0.05], [result]],
                                        index = ['Valor-p', 'Alfa', 'Resultado'],
                                        columns = ['Valor-p do Rainbow Linearity Test'] ))
    
    def independencia_erros(self):
    

        residuos = self.modelo.resid

        # Valores previstos
        valores_previstos = self.modelo.fittedvalues

        # Plot
        plt.figure(figsize = (10,5))
        sns.residplot(x = valores_previstos, y = residuos, color = "green", lowess = True)
        plt.xlabel("Valores Previstos")
        plt.ylabel("Resíduos")
        plt.title("Plot Residual")
        plt.show()
        
        # Define o modelo
        resultado = statsmodels.stats.stattools.durbin_watson(residuos)
        
        print('Resultado do teste:', resultado)
        
        # Interprete o resultado
        if resultado < 1.9:
            print("Há evidências de autocorrelação positiva nos erros! Suposição não satisfeita!")
        elif resultado > 2.1:
            print("Há evidências de autocorrelação negativa nos erros! Suposição não satisfeita!")
        else:
            print("Não há evidências de autocorrelação nos erros! Suposição satisfeita!")

        return 
    # Função
    def homocedasticidade(y, x):
        
        # Estatísticas
        estatisticas = ["F statistic", "p-value"]
        
        # Teste
        teste_goldfeldquandt = sms.het_goldfeldquandt(y, x)
        
        resultado = lzip(estatisticas, teste_goldfeldquandt)
        
        pval = resultado[1][1]
        
        if pval < 0.05:
            print("Há evidências de heterocedasticidade (a regressão não é homocedástica) e rejeitamos a H0. Suposição não satisfeita!")
        else:
            print("Não há evidências de heterocedasticidade (a regressão é provavelmente homocedástica). Falhamos em rejeitar a H0. Suposição satisfeita!")
    
    def normalizacao_erros(residuos):
        
        # Aplica o teste
        resultado = shapiro(residuos)
        
        # Extrai o valor-p
        pval = resultado.pvalue
        
        print('Valor-p =', pval)
        
        if pval < 0.05:
            print("Rejeitamos a H0. Isso indica que há evidências de que os resíduos não seguem uma distribuição normal!")
        else:
            print("Falhamos em rejeitar a H0. Isso indica que os resíduos seguem uma distribuição normal. Suposição satisfeita!")
    # Função para checar o VIF de todas as variáveis
    def multicolinearidade(train):
        
        # Cria o dataframe
        vif = pd.DataFrame()
        
        # Alimenta cada coluna
        vif["feature"] = train.columns

        # Calcula VIF para cada variável
        vif["VIF"] = [variance_inflation_factor(train.values, i) for i in range(len(train.columns))]
        
        return vif
    
class ValidacaoSuposicoesRegressao:

    def __init__(self, modelo):
        self.modelo = modelo
        self.resultados = {
            "linearidade": self.linearidade(),
            "independencia_erros": self.independencia_erros(),
            "homocedasticidade": self.homocedasticidade(self.modelo.endog, self.modelo.exog),
            "normalizacao_erros": self.normalizacao_erros(self.modelo.resid),
            "multicolinearidade": self.multicolinearidade(pd.DataFrame(self.modelo.exog))
        }

    def linearidade(self):
        lin_p = sms.linear_rainbow(self.modelo, frac=0.5)[1]
        result = "Rejeitamos a H0. Há evidências de heterocedasticidade." if lin_p <= 0.05 else "Sucesso! Falhamos em rejeitar a H0."
        return np.transpose(pd.DataFrame([[lin_p, 0.05, result]], columns=['Valor-p do Rainbow Linearity Test', 'Alfa', 'Resultado']))

    def independencia_erros(self):
        residuos = self.modelo.resid
        valores_previstos = self.modelo.fittedvalues
        plt.figure(figsize=(10, 5))
        sns.residplot(x=valores_previstos, y=residuos, color="green", lowess=True)
        plt.xlabel("Valores Previstos")
        plt.ylabel("Resíduos")
        plt.title("Plot Residual")
        plt.show()
        resultado = statsmodels.stats.stattools.durbin_watson(residuos)
        interpretacao = "Não há evidências de autocorrelação nos erros!" if 1.9 <= resultado <= 2.1 else "Há evidências de autocorrelação nos erros!"
        return resultado, interpretacao
    
    def homocedasticidade(self, y, x):
        estatisticas = ["F statistic", "p-value"]
        teste_goldfeldquandt = sms.het_goldfeldquandt(y, x)
        resultado = dict(zip(estatisticas, teste_goldfeldquandt))
        interpretacao = "Não há evidências de heterocedasticidade." if resultado["p-value"] >= 0.05 else "Há evidências de heterocedasticidade."
        return resultado, interpretacao

    def normalizacao_erros(self, residuos):
        resultado = shapiro(residuos)
        interpretacao = "Os resíduos seguem uma distribuição normal." if resultado.pvalue >= 0.05 else "Os resíduos não seguem uma distribuição normal."
        return resultado.pvalue, interpretacao
    def multicolinearidade(self, train):
        vif = pd.DataFrame()
        vif["feature"] = train.columns
        vif["VIF"] = [variance_inflation_factor(train.values, i) for i in range(len(train.columns))]
        return vif
