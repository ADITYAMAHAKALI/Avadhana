"""marketplace match runs and solution matches (issue #68)

Revision ID: a1b2c3d4e5f6
Revises: f02dd236afbf
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f02dd236afbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'match_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rfp_id', sa.String(length=36), nullable=False),
        sa.Column('triggered_by', sa.String(length=36), nullable=False),
        sa.Column('model_versions_used', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.String(length=2000), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['rfp_id'], ['rfps.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_match_runs_rfp_id'), 'match_runs', ['rfp_id'], unique=False)

    op.create_table(
        'solution_matches',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('match_run_id', sa.String(length=36), nullable=False),
        sa.Column('solution_id', sa.String(length=36), nullable=False),
        sa.Column('final_rrf_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('signal_scores', sa.JSON(), nullable=False),
        sa.Column('signal_ranks', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['match_run_id'], ['match_runs.id'], ),
        sa.ForeignKeyConstraint(['solution_id'], ['solutions.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_solution_matches_match_run_id'), 'solution_matches', ['match_run_id'], unique=False
    )
    op.create_index(
        op.f('ix_solution_matches_solution_id'), 'solution_matches', ['solution_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_solution_matches_solution_id'), table_name='solution_matches')
    op.drop_index(op.f('ix_solution_matches_match_run_id'), table_name='solution_matches')
    op.drop_table('solution_matches')
    op.drop_index(op.f('ix_match_runs_rfp_id'), table_name='match_runs')
    op.drop_table('match_runs')
