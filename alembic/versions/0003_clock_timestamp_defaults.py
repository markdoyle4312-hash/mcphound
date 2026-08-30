"""use clock_timestamp() instead of now() for observation-ledger defaults

now() is frozen at transaction start in Postgres, so rows inserted later in
the same transaction as a prior write (e.g. a Hash and then a Scan within one
registry-scan run) can tie on timestamp, breaking any "is this newer than
that" comparison done within a single transaction. clock_timestamp() reflects
real per-statement wall-clock time instead.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-08-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("hashes", "observed_at", server_default=sa.text("clock_timestamp()"))
    op.alter_column("scans", "scanned_at", server_default=sa.text("clock_timestamp()"))
    op.alter_column("server_scores", "computed_at", server_default=sa.text("clock_timestamp()"))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("server_scores", "computed_at", server_default=sa.text("now()"))
    op.alter_column("scans", "scanned_at", server_default=sa.text("now()"))
    op.alter_column("hashes", "observed_at", server_default=sa.text("now()"))
