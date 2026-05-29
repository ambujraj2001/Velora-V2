import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_history_tenant_session", "tenant_id", "session_id"),
    )
