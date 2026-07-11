"""resolution objections (issue #100 — problem lifecycle protocol)

Revision ID: 866f3c167cb7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '866f3c167cb7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('resolution_objections',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('problem_id', sa.String(length=36), nullable=False),
    sa.Column('objecting_user_id', sa.String(length=36), nullable=False),
    sa.Column('raised_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
    sa.ForeignKeyConstraint(['objecting_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resolution_objections_problem_id'), 'resolution_objections', ['problem_id'], unique=False)
    op.create_index(op.f('ix_resolution_objections_objecting_user_id'), 'resolution_objections', ['objecting_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_resolution_objections_objecting_user_id'), table_name='resolution_objections')
    op.drop_index(op.f('ix_resolution_objections_problem_id'), table_name='resolution_objections')
    op.drop_table('resolution_objections')
