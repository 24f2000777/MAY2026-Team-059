"""add complaint_number to complaints

Revision ID: 0dd17ca8e5a2
Revises: 52331e1078d4
Create Date: 2026-08-11 00:56:30.115805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0dd17ca8e5a2'
down_revision: Union[str, Sequence[str], None] = '52331e1078d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adds a short, sequential, human-facing reference number to
    complaints (shown in the UI as e.g. "NGK-000123"), backed by a
    real DB sequence so concurrent inserts never collide - the
    existing UUID id stays the actual primary key/URL param, this is
    purely for display.

    Order: add the column nullable first, backfill every existing row
    in created_at order (oldest gets #1), point the sequence past the
    highest number just assigned, then lock the column down (default,
    NOT NULL, unique) now that every row already has a value.
    """
    op.execute("CREATE SEQUENCE complaint_number_seq")
    op.add_column("complaints", sa.Column("complaint_number", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE complaints
        SET complaint_number = numbered.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn
            FROM complaints
        ) AS numbered
        WHERE complaints.id = numbered.id
        """
    )
    op.execute(
        "SELECT setval('complaint_number_seq', COALESCE((SELECT MAX(complaint_number) FROM complaints), 0) + 1, false)"
    )

    op.alter_column(
        "complaints",
        "complaint_number",
        nullable=False,
        server_default=sa.text("nextval('complaint_number_seq')"),
    )
    op.create_unique_constraint(
        "uq_complaints_complaint_number", "complaints", ["complaint_number"]
    )
    op.execute("ALTER SEQUENCE complaint_number_seq OWNED BY complaints.complaint_number")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_complaints_complaint_number", "complaints", type_="unique")
    op.drop_column("complaints", "complaint_number")
    op.execute("DROP SEQUENCE IF EXISTS complaint_number_seq")
