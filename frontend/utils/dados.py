"""Acesso a dados do dashboard.

Centraliza a leitura do banco (antes duplicada em cada página) e reconstrói o
DataFrame "wide" que o dashboard espera, a partir do modelo relacional novo:
métricas vêm de `minha_vida` e os hábitos de `registros_habito` (pivotados).
"""
import os

import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# Colunas fixas do merge (tudo que não for essas é coluna de hábito).
_COLUNAS_FIXAS = {
    'user_phone_number', 'dia',
    'nota_humor', 'Nota_humor_fim_dia', 'data_hora_acordei', 'data_hora_dormi',
}


def _engine():
    return create_engine(os.getenv("DATABASE_URL"))


def carregar_habitos_meta():
    """Metadados dos hábitos (nome, categoria, ativo, ordem) por usuário."""
    return pd.read_sql(
        "SELECT user_phone_number, nome, categoria, ativo, ordem FROM habitos",
        _engine(),
    )


def carregar_dados():
    """Reconstrói o DataFrame wide (1 linha por usuário+dia): métricas + hábitos.

    Mantém os nomes de coluna que o resto do dashboard já espera, então
    `preparar_df` e as funções de gráfico seguem funcionando.
    """
    engine = _engine()

    # Métricas — a data local é derivada com a mesma expressão usada pelo bot,
    # garantindo alinhamento com a data de registros_habito.
    metrics = pd.read_sql(
        """
        SELECT user_phone_number,
               date(timezone('America/Sao_Paulo', data)) AS dia,
               nota_humor, "Nota_humor_fim_dia",
               data_hora_acordei, data_hora_dormi
        FROM minha_vida
        """,
        engine,
    )

    # Hábitos — pivotados para colunas (nome do hábito), valores 0/1.
    hab = pd.read_sql(
        """
        SELECT h.user_phone_number, r.data AS dia, h.nome, r.valor
        FROM registros_habito r
        JOIN habitos h ON h.id = r.habito_id
        """,
        engine,
    )
    if not hab.empty:
        hab_wide = hab.pivot_table(
            index=['user_phone_number', 'dia'], columns='nome',
            values='valor', aggfunc='max',
        ).reset_index()
    else:
        hab_wide = pd.DataFrame(columns=['user_phone_number', 'dia'])

    df = metrics.merge(hab_wide, on=['user_phone_number', 'dia'], how='outer')

    # Hábito não lançado num dia conta como "não feito" (0), igual ao modelo antigo.
    habito_cols = [c for c in df.columns if c not in _COLUNAS_FIXAS]
    for col in habito_cols:
        df[col] = df[col].fillna(0).astype(int)

    df['data'] = pd.to_datetime(df['dia'])
    return df.drop(columns=['dia'])
