"""empty message

Revision ID: 38814fff4a36
Revises: c0c409627d4d
Create Date: 2022-08-13 07:05:49.407570

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38814fff4a36'
down_revision = 'c0c409627d4d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('show', sa.Column('show_id', sa.Integer(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('show', 'show_id')
    # ### end Alembic commands ###