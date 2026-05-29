import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TenantDatabase(Base):
    __tablename__ = "tenant_databases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    db_name = Column(Text, nullable=False)
    db_type = Column(Text, nullable=False)
    conn_string = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(Text, default="pending")
    onboarded_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "db_type IN ('postgres', 'mongodb')",
            name="chk_db_type",
        ),
    )
