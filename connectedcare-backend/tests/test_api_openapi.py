import pytest

from app.main import app


def test_openapi_generates_without_error():
    spec = app.openapi()
    assert isinstance(spec, dict)
    assert "paths" in spec and isinstance(spec["paths"], dict)
    # ensure schemas generated
    assert "components" in spec and "schemas" in spec["components"]


def test_no_callable_schema_in_components():
    spec = app.openapi()
    schemas = spec.get("components", {}).get("schemas", {})
    for name, schema in schemas.items():
        # guard against Pydantic CallableSchema leak
        assert "callable" not in str(schema).lower()
