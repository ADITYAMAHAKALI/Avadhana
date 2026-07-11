"""comment parent_comment_id (threading, issue #98)

Revision ID: f6578bbbc579
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6578bbbc579'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable self-referential FK — null means a top-level reply to the
    # post (existing behavior, unaffected). No server_default needed
    # (unlike the `hidden` boolean columns added in da05f3e09e10):
    # NULL is precisely the correct backfilled value for every existing
    # comment row, since none of them had a parent before this migration.
    op.add_column('comments', sa.Column('parent_comment_id', sa.String(length=36), nullable=True))
    op.create_index(
        op.f('ix_comments_parent_comment_id'), 'comments', ['parent_comment_id'], unique=False
    )
    op.create_foreign_key(
        'fk_comments_parent_comment_id_comments',
        'comments',
        'comments',
        ['parent_comment_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_comments_parent_comment_id_comments', 'comments', type_='foreignkey')
    op.drop_index(op.f('ix_comments_parent_comment_id'), table_name='comments')
    op.drop_column('comments', 'parent_comment_id')
