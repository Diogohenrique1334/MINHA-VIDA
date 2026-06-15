"""Backfill do modelo relacional de hábitos.

Semeia a tabela `habitos` (um conjunto padrão por usuário) e migra os dados
históricos das colunas Boolean dormentes de `minha_vida` para `registros_habito`.

Idempotente: pode rodar mais de uma vez sem duplicar. Use --dry-run para simular.

Uso:
    python -m backend.scripts.migrar_habitos --dry-run
    python -m backend.scripts.migrar_habitos
"""
import argparse
import os
import sys

from sqlalchemy import func

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.models import Minha_vida, Habito, RegistroHabito
from backend.dependencies import pegar_sessao
from backend.habitos_repo import HABITOS_PADRAO, semear_habitos_padrao


def usuarios_distintos(session):
    """Telefones distintos que têm registros em minha_vida."""
    linhas = session.query(Minha_vida.user_phone_number).distinct().all()
    return [u for (u,) in linhas if u]


def semear_habitos(session, user_phone, dry_run):
    """Garante que os HABITOS_PADRAO existam para o usuário. Retorna nº criados."""
    if dry_run:
        # Apenas conta quantos seriam criados, sem gravar.
        nomes = {n for (n,) in session.query(Habito.nome).filter(
            Habito.user_phone_number == user_phone).all()}
        return sum(1 for p in HABITOS_PADRAO if p["nome"] not in nomes)
    return semear_habitos_padrao(session, user_phone)


def mapa_habito_id(session, user_phone):
    """Dict {nome: habito_id} do usuário."""
    habitos = session.query(Habito).filter(Habito.user_phone_number == user_phone).all()
    return {h.nome: h.id for h in habitos}


def backfill_registros(session, dry_run):
    """Cria registros_habito a partir das colunas antigas. Retorna nº inseridos."""
    # (habito_id, data) já existentes — para idempotência.
    existentes = {
        (hid, data) for (hid, data) in session.query(
            RegistroHabito.habito_id, RegistroHabito.data
        ).all()
    }

    # Linhas de minha_vida com a data local (mesma expressão usada pelo app).
    linhas = session.query(
        Minha_vida,
        func.date(func.timezone('America/Sao_Paulo', Minha_vida.data)).label('dia'),
    ).all()

    # Cache de mapas por usuário.
    mapas = {}
    inseridos = 0
    for registro, dia in linhas:
        user = registro.user_phone_number
        if user not in mapas:
            mapas[user] = mapa_habito_id(session, user)
        habito_por_nome = mapas[user]

        for padrao in HABITOS_PADRAO:
            valor = getattr(registro, padrao["coluna_antiga"], None)
            if valor is None:
                continue
            habito_id = habito_por_nome.get(padrao["nome"])
            if habito_id is None:
                continue
            if (habito_id, dia) in existentes:
                continue
            inseridos += 1
            existentes.add((habito_id, dia))
            if not dry_run:
                session.add(RegistroHabito(habito_id=habito_id, data=dia, valor=bool(valor)))

    if not dry_run:
        session.commit()
    return inseridos


def main():
    parser = argparse.ArgumentParser(description="Backfill de hábitos dinâmicos.")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar.")
    args = parser.parse_args()

    if not os.getenv("DATABASE_URL"):
        print("ERRO CRÍTICO: DATABASE_URL não definida.")
        sys.exit(1)

    modo = "DRY-RUN (nada será gravado)" if args.dry_run else "EXECUÇÃO REAL"
    print(f"=== Backfill de hábitos — {modo} ===")

    with pegar_sessao() as session:
        usuarios = usuarios_distintos(session)
        print(f"Usuários encontrados: {len(usuarios)} -> {usuarios}")

        total_habitos = 0
        for user in usuarios:
            criados = semear_habitos(session, user, args.dry_run)
            total_habitos += criados
            print(f"  {user}: {criados} hábito(s) semeado(s)")

        inseridos = backfill_registros(session, args.dry_run)
        print(f"Hábitos semeados: {total_habitos}")
        print(f"Registros de hábito inseridos: {inseridos}")
        print("OK." if not args.dry_run else "Dry-run concluído (nenhuma alteração).")


if __name__ == "__main__":
    main()
