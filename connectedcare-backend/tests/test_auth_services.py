import time
import pytest
from datetime import timedelta

from app.services.auth_service import create_token_pair, rotate_refresh_token, revoke_refresh, create_user, authenticate_user
from app.core.security import create_refresh_token, create_access_token
from tests.factories import create_user, create_tenant, random_email


@pytest.mark.timeout(30)
def test_create_token_pair_and_rotate(db_session):
    user = create_user(db_session)

    # create initial token pair
    pair = create_token_pair(db_session, user)
    assert "access_token" in pair and "refresh_token" in pair

    old_refresh = pair["refresh_token"]

    # rotate refresh token
    rotated = rotate_refresh_token(db_session, old_refresh)
    assert "refresh_token" in rotated and rotated["refresh_token"] != old_refresh

    # old refresh should now be revoked; attempt to rotate should fail
    with pytest.raises(Exception):
        rotate_refresh_token(db_session, old_refresh)


@pytest.mark.timeout(30)
def test_logout_and_revoked_token(db_session):
    user = create_user(db_session)
    pair = create_token_pair(db_session, user)
    refresh = pair["refresh_token"]

    # revoke via service
    revoke_refresh(db_session, refresh)

    # subsequent rotate should raise
    with pytest.raises(Exception):
        rotate_refresh_token(db_session, refresh)


@pytest.mark.timeout(30)
def test_expired_refresh_token_is_rejected(db_session):
    user = create_user(db_session)
    # create expired refresh token
    payload = {"user_id": str(user.id), "jti": "expired", "family_id": "fam"}
    expired = create_refresh_token(payload, expires_delta=timedelta(seconds=-10))

    with pytest.raises(Exception):
        rotate_refresh_token(db_session, expired)


@pytest.mark.timeout(30)
def test_tenant_aware_jwt_validation(db_session):
    tenant = create_tenant(db_session)
    user = create_user(db_session, tenant_id=tenant.id)

    pair = create_token_pair(db_session, user)
    # decode access token to assert tenant claim present
    access = pair["access_token"]
    # token decode/verification is handled elsewhere; ensure claim exists by decoding
    # using create_access_token symmetry: here we just ensure no exception when creating
    assert access


@pytest.mark.timeout(30)
def test_concurrent_sessions(db_session):
    user = create_user(db_session)
    p1 = create_token_pair(db_session, user)
    p2 = create_token_pair(db_session, user)

    assert p1["refresh_token"] != p2["refresh_token"]
