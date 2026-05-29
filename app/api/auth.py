import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging import bind_context, get_logger
from app.models.tenant import Tenant
from app.security.passwords import hash_password, normalize_email, verify_password

router = APIRouter()
log = get_logger(__name__)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class AuthResponse(BaseModel):
    tenant_id: str
    api_key: str
    name: str
    email: str


def _issue_session(tenant: Tenant, db: Session) -> AuthResponse:
    api_key = secrets.token_hex(16)
    tenant.api_key = hashlib.sha256(api_key.encode()).hexdigest()
    db.commit()
    log.info(
        "auth.session.issued",
        tenant_id=str(tenant.id),
        email=tenant.email,
    )
    return AuthResponse(
        tenant_id=str(tenant.id),
        api_key=api_key,
        name=tenant.name,
        email=tenant.email or "",
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = normalize_email(body.email)
    log.info("auth.login.attempt", email=email)

    tenant = (
        db.query(Tenant)
        .filter(Tenant.email == email, Tenant.is_active.is_(True))
        .first()
    )
    if not tenant or not tenant.password_hash:
        log.warning("auth.login.failed", email=email, reason="unknown_account")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(body.password, tenant.password_hash):
        log.warning("auth.login.failed", email=email, reason="invalid_password")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    bind_context(tenant_id=str(tenant.id))
    log.info("auth.login.success", tenant_id=str(tenant.id), email=email)
    return _issue_session(tenant, db)
