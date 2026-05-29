import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

from app.database import Base


class SchemaEmbedding(Base):
    __tablename__ = "schema_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    table_name = Column(Text, nullable=False)
    chunk_type = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024))
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_schema_embeddings_tenant_id", "tenant_id"),
    )
