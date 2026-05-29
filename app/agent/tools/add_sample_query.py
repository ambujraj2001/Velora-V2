import uuid

from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.models.schema_embedding import SchemaEmbedding
from app.nvidia import get_embedder

log = get_logger(__name__)


def build_add_sample_query_tool(tenant_id: str, db_session: Session) -> StructuredTool:
    def _make_fn(t_id=tenant_id, sess=db_session):
        def add_sample_query(question: str, query: str, table_name: str) -> str:
            log.info(
                "tool.add_sample_query.begin",
                tenant_id=t_id,
                table_name=table_name,
                question_length=len(question),
            )
            try:
                text = (
                    f"Question: {question}\n"
                    f"Query: {query}\n"
                    f"Table/Collection: {table_name}"
                )
                embedder = get_embedder()
                vector = embedder.embed_query(text)

                tenant_uuid = uuid.UUID(t_id) if isinstance(t_id, str) else t_id
                row = SchemaEmbedding(
                    tenant_id=tenant_uuid,
                    table_name=table_name,
                    chunk_type="sample_query",
                    content=text,
                    embedding=vector,
                    metadata_={"auto_added": True, "source": "agent_feedback"},
                )
                sess.add(row)
                sess.commit()
                log.info(
                    "tool.add_sample_query.complete",
                    tenant_id=t_id,
                    table_name=table_name,
                )
                return "Sample query stored successfully."
            except Exception as e:
                sess.rollback()
                log.exception(
                    "tool.add_sample_query.failed",
                    tenant_id=t_id,
                    table_name=table_name,
                    error=str(e),
                )
                return f"Could not store sample query: {e}"

        return add_sample_query

    fn = _make_fn()

    return StructuredTool.from_function(
        func=fn,
        name="add_sample_query",
        description=(
            "After successfully answering a question with a verified "
            "correct query, call this to store the question-query pair. "
            "This improves future accuracy for similar questions. "
            "Only call after confirmed correct results."
        ),
    )
