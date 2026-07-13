"""CORS regression tests: Starlette exact-matches allow_origins, so the old
"https://*.vercel.app" entry never matched; previews must use the regex."""

from fastapi.testclient import TestClient

import main


def _preflight(client, origin):
    return client.options(
        "/api/priority-queue",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


def test_localhost_origin_allowed():
    with TestClient(main.app) as client:
        r = _preflight(client, "http://localhost:3000")
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_vercel_preview_origin_allowed_via_regex():
    with TestClient(main.app) as client:
        r = _preflight(client, "https://claimguard-git-feat-abc123.vercel.app")
        assert r.status_code == 200
        assert (
            r.headers["access-control-allow-origin"]
            == "https://claimguard-git-feat-abc123.vercel.app"
        )


def test_unknown_origin_rejected():
    with TestClient(main.app) as client:
        r = _preflight(client, "https://evil.example.com")
        assert r.status_code == 400
        assert "access-control-allow-origin" not in r.headers


def test_vercel_lookalike_rejected():
    with TestClient(main.app) as client:
        # regex must anchor on the real vercel.app domain, dot escaped
        r = _preflight(client, "https://foo.vercel.app.evil.com")
        assert r.status_code == 400
