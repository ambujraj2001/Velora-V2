import hashlib

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.models.tenant import Tenant

log = get_logger(__name__)


def verify_api_key(db: Session, x_api_key: str) -> str:
    hashed = hashlib.sha256(x_api_key.encode()).hexdigest()
    tenant = (
        db.query(Tenant)
        .filter(Tenant.api_key == hashed, Tenant.is_active.is_(True))
        .first()
    )
    if not tenant:
        log.warning("auth.api_key.invalid")
        raise HTTPException(status_code=401, detail="Invalid API key")
    log.debug("auth.api_key.valid", tenant_id=str(tenant.id))
    return str(tenant.id)


def require_tenant_access(tenant_id: str, authenticated_tenant_id: str) -> None:
    if tenant_id != authenticated_tenant_id:
        log.warning(
            "auth.access.denied",
            requested_tenant_id=tenant_id,
            authenticated_tenant_id=authenticated_tenant_id,
        )
        raise HTTPException(status_code=403, detail="Access denied for this tenant")
