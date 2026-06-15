"""Cria tabelas habitos e registros_habito (habitos dinamicos)

Revision ID: c7a1b2c3d4e5
Revises: 9b53d5511a9b
Create Date: 2026-06-16 00:00:00.000000

Migracao aditiva: cria as tabelas do modelo relacional de habitos. NAO mexe
nas colunas Boolean antigas de minha_vida (ficam dormentes ate um cleanup
posterior). O backfill dos dados historicos roda via backend/scripts/migrar_habitos.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = '9b53d5511a9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'habitos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_phone_number', sa.String(), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('categoria', sa.String(), nullable=False),
        sa.Column('tipo', sa.String(), nullable=False, server_default='sim_nao'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('emoji', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_phone_number', 'nome', name='_user_habito_uc'),
    )
    op.create_table(
        'registros_habito',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('habito_id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('valor', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['habito_id'], ['habitos.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('habito_id', 'data', name='_habito_data_uc'),
    )


def downgrade() -> None:
    op.drop_table('registros_habito')
    op.drop_table('habitos')
