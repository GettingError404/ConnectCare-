import uuid

import pytest
from sqlalchemy.orm import Session

from app.services.rbac_seeding import ensure_default_rbac_seed


def test_rbac_seed_idempotent(db_session: Session):
    # should not raise
    ensure_default_rbac_seed(db_session)
    ensure_default_rbac_seed(db_session)

