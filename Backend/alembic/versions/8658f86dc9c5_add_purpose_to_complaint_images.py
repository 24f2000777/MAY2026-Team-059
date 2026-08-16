"""add purpose to complaint_images

Revision ID: 8658f86dc9c5
Revises: 0dd17ca8e5a2
Create Date: 2026-08-16 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8658f86dc9c5'
down_revision: Union[str, Sequence[str], None] = '0dd17ca8e5a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'complaint_images',
        sa.Column('purpose', sa.String(length=20), server_default='citizen_evidence', nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('complaint_images', 'purpose')
