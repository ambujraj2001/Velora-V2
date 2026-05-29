import json
import uuid

from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.logging import get_logger
from app.models.tenant_database import TenantDatabase
from app.security.encryption import decrypt

log = get_logger(__name__)


def build_get_db_info_tool(tenant_id: str, db_session: Session) -> StructuredTool:
    def _make_fn(t_id=tenant_id, sess=db_session):
        def get_db_info() -> str:
            log.info("tool.get_db_info.begin", tenant_id=t_id)
            try:
                tenant_uuid = uuid.UUID(t_id) if isinstance(t_id, str) else t_id
                tenant_db = (
                    sess.query(TenantDatabase)
                    .filter(TenantDatabase.tenant_id == tenant_uuid)
                    .first()
                )
                if not tenant_db:
                    log.warning("tool.get_db_info.no_database", tenant_id=t_id)
                    return json.dumps({"error": "No database connected."})

                conn_string = decrypt(tenant_db.conn_string)
                connector = get_connector(tenant_db.db_type, conn_string)
                schema = connector.get_schema()
                table_or_collection_names = list(schema.keys())

                log.info(
                    "tool.get_db_info.complete",
                    tenant_id=t_id,
                    db_name=tenant_db.db_name,
                    db_type=tenant_db.db_type,
                    table_count=len(table_or_collection_names),
                )
                return json.dumps(
                    {
                        "db_name": tenant_db.db_name,
                        "db_type": tenant_db.db_type,
                        "description": tenant_db.description,
                        "status": tenant_db.status,
                        "tables_or_collections": table_or_collection_names,
                    }
                )
            except Exception as e:
                log.exception(
                    "tool.get_db_info.failed",
                    tenant_id=t_id,
                    error=str(e),
                )
                return json.dumps({"error": f"Could not load database info: {e}"})

        return get_db_info

    fn = _make_fn()

    return StructuredTool.from_function(
        func=fn,
        name="get_db_info",
        description=(
            "Returns the tenant's database type (postgres or mongodb), "
            "name, description, and a list of all table or collection "
            "names. Call this at the start of every conversation to "
            "understand what data is available."
        ),
    )
