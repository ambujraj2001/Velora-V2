import uuid
from collections import defaultdict

from langchain_core.tools import StructuredTool
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.nvidia import get_embedder

log = get_logger(__name__)


def build_retrieve_schema_tool(tenant_id: str, db_session: Session) -> StructuredTool:
    def _make_fn(t_id=tenant_id, sess=db_session):
        def retrieve_schema(question: str) -> str:
            log.info(
                "tool.retrieve_schema.begin",
                tenant_id=t_id,
                question_length=len(question),
            )
            try:
                embedder = get_embedder()
                question_vector = embedder.embed_query(question)
                vector_literal = "[" + ",".join(str(v) for v in question_vector) + "]"

                tenant_uuid = uuid.UUID(t_id) if isinstance(t_id, str) else t_id

                # Get similarity-ranked results (generous limit to cover multi-table JOINs)
                result = sess.execute(
                    text(
                        """
                        SELECT content, chunk_type, table_name, metadata
                        FROM schema_embeddings
                        WHERE tenant_id = :tenant_id
                        ORDER BY embedding <=> CAST(:question_vector AS vector)
                        LIMIT 20
                        """
                    ),
                    {
                        "tenant_id": tenant_uuid,
                        "question_vector": vector_literal,
                    },
                )
                rows = result.fetchall()

                # Also fetch ALL DDL chunks so we never miss a table's structure
                ddl_result = sess.execute(
                    text(
                        """
                        SELECT content, chunk_type, table_name, metadata
                        FROM schema_embeddings
                        WHERE tenant_id = :tenant_id AND chunk_type = 'ddl'
                        """
                    ),
                    {"tenant_id": tenant_uuid},
                )
                ddl_rows = ddl_result.fetchall()
            except Exception as e:
                log.exception(
                    "tool.retrieve_schema.failed",
                    tenant_id=t_id,
                    error=str(e),
                )
                return f"Schema search error: {e}"

            grouped: dict[str, dict] = defaultdict(
                lambda: {"ddl": [], "description": [], "sample_query": [], "db_type": "postgres"}
            )

            # Merge DDL rows first (ensures every table has its structure)
            for row in ddl_rows:
                content, chunk_type, table_name, metadata = row
                db_type = (metadata or {}).get("db_type", "postgres")
                grouped[table_name]["db_type"] = db_type
                if content not in grouped[table_name]["ddl"]:
                    grouped[table_name]["ddl"].append(content)

            # Merge similarity-ranked rows (descriptions + sample queries for relevant tables)
            for row in rows:
                content, chunk_type, table_name, metadata = row
                db_type = (metadata or {}).get("db_type", "postgres")
                grouped[table_name]["db_type"] = db_type
                if chunk_type in grouped[table_name]:
                    if content not in grouped[table_name][chunk_type]:
                        grouped[table_name][chunk_type].append(content)

            blocks = []
            for table_name, chunks in grouped.items():
                db_type = chunks["db_type"]
                label = "Table" if db_type == "postgres" else "Collection"
                parts = [f"{label}: {table_name} ({db_type})"]
                if chunks["ddl"]:
                    parts.append(chunks["ddl"][0])
                if chunks["description"]:
                    parts.append(chunks["description"][0])
                for sq in chunks["sample_query"]:
                    parts.append(sq)
                blocks.append("\n".join(parts))

            # Build a JOIN hint from FK info in DDL chunks
            fk_lines = []
            for table_name, chunks in grouped.items():
                for ddl in chunks["ddl"]:
                    for line in ddl.split("\n"):
                        if "Foreign keys:" in line and "none" not in line.lower():
                            fk_lines.append(f"  {table_name}: {line.strip()}")
            if fk_lines:
                join_hint = (
                    "\n\n━━━ JOIN RELATIONSHIPS ━━━\n"
                    "Use these foreign keys when JOINing tables:\n"
                    + "\n".join(fk_lines)
                    + "\nExample: bookings → flights → aircraft means:"
                    "\n  bookings JOIN flights ON bookings.flight_id = flights.flight_id"
                    "\n  JOIN aircraft ON flights.aircraft_id = aircraft.aircraft_id"
                )
            else:
                join_hint = ""

            output = "\n\n---\n\n".join(blocks) + join_hint if blocks else "No relevant schema found."
            log.info(
                "tool.retrieve_schema.complete",
                tenant_id=t_id,
                rows_found=len(rows),
                tables_matched=list(grouped.keys()),
            )
            return output

        return retrieve_schema

    fn = _make_fn()

    return StructuredTool.from_function(
        func=fn,
        name="retrieve_schema",
        description=(
            "Search the schema knowledge base to find which tables or "
            "collections are relevant to a question. ALWAYS call this "
            "first before writing any query. Returns exact column/field "
            "names, types, and example queries to use. Never guess "
            "column or collection names — always retrieve first."
        ),
    )
