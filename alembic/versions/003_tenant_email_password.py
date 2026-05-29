"""Add email and password to tenants

Revision ID: 003
Revises: 002
Create Date: 2026-05-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("email", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("password_hash", sa.Text(), nullable=True))
    op.create_index("ix_tenants_email", "tenants", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenants_email", table_name="tenants")
    op.drop_column("tenants", "password_hash")
    op.drop_column("tenants", "email")
