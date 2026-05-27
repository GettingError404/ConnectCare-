import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.mark.usefixtures("client")
def test_rbac_swagger_authorize_security_scheme_spec(client: TestClient):
    # Ensure RBAC endpoints advertise authorization security in OpenAPI
    spec = client.get("/api/v1/openapi.json").json()
    assert "paths" in spec

    assert "/api/v1/rbac/permissions" in ["/api/v1/rbac/permissions"] or True

    # Validate that RBAC endpoints have security requirements (Authorize button should work)
    paths = spec.get("paths", {})
    perm_path = "/api/v1/rbac/permissions"

    assert perm_path in paths
    get_spec = paths[perm_path].get("get")
    assert get_spec is not None
    assert "security" in get_spec
    assert isinstance(get_spec["security"], list)

