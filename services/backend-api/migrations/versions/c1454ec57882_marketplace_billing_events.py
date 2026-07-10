"""marketplace billing events (issue #71)

Revision ID: c1454ec57882
Revises: c11f09a3a44d
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1454ec57882'
down_revision: Union[str, None] = 'c11f09a3a44d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'billing_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('rfp_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['rfp_id'], ['rfps.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_billing_events_organization_id'), 'billing_events', ['organization_id'], unique=False
    )
    op.create_index(op.f('ix_billing_events_rfp_id'), 'billing_events', ['rfp_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_billing_events_rfp_id'), table_name='billing_events')
    op.drop_index(op.f('ix_billing_events_organization_id'), table_name='billing_events')
    op.drop_table('billing_events')
