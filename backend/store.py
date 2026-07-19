"""Storage facade: DuckDB (local default) or PostgreSQL (multi-tenant)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import duckdb_store
import pg_store


def _backend() -> str:
    return os.getenv("STORAGE_BACKEND", "duckdb").lower()


def _require_org_id(org_id: Optional[str]) -> str:
    if not org_id:
        raise ValueError("org_id is required when STORAGE_BACKEND=postgres")
    return org_id


def upsert_claim(claim: Dict[str, Any], org_id: Optional[str] = None) -> None:
    if _backend() == "postgres":
        return pg_store.upsert_claim(claim, _require_org_id(org_id))
    return duckdb_store.upsert_claim(claim, org_id=org_id)


def resolve_claim(
    claim_id: str,
    org_id: Optional[str] = None,
    resolved_by: Optional[str] = None,
) -> bool:
    if _backend() == "postgres":
        return pg_store.resolve_claim(claim_id, _require_org_id(org_id), resolved_by=resolved_by)
    return duckdb_store.resolve_claim(claim_id, org_id=org_id, resolved_by=resolved_by)


def get_claim(claim_id: str, org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if _backend() == "postgres":
        return pg_store.get_claim(claim_id, _require_org_id(org_id))
    return duckdb_store.get_claim(claim_id, org_id=org_id)


def clear_claims(org_id: Optional[str] = None) -> None:
    if _backend() == "postgres":
        return pg_store.clear_claims(_require_org_id(org_id))
    return duckdb_store.clear_claims(org_id=org_id)


def clear_demo_claims(org_id: Optional[str] = None) -> None:
    """Remove only synthetic demo claims, leaving real analyzed claims intact."""
    if _backend() == "postgres":
        return pg_store.clear_demo_claims(_require_org_id(org_id))
    return duckdb_store.clear_demo_claims(org_id=org_id)


def list_claims(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if _backend() == "postgres":
        return pg_store.list_claims(_require_org_id(org_id))
    return duckdb_store.list_claims(org_id=org_id)


def get_executive_metrics(org_id: Optional[str] = None) -> Dict[str, Any]:
    if _backend() == "postgres":
        return pg_store.get_executive_metrics(_require_org_id(org_id))
    return duckdb_store.get_executive_metrics(org_id=org_id)


def ping() -> bool:
    """Cheap connectivity check for readiness probes. Returns True if the
    active backend accepts a trivial query, otherwise raises."""
    if _backend() == "postgres":
        with pg_store._connect() as con:  # noqa: SLF001 - internal health check
            con.execute("SELECT 1")
        return True
    con = duckdb_store._connect()  # noqa: SLF001 - internal health check
    con.execute("SELECT 1")
    con.close()
    return True
