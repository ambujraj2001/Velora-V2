import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging import bind_context, get_logger
from app.models.tenant import Tenant
from app.security.auth import require_tenant_access, verify_api_key
from app.security.passwords import hash_password, normalize_email

router = APIRouter()
log = get_logger(__name__)


class CreateTenantRequest(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)


class CreateTenantResponse(BaseModel):
    tenant_id: str
    api_key: str
    name: str
    email: str


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    email: str | None
    created_at: str
    is_active: bool


def get_authenticated_tenant(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db),
) -> str:
    tenant_id = verify_api_key(db, x_api_key)
    bind_context(tenant_id=tenant_id)
    return tenant_id


@router.post("", response_model=CreateTenantResponse)
def create_tenant(body: CreateTenantRequest, db: Session = Depends(get_db)):
    email = normalize_email(body.email)
    log.info("tenant.create.attempt", email=email, name=body.name.strip())

    existing = db.query(Tenant).filter(Tenant.email == email).first()
    if existing:
        log.warning("tenant.create.failed", email=email, reason="email_exists")
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    tenant_id = uuid.uuid4()
    api_key = secrets.token_hex(16)
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

    tenant = Tenant(
        id=tenant_id,
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        api_key=hashed_key,
    )
    db.add(tenant)
    db.commit()

    bind_context(tenant_id=str(tenant_id))
    log.info("tenant.create.success", tenant_id=str(tenant_id), email=email)
    return CreateTenantResponse(
        tenant_id=str(tenant_id),
        api_key=api_key,
        name=tenant.name,
        email=email,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)
    log.info("tenant.get", tenant_id=tenant_id)

    tenant = db.query(Tenant).filter(Tenant.id == uuid.UUID(tenant_id)).first()
    if not tenant:
        log.warning("tenant.get.not_found", tenant_id=tenant_id)
        raise HTTPException(status_code=404, detail="Tenant not found")

    return TenantResponse(
        tenant_id=str(tenant.id),
        name=tenant.name,
        email=tenant.email,
        created_at=tenant.created_at.isoformat() if tenant.created_at else "",
        is_active=tenant.is_active,
    )
