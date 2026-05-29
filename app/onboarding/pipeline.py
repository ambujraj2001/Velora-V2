import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.logging import get_logger
from app.models.schema_embedding import SchemaEmbedding
from app.models.tenant_database import TenantDatabase
from app.onboarding.embedder import embed_and_store
from app.onboarding.enrich import enrich_table
from app.onboarding.introspect import introspect
from app.security.encryption import decrypt

log = get_logger(__name__)


def run_onboarding(tenant_id: str, db_session: Session) -> dict:
    tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    log.info("onboarding.pipeline.begin", tenant_id=tenant_id)

    tenant_db = (
        db_session.query(TenantDatabase)
        .filter(TenantDatabase.tenant_id == tenant_uuid)
        .first()
    )
    if not tenant_db:
        log.error("onboarding.pipeline.no_connection", tenant_id=tenant_id)
        raise ValueError("No database connected for tenant")

    try:
        log.info(
            "onboarding.pipeline.connect",
            tenant_id=tenant_id,
            db_name=tenant_db.db_name,
            db_type=tenant_db.db_type,
        )
        conn_string = decrypt(tenant_db.conn_string)
        connector = get_connector(tenant_db.db_type, conn_string)

        if not connector.test_connection():
            tenant_db.status = "error"
            db_session.commit()
            log.error("onboarding.pipeline.connection_failed", tenant_id=tenant_id)
            raise RuntimeError("Could not connect to tenant database")

        deleted = (
            db_session.query(SchemaEmbedding)
            .filter(SchemaEmbedding.tenant_id == tenant_uuid)
            .delete()
        )
        log.info(
            "onboarding.pipeline.embeddings_cleared",
            tenant_id=tenant_id,
            deleted_count=deleted,
        )

        log.info("onboarding.pipeline.introspect.begin", tenant_id=tenant_id)
        introspected = introspect(connector)
        log.info(
            "onboarding.pipeline.introspect.complete",
            tenant_id=tenant_id,
            table_count=len(introspected),
            tables=list(introspected.keys()),
        )

        total_chunks = 0
        for table_name, table_schema in introspected.items():
            log.info(
                "onboarding.pipeline.table.begin",
                tenant_id=tenant_id,
                table_name=table_name,
            )
            enriched = enrich_table(table_name, table_schema, tenant_db.db_type)
            log.info(
                "onboarding.pipeline.table.enriched",
                tenant_id=tenant_id,
                table_name=table_name,
                sample_queries=len(enriched.get("sample_queries", [])),
            )
            chunks = embed_and_store(
                tenant_id,
                table_name,
                table_schema,
                enriched,
                tenant_db.db_type,
                db_session,
            )
            total_chunks += chunks
            log.info(
                "onboarding.pipeline.table.embedded",
                tenant_id=tenant_id,
                table_name=table_name,
                chunks_stored=chunks,
            )

        tenant_db.status = "active"
        tenant_db.onboarded_at = datetime.utcnow()
        db_session.commit()

        result = {
            "tables_indexed": len(introspected),
            "chunks_stored": total_chunks,
        }
        log.info("onboarding.pipeline.complete", tenant_id=tenant_id, **result)
        return result
    except Exception:
        tenant_db.status = "error"
        db_session.commit()
        log.exception("onboarding.pipeline.failed", tenant_id=tenant_id)
        raise
