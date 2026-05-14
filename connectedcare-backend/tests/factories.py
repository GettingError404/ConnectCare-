import uuid
from typing import Optional

from app.core.security import get_password_hash
from app.models.user import User
from app.models.tenant import Tenant


def random_email() -> str:
    return f"test+{uuid.uuid4().hex[:8]}@example.com"


def create_tenant(db, slug: Optional[str] = None) -> Tenant:
    slug = slug or f"tenant-{uuid.uuid4().hex[:8]}"
    t = Tenant(name=f"Tenant {slug}", slug=slug)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def create_user(db, email: Optional[str] = None, password: str = "TestP@ssw0rd!", tenant_id=None) -> User:
    email = email or random_email()
    user = User(email=email, full_name="Test User", password_hash=get_password_hash(password), tenant_id=tenant_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
