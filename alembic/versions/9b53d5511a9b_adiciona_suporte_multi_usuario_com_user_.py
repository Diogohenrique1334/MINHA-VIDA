"""Adiciona suporte multi-usuario com user_phone_number

Revision ID: 9b53d5511a9b
Revises: aa305788aab6
Create Date: 2024-07-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b53d5511a9b'
down_revision = 'aa305788aab6'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona coluna usando batch mode
    with op.batch_alter_table('minha_vida') as batch_op:
        batch_op.add_column(sa.Column('user_phone_number', sa.String(), nullable=True))
    
    # Cria constraint única usando batch mode
    with op.batch_alter_table('minha_vida') as batch_op:
        batch_op.create_unique_constraint('_user_date_uc', ['user_phone_number', 'data'])


def downgrade():
    # Remove constraint usando batch mode
    with op.batch_alter_table('minha_vida') as batch_op:
        batch_op.drop_constraint('_user_date_uc', type_='unique')
    
    # Remove coluna usando batch mode
    with op.batch_alter_table('minha_vida') as batch_op:
        batch_op.drop_column('user_phone_number')