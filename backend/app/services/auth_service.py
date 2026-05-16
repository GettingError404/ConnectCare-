from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from jose import jwt
import uuid
import secrets

from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.rbac import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.repositories.auth import SessionRepository, RefreshTokenRepository


REFRESH_EXPIRE_DAYS = 30


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return (
        db.query(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .filter(User.email == email)
        .one_or_none()
    )


def create_user(db: Session, payload: RegisterRequest) -> User:
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed = get_password_hash(payload.password)
    user = User(email=payload.email, full_name=payload.name, password_hash=hashed)
    try:
        db.add(user)
        db.flush()

        tenant = Tenant(
            name=f"{payload.name} Tenant",
            slug=f"user-{user.id.hex[:12]}",
            description=f"Auto-created personal tenant for {payload.email}",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        user.tenant_id = tenant.id
        db.commit()
        db.refresh(user)
        return user
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


def _default_token_payload(user: User) -> dict:
    data = {"sub": str(user.id), "user_id": str(user.id)}
    if user.tenant_id:
        data["tenant_id"] = str(user.tenant_id)
    roles = [
        assignment.role.slug
        for assignment in getattr(user, "user_roles", [])
        if assignment.is_active and assignment.role and not getattr(assignment.role, "deleted_at", None)
    ]
    if roles:
        data["roles"] = sorted(set(roles))
    return data


def create_token_pair(db: Session, user: User, device_info: Optional[str] = None, ip: Optional[str] = None, user_agent: Optional[str] = None) -> dict:
    # create session
    session_repo = SessionRepository(db)
    refresh_repo = RefreshTokenRepository(db)

    session = session_repo.create_session(user_id=user.id, tenant_id=getattr(user, "tenant_id", None), device_info=device_info, ip_address=ip, user_agent=user_agent)

    # create access token
    access_expires = timedelta(minutes=60)
    access_payload = _default_token_payload(user)
    access_payload["session_id"] = str(session.id)
    access_token = create_access_token(access_payload, expires_delta=access_expires)

    # create refresh token (opaque jti + family)
    jti = uuid.uuid4().hex
    family_id = secrets.token_hex(16)
    refresh_payload = {**_default_token_payload(user), "session_id": str(session.id), "jti": jti, "family_id": family_id}
    refresh_token = create_refresh_token(refresh_payload, expires_delta=timedelta(days=REFRESH_EXPIRE_DAYS))

    # persist refresh record
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS)
    refresh_repo.create(jti=jti, family_id=family_id, user_id=user.id, session_id=session.id, expires_at=expires_at)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def rotate_refresh_token(db: Session, refresh_token_str: str) -> dict:
    refresh_repo = RefreshTokenRepository(db)
    try:
        payload = decode_token(refresh_token_str)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload.get("jti")
    family_id = payload.get("family_id")
    user_id = payload.get("sub") or payload.get("user_id")
    if not jti or not family_id or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")

    stored = refresh_repo.get_by_jti(jti)
    if not stored or stored.revoked:
        # possible reuse attack — revoke entire family
        if stored and stored.family_id:
            refresh_repo.revoke_family(stored.family_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    # rotate: create new jti and token, mark old as revoked/replaced
    new_jti = uuid.uuid4().hex
    new_payload = {"sub": str(user_id), "user_id": str(user_id), "family_id": family_id, "jti": new_jti}
    if stored.session_id:
        new_payload["session_id"] = str(stored.session_id)
    new_refresh_token = create_refresh_token(new_payload, expires_delta=timedelta(days=REFRESH_EXPIRE_DAYS))
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS)
    refresh_repo.create(jti=new_jti, family_id=family_id, user_id=stored.user_id, session_id=stored.session_id, expires_at=expires_at)
    # mark old as revoked and point to replacement
    refresh_repo.revoke(jti, replaced_by=new_jti)

    # create a fresh access token for the user
    # load user from db
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    access_token = create_access_token(_default_token_payload(user), expires_delta=timedelta(minutes=60))

    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


def revoke_refresh(db: Session, refresh_token_str: str):
    refresh_repo = RefreshTokenRepository(db)
    session_repo = SessionRepository(db)
    try:
        payload = decode_token(refresh_token_str)
    except Exception:
        return
    jti = payload.get("jti")
    if jti:
        stored = refresh_repo.get_by_jti(jti)
        if stored and stored.session_id:
            session_repo.revoke_session(stored.session_id)
        refresh_repo.revoke(jti)

