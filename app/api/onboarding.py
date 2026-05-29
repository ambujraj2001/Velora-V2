import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.tenants import get_authenticated_tenant
from app.database import SessionLocal, get_db
from app.logging import bind_context, get_logger
from app.models.tenant_database import TenantDatabase
from app.onboarding.pipeline import run_onboarding
from app.security.auth import require_tenant_access

router = APIRouter()
log = get_logger(__name__)


class OnboardStartResponse(BaseModel):
    status: str
    message: str


class OnboardStatusResponse(BaseModel):
    status: str
    onboarded_at: str | None
    message: str


def _run_onboarding_background(tenant_id: str) -> None:
    bind_context(tenant_id=tenant_id)
    log.info("onboarding.background.start", tenant_id=tenant_id)
    db = SessionLocal()
    try:
        result = run_onboarding(tenant_id, db)
        log.info(
            "onboarding.background.complete",
            tenant_id=tenant_id,
            tables_indexed=result.get("tables_indexed"),
            chunks_stored=result.get("chunks_stored"),
        )
    except Exception:
        log.exception("onboarding.background.failed", tenant_id=tenant_id)
    finally:
        db.close()


@router.post("/{tenant_id}", response_model=OnboardStartResponse)
def start_onboarding(
    tenant_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)
    log.info("onboarding.start.requested", tenant_id=tenant_id)

    tenant_uuid = uuid.UUID(tenant_id)
    tenant_db = (
        db.query(TenantDatabase)
        .filter(TenantDatabase.tenant_id == tenant_uuid)
        .first()
    )
    if not tenant_db:
        log.warning("onboarding.start.no_connection", tenant_id=tenant_id)
        raise HTTPException(status_code=404, detail="No database connected for tenant.")

    background_tasks.add_task(_run_onboarding_background, tenant_id)
    log.info(
        "onboarding.start.queued",
        tenant_id=tenant_id,
        db_name=tenant_db.db_name,
        db_type=tenant_db.db_type,
    )

    return OnboardStartResponse(
        status="onboarding_started",
        message=(
            "Schema indexing running in background. "
            "Poll GET /onboard/{tenant_id}/status"
        ),
    )


@router.get("/{tenant_id}/status", response_model=OnboardStatusResponse)
def get_onboarding_status(
    tenant_id: str,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)

    tenant_uuid = uuid.UUID(tenant_id)
    tenant_db = (
        db.query(TenantDatabase)
        .filter(TenantDatabase.tenant_id == tenant_uuid)
        .first()
    )
    if not tenant_db:
        raise HTTPException(status_code=404, detail="No database connected for tenant.")

    status = tenant_db.status
    if status == "pending":
        message = "Onboarding not started yet"
    elif status == "active":
        message = "Database indexed and ready"
    else:
        message = "Onboarding failed. Re-POST /onboard to retry."

    log.info(
        "onboarding.status",
        tenant_id=tenant_id,
        status=status,
        onboarded_at=tenant_db.onboarded_at.isoformat() if tenant_db.onboarded_at else None,
    )

    return OnboardStatusResponse(
        status=status,
        onboarded_at=(
            tenant_db.onboarded_at.isoformat() if tenant_db.onboarded_at else None
        ),
        message=message,
    )
