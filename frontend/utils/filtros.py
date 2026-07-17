"""Camada de filtros da sidebar (compartilhada pelas 3 páginas).

Monta o Painel de filtros - seletor de usuário (Diogo/Michele), mês e hora do
despertar - e devolve o DataFrame já filtrado e indexado por Data. Antes esse
bloco estava copiado em Habitos.py, Humor.py e Sono.py; centralizar evita
divergência entre as páginas (padrão do BDC: servicos/filtros.py).
"""
import streamlit as st

# Nome de exibição -> telefone (para buscar metadados de hábitos por usuário).
USUARIO_PARA_TELEFONE = {"Diogo": "5511959536031", "Michele": "5511991422452"}


def _usuarios_disponiveis(df):
    """Usuários que realmente têm dados, com Diogo primeiro (default)."""
    presentes = [u for u in df["user_phone_number"].dropna().unique().tolist()]
    ordenados = [u for u in ("Diogo", "Michele") if u in presentes]
    # Qualquer usuário extra fora da lista conhecida entra ao final.
    ordenados += [u for u in presentes if u not in ordenados]
    return ordenados or ["Diogo"]


def render_filtros(df, key_prefix="", imagem=None):
    """Renderiza o painel de filtros e retorna (df_filtrado_indexado, usuario).

    df: DataFrame já tratado por `preparar_df` (todos os usuários).
    key_prefix: prefixo único das keys dos widgets (evita colisão entre páginas).
    imagem: imagem opcional exibida na sidebar (decorativa).

    Retorna o DataFrame filtrado por usuário/mês/hora e indexado por 'Data'.
    """
    st.sidebar.title("Painel de filtros")

    usuarios = _usuarios_disponiveis(df)
    usuario = st.sidebar.selectbox(
        "Selecione o usuário", usuarios, index=0, key=f"{key_prefix}usuario"
    )

    if imagem is not None:
        st.sidebar.image(imagem, caption="-------------------------------------")

    df_user = df[df["user_phone_number"] == usuario]

    meses = st.sidebar.multiselect(
        "Selecione os meses de análise",
        df_user["Data"].dt.strftime("%m - %Y").unique(),
        key=f"{key_prefix}meses",
    )
    df_filtrado = df_user[df_user["mes"].isin(meses)] if meses else df_user
    df_filtrado = df_filtrado.set_index("Data")

    horas = st.sidebar.multiselect(
        "Selecione a hora do despertar",
        sorted(
            df_filtrado[df_filtrado["Hora que eu acordei"].dt.hour != 0][
                "Hora que eu acordei"
            ].dt.hour.unique()
        ),
        key=f"{key_prefix}hora_despertar",
    )
    if horas:
        df_filtrado = df_filtrado[df_filtrado["Hora que eu acordei"].dt.hour.isin(horas)]

    return df_filtrado, usuario
