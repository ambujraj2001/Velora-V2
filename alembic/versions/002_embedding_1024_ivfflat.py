"""Switch embeddings to 1024 dims with ivfflat index

Revision ID: 002
Revises: 001
Create Date: 2026-05-30
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Old 4096-dim vectors are incompatible with the new model; re-onboard tenants.
    op.execute("DELETE FROM schema_embeddings")
    op.execute(
        "ALTER TABLE schema_embeddings "
        "ALTER COLUMN embedding TYPE vector(1024) "
        "USING NULL"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_schema_embeddings_embedding
        ON schema_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_schema_embeddings_embedding")
    op.execute("DELETE FROM schema_embeddings")
    op.execute(
        "ALTER TABLE schema_embeddings "
        "ALTER COLUMN embedding TYPE vector(4096) "
        "USING NULL"
    )
