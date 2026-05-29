import uuid

from sqlalchemy.orm import Session

from app.logging import get_logger
from app.models.schema_embedding import SchemaEmbedding
from app.nvidia import get_embedder

log = get_logger(__name__)


def _build_ddl_chunk(table_name: str, table_schema: dict, db_type: str) -> str:
    if db_type == "postgres":
        col_parts = []
        for col in table_schema.get("columns", []):
            part = f"{col['name']} ({col['type']})"
            if not col.get("nullable"):
                part += " [NOT NULL]"
            col_parts.append(part)
        fk_parts = []
        for fk in table_schema.get("foreign_keys", []):
            fk_parts.append(f"{fk['column']} → {fk['references']}")
        fk_line = ", ".join(fk_parts) if fk_parts else "none"
        return (
            f"Table: {table_name}\n"
            f"Columns: {', '.join(col_parts)}\n"
            f"Foreign keys: {fk_line}"
        )
    else:
        field_parts = []
        for col in table_schema.get("columns", []):
            field_parts.append(f"{col['name']} ({col['type']})")
        return f"Collection: {table_name}\nFields: {', '.join(field_parts)}"


def _build_description_chunk(
    table_name: str, enriched: dict, db_type: str
) -> str:
    questions = enriched.get("business_questions", [])
    question_lines = "\n".join(f"- {q}" for q in questions)
    return (
        f"Table: {table_name} ({db_type})\n"
        f"Description: {enriched.get('description', '')}\n"
        f"Useful for answering:\n{question_lines}"
    )


def _build_sample_query_chunk(
    question: str, query: str, table_name: str
) -> str:
    return (
        f"Question: {question}\n"
        f"Query: {query}\n"
        f"Table/Collection: {table_name}"
    )


def embed_and_store(
    tenant_id: str,
    table_name: str,
    introspected: dict,
    enriched: dict,
    db_type: str,
    db_session: Session,
) -> int:
    log.info(
        "onboarding.embed.begin",
        tenant_id=tenant_id,
        table_name=table_name,
        db_type=db_type,
    )
    embedder = get_embedder()
    chunks: list[tuple[str, str]] = []

    ddl_text = _build_ddl_chunk(table_name, introspected, db_type)
    chunks.append(("ddl", ddl_text))

    desc_text = _build_description_chunk(table_name, enriched, db_type)
    chunks.append(("description", desc_text))

    for sample in enriched.get("sample_queries", []):
        if sample.get("question") and sample.get("query"):
            sq_text = _build_sample_query_chunk(
                sample["question"], sample["query"], table_name
            )
            chunks.append(("sample_query", sq_text))

    tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    stored = 0

    for chunk_type, content in chunks:
        vector = embedder.embed_query(content)
        row = SchemaEmbedding(
            tenant_id=tenant_uuid,
            table_name=table_name,
            chunk_type=chunk_type,
            content=content,
            embedding=vector,
            metadata_={"db_type": db_type, "table": table_name},
        )
        db_session.add(row)
        stored += 1
        log.debug(
            "onboarding.embed.chunk",
            tenant_id=tenant_id,
            table_name=table_name,
            chunk_type=chunk_type,
            content_length=len(content),
        )

    log.info(
        "onboarding.embed.complete",
        tenant_id=tenant_id,
        table_name=table_name,
        chunks_stored=stored,
    )
    return stored
