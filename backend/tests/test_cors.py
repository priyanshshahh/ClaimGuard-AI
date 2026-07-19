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
    """CORSMiddleware binds allow_origin_regex at construction; patch the
    live middleware option so this covers the production regex pattern."""
    import re

    regex = r"https://.*\.vercel\.app"
    app = main.app
    mw = app.middleware_stack
    while mw is not None:
        if mw.__class__.__name__ == "CORSMiddleware":
            mw.allow_origin_regex = re.compile(regex)
            break
        mw = getattr(mw, "app", None)
    with TestClient(app) as client:
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
    import re

    regex = r"https://.*\.vercel\.app"
    app = main.app
    mw = app.middleware_stack
    while mw is not None:
        if mw.__class__.__name__ == "CORSMiddleware":
            mw.allow_origin_regex = re.compile(regex)
            break
        mw = getattr(mw, "app", None)
    with TestClient(app) as client:
        # regex must anchor on the real vercel.app domain, dot escaped
        r = _preflight(client, "https://foo.vercel.app.evil.com")
        assert r.status_code == 400
