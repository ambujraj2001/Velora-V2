import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=True)
    password_hash = Column(Text, nullable=True)
    api_key = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
