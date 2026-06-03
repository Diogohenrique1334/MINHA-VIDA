import pandas as pd
import datetime
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import pytz

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.models import Minha_vida
from backend.dependencies import pegar_sessao

ARQUIVO_EXCEL = Path(__file__).parent / 'Planilha_da_vida_dias_zerados.xlsx'
FUSO_BRASIL = pytz.timezone('America/Sao_Paulo')

print("Iniciando importação para o banco de dados de produção (PostgreSQL)...")

if not os.getenv("DATABASE_URL"):
    print("ERRO CRÍTICO: DATABASE_URL não encontrada.")
    exit()

with pegar_sessao() as session:
    try:
        df = pd.read_excel(ARQUIVO_EXCEL)
        print(f"Arquivo lido: {len(df)} linhas.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{ARQUIVO_EXCEL}' não encontrado.")
        exit()

    try:
        registros_adicionados = 0
        for index, row in df.iterrows():
            def para_booleano(valor):
                if pd.isna(valor): return None
                return str(valor).lower() in ['sim', 'true', '1.0', '1', 'verdadeiro']

            def para_horario(valor):
                if pd.isna(valor): return None
                if isinstance(valor, datetime.time): return valor
                try:
                    return datetime.datetime.strptime(str(valor), '%H:%M:%S').time()
                except:
                    try:
                        return datetime.datetime.strptime(str(valor), '%H:%M').time()
                    except:
                        return None

            data_registro = pd.to_datetime(row['Data']).date()

            data_hora_acordei_final = None
            hora_acordei = para_horario(row['Hora que eu acordei'])
            if hora_acordei:
                data_hora_acordei_final = FUSO_BRASIL.localize(datetime.datetime.combine(data_registro, hora_acordei))

            data_hora_dormi_final = None
            hora_dormir = para_horario(row['Horario que eu fui dormir'])
            if hora_dormir:
                dia_anterior = data_registro - datetime.timedelta(days=1)
                data_hora_dormi_final = FUSO_BRASIL.localize(datetime.datetime.combine(dia_anterior, hora_dormir))

            novo_registro = Minha_vida(
                data=FUSO_BRASIL.localize(datetime.datetime.combine(data_registro, datetime.time(0, 0))),
                user_phone_number=str(row['user_phone_number']),
                nota_humor=float(row['Nota do humor']) if pd.notna(row['Nota do humor']) else None,
                secreto=para_booleano(row['secreto']),
                Estudar=para_booleano(row['Estudar']),
                Leitura=para_booleano(row['Leitura']),
                Exercício_aerobico=para_booleano(row['Exercício aeróbico']),
                Alimentação_saudavel=para_booleano(row['Alimentação saudável']),
                Consumo_de_agua=para_booleano(row['Consumo de água']),
                Academia=para_booleano(row['Academia']),
                Atividade_sexual=para_booleano(row['Atividade sexual']),
                data_hora_acordei=data_hora_acordei_final,
                data_hora_dormi=data_hora_dormi_final,
                Nota_humor_fim_dia=float(row['Nota do humor fim do dia']) if pd.notna(row['Nota do humor fim do dia']) else None
            )
            session.add(novo_registro)
            registros_adicionados += 1

        session.commit()
        print(f"SUCESSO: {registros_adicionados} registros adicionados.")
    except Exception as e:
        print(f"ERRO: {e}")
        session.rollback()
