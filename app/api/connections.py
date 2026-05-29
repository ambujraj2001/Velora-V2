import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.tenants import get_authenticated_tenant
from app.connectors.registry import get_connector
from app.database import get_db
from app.logging import get_logger
from app.models.schema_embedding import SchemaEmbedding
from app.models.tenant_database import TenantDatabase
from app.security.auth import require_tenant_access
from app.security.encryption import encrypt

router = APIRouter()
log = get_logger(__name__)


class ConnectDatabaseRequest(BaseModel):
    db_name: str
    db_type: str
    conn_string: str
    description: str


class ConnectDatabaseResponse(BaseModel):
    connection_id: str
    db_name: str
    db_type: str
    status: str


class ConnectionStatusResponse(BaseModel):
    db_name: str
    db_type: str
    description: str | None
    status: str
    onboarded_at: str | None


class DisconnectResponse(BaseModel):
    status: str


@router.post("/{tenant_id}", response_model=ConnectDatabaseResponse)
def connect_database(
    tenant_id: str,
    body: ConnectDatabaseRequest,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)
    log.info(
        "connection.connect.attempt",
        tenant_id=tenant_id,
        db_name=body.db_name,
        db_type=body.db_type,
    )

    if body.db_type not in ("postgres", "mongodb"):
        log.warning(
            "connection.connect.failed",
            tenant_id=tenant_id,
            reason="invalid_db_type",
            db_type=body.db_type,
        )
        raise HTTPException(
            status_code=422,
            detail="db_type must be 'postgres' or 'mongodb'",
        )

    tenant_uuid = uuid.UUID(tenant_id)
    existing = (
        db.query(TenantDatabase)
        .filter(TenantDatabase.tenant_id == tenant_uuid)
        .first()
    )
    if existing:
        log.warning(
            "connection.connect.failed",
            tenant_id=tenant_id,
            reason="already_connected",
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "Tenant already has a database connected. "
                "DELETE /connections/{tenant_id} first."
            ),
        )

    log.info("connection.test.begin", tenant_id=tenant_id, db_type=body.db_type)
    connector = get_connector(body.db_type, body.conn_string)
    if not connector.test_connection():
        log.warning(
            "connection.test.failed",
            tenant_id=tenant_id,
            db_name=body.db_name,
        )
        raise HTTPException(
            status_code=400,
            detail="Could not connect to database. Check connection string.",
        )
    log.info("connection.test.success", tenant_id=tenant_id, db_name=body.db_name)

    encrypted = encrypt(body.conn_string)
    tenant_db = TenantDatabase(
        tenant_id=tenant_uuid,
        db_name=body.db_name,
        db_type=body.db_type,
        conn_string=encrypted,
        description=body.description,
        status="pending",
    )
    db.add(tenant_db)
    db.commit()
    db.refresh(tenant_db)

    log.info(
        "connection.connect.success",
        tenant_id=tenant_id,
        connection_id=str(tenant_db.id),
        db_name=body.db_name,
        db_type=body.db_type,
    )
    return ConnectDatabaseResponse(
        connection_id=str(tenant_db.id),
        db_name=tenant_db.db_name,
        db_type=tenant_db.db_type,
        status="connected",
    )


@router.delete("/{tenant_id}", response_model=DisconnectResponse)
def disconnect_database(
    tenant_id: str,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)
    log.info("connection.disconnect.begin", tenant_id=tenant_id)

    tenant_uuid = uuid.UUID(tenant_id)
    embeddings_deleted = (
        db.query(SchemaEmbedding)
        .filter(SchemaEmbedding.tenant_id == tenant_uuid)
        .delete()
    )
    connections_deleted = (
        db.query(TenantDatabase)
        .filter(TenantDatabase.tenant_id == tenant_uuid)
        .delete()
    )
    db.commit()

    log.info(
        "connection.disconnect.success",
        tenant_id=tenant_id,
        embeddings_deleted=embeddings_deleted,
        connections_deleted=connections_deleted,
    )
    return DisconnectResponse(status="disconnected")


@router.get("/{tenant_id}", response_model=ConnectionStatusResponse)
def get_connection(
    tenant_id: str,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)
    log.info("connection.status", tenant_id=tenant_id)

    tenant_uuid = uuid.UUID(tenant_id)
    tenant_db = (
        db.query(TenantDatabase)
        .filter(TenantDatabase.tenant_id == tenant_uuid)
        .first()
    )
    if not tenant_db:
        log.warning("connection.status.not_found", tenant_id=tenant_id)
        raise HTTPException(status_code=404, detail="No database connected.")

    return ConnectionStatusResponse(
        db_name=tenant_db.db_name,
        db_type=tenant_db.db_type,
        description=tenant_db.description,
        status=tenant_db.status,
        onboarded_at=(
            tenant_db.onboarded_at.isoformat() if tenant_db.onboarded_at else None
        ),
    )
