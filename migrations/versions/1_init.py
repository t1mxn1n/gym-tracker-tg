"""init

Revision ID: 1
Revises: 
Create Date: 2025-01-08 16:52:50.547147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BP = [
    {"name": "Грудь"},
    {"name": "Спина"},
    {"name": "Бицепс"},
    {"name": "Трицепс"},
    {"name": "Плечи"},
    {"name": "Ноги"},
    {"name": "Другое"}
]


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    body_part = op.create_table('body_part',
                                sa.Column('id', sa.Integer(), nullable=False),
                                sa.Column('name', sa.String(length=50), nullable=False),
                                sa.PrimaryKeyConstraint('id'),
                                sa.UniqueConstraint('name')
                                )
    op.bulk_insert(body_part, BP)
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
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('bp_id', sa.Integer(), nullable=False),
                    sa.Column('exercise_id', sa.Integer(), nullable=False),
                    sa.Column('note', sa.String(length=50), nullable=False),
                    sa.ForeignKeyConstraint(['bp_id'], ['body_part.id'], ),
                    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('history')
    op.drop_table('exercise')
    op.drop_table('user')
    op.drop_table('body_part')
    # ### end Alembic commands ###
