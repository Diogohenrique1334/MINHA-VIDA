"""Camada de acesso a dados dos hábitos dinâmicos.

Concentra as queries das tabelas `habitos` e `registros_habito`, mantendo o
webhook (`whats.py`) e os scripts livres de SQL espalhado.
"""
import datetime

from backend.models import Habito, RegistroHabito

# As 4 hipercategorias usadas no dashboard (Hiper_categoria).
CATEGORIAS = ["Saúde do corpo", "Evolução pessoal", "Lazer", "Saúde da mente"]

# Hábitos padrão (semente). `coluna_antiga` mapeia para a coluna Boolean dormente
# em `minha_vida`, usada apenas no backfill do histórico. `nome` usa o nome de
# exibição que o dashboard já espera.
HABITOS_PADRAO = [
    {"nome": "Academia",           "categoria": "Saúde do corpo",    "coluna_antiga": "Academia",             "ordem": 1, "emoji": "🏋️"},
    {"nome": "Exercício aeróbico", "categoria": "Saúde do corpo",    "coluna_antiga": "Exercício_aerobico",   "ordem": 2, "emoji": "🏃"},
    {"nome": "Alimentação saudável","categoria": "Saúde do corpo",   "coluna_antiga": "Alimentação_saudavel", "ordem": 3, "emoji": "🥗"},
    {"nome": "Consumo de água",    "categoria": "Saúde do corpo",    "coluna_antiga": "Consumo_de_agua",      "ordem": 4, "emoji": "💧"},
    {"nome": "Estudar",            "categoria": "Evolução pessoal",  "coluna_antiga": "Estudar",              "ordem": 5, "emoji": "📚"},
    {"nome": "Leitura",            "categoria": "Evolução pessoal",  "coluna_antiga": "Leitura",              "ordem": 6, "emoji": "📖"},
    {"nome": "Atividade sexual",   "categoria": "Lazer",             "coluna_antiga": "Atividade_sexual",     "ordem": 7, "emoji": "❤️"},
    {"nome": "secreto",            "categoria": "Lazer",             "coluna_antiga": "secreto",              "ordem": 8, "emoji": "🚬"},
]


def semear_habitos_padrao(session, user_phone):
    """Cria os HABITOS_PADRAO que ainda não existirem para o usuário (idempotente).

    Retorna o número de hábitos criados.
    """
    criados = 0
    for padrao in HABITOS_PADRAO:
        existe = session.query(Habito).filter(
            Habito.user_phone_number == user_phone,
            Habito.nome == padrao["nome"],
        ).first()
        if existe:
            continue
        criados += 1
        session.add(Habito(
            user_phone_number=user_phone,
            nome=padrao["nome"],
            categoria=padrao["categoria"],
            tipo="sim_nao",
            ativo=True,
            ordem=padrao["ordem"],
            emoji=padrao.get("emoji"),
        ))
    if criados:
        session.commit()
    return criados


def garantir_habitos_padrao(session, user_phone):
    """Semeia os hábitos padrão apenas se o usuário ainda não tiver nenhum hábito.

    Evita menu vazio para usuários novos, sem reintroduzir hábitos que o usuário
    tenha removido/congelado de propósito. Retorna o número de hábitos criados.
    """
    ja_tem = session.query(Habito).filter(Habito.user_phone_number == user_phone).count()
    if ja_tem:
        return 0
    return semear_habitos_padrao(session, user_phone)


def listar_habitos(session, user_phone, apenas_ativos=False):
    """Lista os hábitos de um usuário, ordenados por `ordem` e `nome`."""
    query = session.query(Habito).filter(Habito.user_phone_number == user_phone)
    if apenas_ativos:
        query = query.filter(Habito.ativo.is_(True))
    return query.order_by(Habito.ordem, Habito.nome).all()


def listar_habitos_ativos(session, user_phone):
    """Lista apenas os hábitos ativos (para o checklist diário)."""
    return listar_habitos(session, user_phone, apenas_ativos=True)


def buscar_habito(session, habito_id):
    """Retorna o hábito pelo id, ou None."""
    return session.query(Habito).filter(Habito.id == habito_id).first()


def criar_habito(session, user_phone, nome, categoria, emoji=None):
    """Cria um hábito novo. Se já existir (mesmo user + nome), reativa o existente.

    Retorna (habito, criado: bool).
    """
    nome = nome.strip()
    existente = session.query(Habito).filter(
        Habito.user_phone_number == user_phone,
        Habito.nome == nome,
    ).first()
    if existente:
        if not existente.ativo:
            existente.ativo = True
            session.commit()
        return existente, False

    ordem_atual = session.query(Habito).filter(
        Habito.user_phone_number == user_phone
    ).count()
    habito = Habito(
        user_phone_number=user_phone,
        nome=nome,
        categoria=categoria,
        tipo="sim_nao",
        ativo=True,
        ordem=ordem_atual + 1,
        emoji=emoji,
    )
    session.add(habito)
    session.commit()
    return habito, True


def set_ativo(session, habito_id, ativo):
    """Congela (ativo=False) ou reativa (ativo=True) um hábito."""
    habito = buscar_habito(session, habito_id)
    if habito is None:
        return None
    habito.ativo = ativo
    session.commit()
    return habito


def buscar_registro_habito(session, habito_id, data):
    """Retorna o lançamento de um hábito numa data, ou None."""
    return session.query(RegistroHabito).filter(
        RegistroHabito.habito_id == habito_id,
        RegistroHabito.data == data,
    ).first()


def registrar_valor(session, habito_id, data, valor):
    """Upsert do lançamento (habito_id, data) com `valor`. Retorna o registro."""
    registro = buscar_registro_habito(session, habito_id, data)
    if registro is None:
        registro = RegistroHabito(habito_id=habito_id, data=data, valor=valor)
        session.add(registro)
    else:
        registro.valor = valor
    session.commit()
    return registro


def alternar_valor(session, habito_id, data):
    """Alterna o lançamento de um hábito na data (sem registro -> True; senão inverte).

    Retorna o novo valor (bool).
    """
    registro = buscar_registro_habito(session, habito_id, data)
    novo_valor = not registro.valor if registro is not None else True
    registrar_valor(session, habito_id, data, novo_valor)
    return novo_valor


def habitos_lancados_no_dia(session, user_phone, data):
    """Quantidade de hábitos com lançamento (qualquer valor) num dia."""
    return session.query(RegistroHabito).join(Habito).filter(
        Habito.user_phone_number == user_phone,
        RegistroHabito.data == data,
    ).count()
