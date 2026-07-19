"""Auth middleware tests."""


import jwt
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.setenv("API_KEYS", "test-secret-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-test-secret")
    with TestClient(main.app) as c:
        yield c


def test_auth_disabled_allows_api(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    with TestClient(main.app) as client:
        r = client.get("/api/dashboard-metrics")
        assert r.status_code == 200


def test_missing_auth_returns_401(auth_client):
    r = auth_client.get("/api/dashboard-metrics")
    assert r.status_code == 401


def test_api_key_auth_works(auth_client):
    r = auth_client.get(
        "/api/dashboard-metrics",
        headers={"X-API-Key": "test-secret-key"},
    )
    assert r.status_code == 200


def test_invalid_api_key_rejected(auth_client):
    r = auth_client.get(
        "/api/dashboard-metrics",
        headers={"X-API-Key": "wrong"},
    )
    assert r.status_code == 401


def test_bearer_jwt_auth_works(auth_client):
    # org_id + role live in app_metadata (trusted server-set claims).
    token = jwt.encode(
        {
            "sub": "user-1",
            "email": "u@test.com",
            "app_metadata": {"org_id": "org-123", "role": "member"},
        },
        "jwt-test-secret",
        algorithm="HS256",
    )
    r = auth_client.get(
        "/api/dashboard-metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


def test_role_read_from_app_metadata_not_top_level(auth_client):
    # Supabase sets a top-level role="authenticated"; it must be ignored and the
    # application role must be read from app_metadata.
    token = jwt.encode(
        {
            "sub": "admin-1",
            "email": "admin@test.com",
            "role": "authenticated",  # top-level: must NOT be used
            "app_metadata": {"org_id": "org-9", "role": "admin"},
        },
        "jwt-test-secret",
        algorithm="HS256",
    )
    me = auth_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "admin"
    assert body["org_id"] == "org-9"


def test_org_id_from_user_metadata_and_default(auth_client, monkeypatch):
    # No app_metadata.org_id -> fall back to user_metadata, then DEFAULT_ORG_ID.
    monkeypatch.setenv("DEFAULT_ORG_ID", "fallback-org")
    token = jwt.encode(
        {"sub": "user-2", "email": "u2@test.com", "user_metadata": {}},
        "jwt-test-secret",
        algorithm="HS256",
    )
    me = auth_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["org_id"] == "fallback-org"
    assert me.json()["role"] == "member"


def test_missing_org_id_rejected(auth_client, monkeypatch):
    # No org anywhere and no DEFAULT_ORG_ID -> 401 with a clear message.
    monkeypatch.delenv("DEFAULT_ORG_ID", raising=False)
    token = jwt.encode(
        {"sub": "user-3", "email": "u3@test.com"},
        "jwt-test-secret",
        algorithm="HS256",
    )
    r = auth_client.get(
        "/api/dashboard-metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert "org_id" in r.json()["detail"]


def test_model_info_public_without_auth(auth_client):
    r = auth_client.get("/api/model-info")
    assert r.status_code == 200
