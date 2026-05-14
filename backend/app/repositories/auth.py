from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.auth import UserSession, RefreshToken


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: UUID, tenant_id: Optional[UUID] = None, device_info: Optional[str] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> UserSession:
        s = UserSession(user_id=user_id, tenant_id=tenant_id, device_info=device_info, ip_address=ip_address, user_agent=user_agent, last_seen_at=datetime.utcnow())
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def get_session(self, session_id: UUID) -> Optional[UserSession]:
        return self.db.get(UserSession, session_id)

    def revoke_session(self, session_id: UUID):
        s = self.get_session(session_id)
        if not s:
            return
        s.revoked = True
        self.db.add(s)
        self.db.commit()

    def revoke_all_for_user(self, user_id: UUID):
        self.db.query(UserSession).filter(UserSession.user_id == user_id).update({"revoked": True})
        self.db.commit()


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, jti: str, family_id: str, user_id: UUID, session_id: Optional[UUID], expires_at: Optional[datetime]):
        rt = RefreshToken(jti=jti, family_id=family_id, user_id=user_id, session_id=session_id, expires_at=expires_at)
        self.db.add(rt)
        self.db.commit()
        self.db.refresh(rt)
        return rt

    def get_by_jti(self, jti: str) -> Optional[RefreshToken]:
        return self.db.query(RefreshToken).filter(RefreshToken.jti == jti).one_or_none()

    def revoke(self, jti: str, replaced_by: Optional[str] = None):
        rt = self.get_by_jti(jti)
        if not rt:
            return
        rt.revoked = True
        if replaced_by:
            rt.replaced_by = replaced_by
        self.db.add(rt)
        self.db.commit()

    def revoke_family(self, family_id: str):
        self.db.query(RefreshToken).filter(RefreshToken.family_id == family_id).update({"revoked": True})
        self.db.commit()

    def revoke_all_for_user(self, user_id: UUID):
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
        self.db.commit()
