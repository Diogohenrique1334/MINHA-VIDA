"""Cria colunas data_hora_acordei/data_hora_dormi se faltarem

Revision ID: d8e9f0a1b2c3
Revises: c7a1b2c3d4e5
Create Date: 2026-06-16 00:10:00.000000

Conserta uma inconsistência da história de migrações: a revisão 341eea223d28
dropou as colunas antigas de sono (TIME) mas nunca criou as novas
(data_hora_acordei/data_hora_dormi, DateTime) que o modelo usa. Em produção
essas colunas existem (criadas fora do Alembic), então usamos ADD COLUMN
IF NOT EXISTS: no-op onde já existem, criação onde faltam (bancos do zero).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'c7a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE minha_vida ADD COLUMN IF NOT EXISTS data_hora_acordei TIMESTAMP WITHOUT TIME ZONE')
    op.execute('ALTER TABLE minha_vida ADD COLUMN IF NOT EXISTS data_hora_dormi TIMESTAMP WITHOUT TIME ZONE')


def downgrade() -> None:
    op.execute('ALTER TABLE minha_vida DROP COLUMN IF EXISTS data_hora_dormi')
    op.execute('ALTER TABLE minha_vida DROP COLUMN IF EXISTS data_hora_acordei')
