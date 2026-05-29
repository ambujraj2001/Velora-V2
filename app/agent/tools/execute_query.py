import json
import uuid

from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.logging import get_logger
from app.models.tenant_database import TenantDatabase
from app.security.encryption import decrypt

log = get_logger(__name__)


def build_execute_query_tool(tenant_id: str, db_session: Session) -> StructuredTool:
    def _make_fn(t_id=tenant_id, sess=db_session):
        def execute_query(query: str) -> str:
            query_preview = query[:200] + ("..." if len(query) > 200 else "")
            log.info(
                "tool.execute_query.begin",
                tenant_id=t_id,
                query_preview=query_preview,
            )
            try:
                tenant_uuid = uuid.UUID(t_id) if isinstance(t_id, str) else t_id
                tenant_db = (
                    sess.query(TenantDatabase)
                    .filter(TenantDatabase.tenant_id == tenant_uuid)
                    .first()
                )
                if not tenant_db:
                    log.warning("tool.execute_query.no_database", tenant_id=t_id)
                    return "Error: no database connected for tenant."

                conn_string = decrypt(tenant_db.conn_string)
                connector = get_connector(tenant_db.db_type, conn_string)

                if tenant_db.db_type == "postgres":
                    result = connector.execute(query)
                else:
                    try:
                        parsed = json.loads(query)
                    except json.JSONDecodeError:
                        log.warning(
                            "tool.execute_query.invalid_json",
                            tenant_id=t_id,
                        )
                        return (
                            'Error: MongoDB query must be JSON with '
                            "'collection' key. "
                            'Example: {"collection": "orders", '
                            '"filter": {}, "limit": 10}'
                        )
                    if "collection" not in parsed:
                        log.warning(
                            "tool.execute_query.missing_collection",
                            tenant_id=t_id,
                        )
                        return (
                            'Error: MongoDB query must be JSON with '
                            "'collection' key. "
                            'Example: {"collection": "orders", '
                            '"filter": {}, "limit": 10}'
                        )
                    result = connector.execute(query)

                if len(result) == 0:
                    log.info("tool.execute_query.empty", tenant_id=t_id)
                    return "Query returned no results."

                note = ""
                if len(result) >= 100:
                    note = f"\nNote: showing 100 of {len(result)}+ rows."

                log.info(
                    "tool.execute_query.complete",
                    tenant_id=t_id,
                    row_count=len(result),
                    truncated=len(result) >= 100,
                )
                return json.dumps(result[:100], default=str) + note
            except Exception as e:
                log.exception(
                    "tool.execute_query.failed",
                    tenant_id=t_id,
                    error=str(e),
                )
                return f"Query error: {str(e)} — fix the query and try again."

        return execute_query

    fn = _make_fn()

    return StructuredTool.from_function(
        func=fn,
        name="execute_query",
        description=(
            "Execute a read-only query on the tenant's database.\n"
            "For PostgreSQL: pass a valid SQL SELECT statement.\n"
            "  Example: SELECT id, name, amount FROM orders "
            "WHERE status = 'active' LIMIT 20\n"
            "For MongoDB: pass a JSON string with collection and filter.\n"
            '  Example: {"collection": "orders", '
            '"filter": {"status": "active"}, "limit": 20}\n'
            "Only call this after retrieve_schema. "
            "Use exact names from the schema output. "
            "Only read operations are permitted."
        ),
    )
