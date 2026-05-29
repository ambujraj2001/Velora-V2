"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "tenants",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key"),
    )

    op.create_table(
        "tenant_databases",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", UUID(), nullable=False),
        sa.Column("db_name", sa.Text(), nullable=False),
        sa.Column("db_type", sa.Text(), nullable=False),
        sa.Column("conn_string", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=True),
        sa.Column("onboarded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("db_type IN ('postgres', 'mongodb')", name="chk_db_type"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )

    op.create_table(
        "schema_embeddings",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", UUID(), nullable=False),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("chunk_type", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schema_embeddings_tenant_id", "schema_embeddings", ["tenant_id"])
    op.execute(
        """
        CREATE INDEX ix_schema_embeddings_embedding
        ON schema_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    op.create_table(
        "chat_history",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", UUID(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_history_tenant_session",
        "chat_history",
        ["tenant_id", "session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_history_tenant_session", table_name="chat_history")
    op.drop_table("chat_history")
    op.execute("DROP INDEX IF EXISTS ix_schema_embeddings_embedding")
    op.drop_index("ix_schema_embeddings_tenant_id", table_name="schema_embeddings")
    op.drop_table("schema_embeddings")
    op.drop_table("tenant_databases")
    op.drop_table("tenants")
