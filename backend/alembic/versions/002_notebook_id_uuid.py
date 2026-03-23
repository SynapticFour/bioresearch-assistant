"""Convert notebook id from VARCHAR to UUID.

Revision ID: 002
Revises: 001
Create Date: 2026-03-02
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (e.g. HelixTest CI): 001 already uses String(36); no ALTER TYPE.
        return
    op.execute("ALTER TABLE notebooks ALTER COLUMN id TYPE UUID USING id::uuid")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE notebooks ALTER COLUMN id TYPE VARCHAR(36) USING id::varchar")
