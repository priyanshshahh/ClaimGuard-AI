"""Authentication for ClaimGuard-AI API routes.

Supports:
  - AUTH_DISABLED=true for local CI / DuckDB (returns a synthetic admin user)
  - X-API-Key header matching API_KEYS (comma-separated)
  - Authorization: Bearer <JWT> verified with SUPABASE_JWT_SECRET (HS256)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def _auth_disabled() -> bool:
    return os.getenv("AUTH_DISABLED", "").lower() in ("1", "true", "yes")


def _api_keys() -> set[str]:
    raw = os.getenv("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


@dataclass
class CurrentUser:
    user_id: str
    org_id: str
    role: str
    email: str


def _local_user() -> CurrentUser:
    return CurrentUser(
        user_id="local",
        org_id="local",
        role="admin",
        email="local@localhost",
    )


def _user_from_jwt(token: str) -> CurrentUser:
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured",
        )
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    user_id = str(payload.get("sub") or payload.get("user_id") or "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    app_meta = payload.get("app_metadata") or {}
    user_meta = payload.get("user_metadata") or {}

    # org_id resolution: never trust a top-level claim for tenancy. Supabase
    # puts application tenancy in app_metadata (set by trusted server code) with
    # user_metadata as a fallback, then the deployment-wide DEFAULT_ORG_ID.
    org_id = (
        app_meta.get("org_id")
        or user_meta.get("org_id")
        or os.getenv("DEFAULT_ORG_ID", "")
    )

    # role resolution: NEVER use the top-level `role` claim. Supabase sets it to
    # the Postgres role ("authenticated"), which is not an application role.
    # Application role lives in app_metadata (trusted) then user_metadata.
    role = (
        app_meta.get("role")
        or user_meta.get("role")
        or "member"
    )
    email = str(payload.get("email") or user_meta.get("email") or "")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Token missing org_id claim (expected app_metadata.org_id, "
                "user_metadata.org_id, or a configured DEFAULT_ORG_ID)"
            ),
        )

    return CurrentUser(user_id=user_id, org_id=str(org_id), role=str(role), email=email)


def _user_from_api_key(api_key: str) -> CurrentUser:
    if api_key not in _api_keys():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return CurrentUser(
        user_id="api-key",
        org_id=os.getenv("API_KEY_ORG_ID", "local"),
        role="admin",
        email="api-key@local",
    )


def authenticate_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> CurrentUser:
    if _auth_disabled():
        return _local_user()

    api_key = request.headers.get("X-API-Key")
    if api_key:
        return _user_from_api_key(api_key.strip())

    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        return _user_from_jwt(credentials.credentials)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication (X-API-Key or Bearer JWT)",
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    return authenticate_request(request, credentials)


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
