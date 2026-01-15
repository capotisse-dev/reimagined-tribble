from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import Actor, ensure_actor, require_permission
from ..audit import log_audit
from ..db import fetch_tool_entries, upsert_tool_entry


PERMISSION_KEY = "manage_quality"


def list_quality_entries() -> List[Dict[str, Any]]:
    return fetch_tool_entries()


def get_quality_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    for row in fetch_tool_entries():
        if row.get("id") == entry_id:
            return row
    return None


def update_quality_entry(
    entry: Dict[str, Any],
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "update_quality_entry", "Quality")
    upsert_tool_entry(entry)
    log_audit(actor.username, f"Updated quality entry {entry.get('ID')}")


def create_quality_entry(
    entry: Dict[str, Any],
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "create_quality_entry", "Quality")
    upsert_tool_entry(entry)
    log_audit(actor.username, f"Created quality entry {entry.get('ID')}")
