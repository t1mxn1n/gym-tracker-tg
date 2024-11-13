"""1_init

Revision ID: 078c63800173
Revises: 
Create Date: 2024-11-13 17:59:48.677432

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '078c63800173'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('body_part',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=50), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name')
                    )
    op.create_table('user',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('user_name', sa.String(length=50), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('user_id')
                    )
    op.create_table('exercise',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('bp_id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=50), nullable=False),
                    sa.ForeignKeyConstraint(['bp_id'], ['body_part.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name')
                    )
    op.create_table('history',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('date', sa.Integer(), nullable=False),
                    sa.Column('bp_id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=50), nullable=False),
                    sa.ForeignKeyConstraint(['bp_id'], ['body_part.id'], ),
                    sa.ForeignKeyConstraint(['date'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name')
                    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('history')
    op.drop_table('exercise')
    op.drop_table('user')
    op.drop_table('body_part')
    # ### end Alembic commands ###