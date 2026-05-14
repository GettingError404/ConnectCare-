import uuid
from datetime import datetime, timezone

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"


def random_email() -> str:
    return f"test+{uuid.uuid4().hex[:8]}@example.com"


def create_user(client: httpx.Client, email: str, password: str, name: str) -> dict:
    resp = client.post("/auth/register", json={"email": email, "password": password, "name": name})
    assert resp.status_code == 201, f"register failed: {resp.status_code} {resp.text}"
    return resp.json()


def login_user(client: httpx.Client, email: str, password: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    payload = resp.json()
    assert "access_token" in payload and payload["access_token"], "no access_token returned"
    return payload["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_device(client: httpx.Client, token: str, payload: dict) -> dict:
    resp = client.post("/devices/register", json=payload, headers=auth_headers(token))
    assert resp.status_code == 201, f"device register failed: {resp.status_code} {resp.text}"
    return resp.json()


def create_vital(client: httpx.Client, token: str, payload: dict) -> dict:
    resp = client.post("/v1/vitals", json=payload, headers=auth_headers(token))
    assert resp.status_code == 201, f"create vital failed: {resp.status_code} {resp.text}"
    return resp.json()


def get_vitals(client: httpx.Client, token: str, user_id: str) -> list:
    resp = client.get(f"/v1/vitals/{user_id}", headers=auth_headers(token))
    assert resp.status_code == 200, f"get vitals failed: {resp.status_code} {resp.text}"
    return resp.json()


def get_latest_vitals(client: httpx.Client, token: str, user_id: str) -> list:
    resp = client.get(f"/v1/vitals/{user_id}/latest", headers=auth_headers(token))
    assert resp.status_code == 200, f"get latest vitals failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.mark.timeout(30)
def test_e2e_user_auth_device_vitals_flow():
    """End-to-end flow: register -> login -> register device -> insert vital -> fetch -> latest"""
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # realistic test data
    email = random_email()
    password = "StrongP@ssw0rd!"
    name = "Test User"

    # 1. Register user
    user = create_user(client, email, password, name)
    assert "id" in user and user["email"] == email
    user_id = user["id"]

    # 2. Login user
    token = login_user(client, email, password)

    # 3. Register device
    device_payload = {
        "device_name": "Test Watch",
        "device_type": "wearable",
        "device_identifier": f"TW-{uuid.uuid4().hex[:8]}",
        "manufacturer": "TestCorp",
    }
    device = register_device(client, token, device_payload)
    assert device["device_name"] == device_payload["device_name"]
    device_id = device["id"]

    # 4. Insert vital data
    recorded_at = datetime.now(timezone.utc).isoformat()
    vital_payload = {
        "user_id": user_id,
        "device_id": device_id,
        "metric_type": "heart_rate",
        "value": 72.5,
        "unit": "bpm",
        "recorded_at": recorded_at,
    }
    vital = create_vital(client, token, vital_payload)
    assert vital["user_id"] == user_id
    assert vital["device_id"] == device_id
    assert float(vital["value"]) == pytest.approx(72.5, rel=1e-3)

    # 5. Fetch vitals
    vitals = get_vitals(client, token, user_id)
    assert isinstance(vitals, list) and len(vitals) >= 1
    # find our inserted vital
    matched = [v for v in vitals if v.get("id") == vital.get("id")]
    assert len(matched) == 1
    assert matched[0]["metric_type"] == "heart_rate"

    # 6. Fetch latest vitals
    latest = get_latest_vitals(client, token, user_id)
    assert isinstance(latest, list)
    # latest should include our metric_type with the recorded value
    types = {v["metric_type"] for v in latest}
    assert "heart_rate" in types

    client.close()
