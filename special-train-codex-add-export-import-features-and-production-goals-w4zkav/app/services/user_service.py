from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import Actor, ensure_actor, require_permission
from ..audit import log_audit
from ..db import (
    delete_screen_permission,
    get_user,
    list_screen_permissions,
    list_users,
    set_screen_permission,
    upsert_user,
    update_user_fields,
)


PERMISSION_KEY = "manage_users"


def create_user(
    *,
    username: str,
    password: str,
    role: str,
    name: str,
    line: str,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "create_user", "Admin")
    upsert_user(
        username=username,
        password=password,
        role=role,
        name=name,
        line=line,
        is_active=1,
        created_by=actor.username,
        updated_by=actor.username,
    )
    log_audit(actor.username, f"Created user {username} ({role})")


def update_user(
    username: str,
    fields: Dict[str, Any],
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "update_user", "Admin")
    fields = dict(fields)
    fields["updated_by"] = actor.username
    update_user_fields(username, fields)
    log_audit(actor.username, f"Updated user {username}")


def list_user_accounts() -> List[Dict[str, Any]]:
    return list_users()


def get_user_account(username: str) -> Optional[Dict[str, Any]]:
    return get_user(username)


def list_permissions(username: Optional[str] = None) -> List[Dict[str, Any]]:
    return list_screen_permissions(username)


def set_permission(
    username: str,
    screen: str,
    level: str,
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "set_permission", "Admin")
    set_screen_permission(username, screen, level)
    log_audit(actor.username, f"Set access {screen}={level} for {username}")


def delete_permission(
    username: str,
    screen: str,
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "delete_permission", "Admin")
    delete_screen_permission(username, screen)
    log_audit(actor.username, f"Removed access {screen} for {username}")
