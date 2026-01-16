from __future__ import annotations

from typing import Dict

from ..audit import log_audit
from ..exceptions import PermissionDenied
from ..permissions import can


class Actor:
    def __init__(self, username: str, role: str):
        self.username = username or ""
        self.role = role or ""

    @classmethod
    def from_controller(cls, controller) -> "Actor":
        return cls(getattr(controller, "user", "") or "", getattr(controller, "role", "") or "")


def require_permission(actor: Actor, permission_key: str, action: str, screen: str) -> None:
    """Validate permissions for a modifying action."""
    if can(actor.role, permission_key, at_least="edit"):
        return
    log_audit(actor.username, f"Permission denied for {screen}:{action}")
    raise PermissionDenied(f"{actor.username} lacks permission for {action}")


def ensure_actor(actor_user: Actor | Dict[str, str] | None) -> Actor:
    if isinstance(actor_user, Actor):
        return actor_user
    if isinstance(actor_user, dict):
        return Actor(actor_user.get("username", ""), actor_user.get("role", ""))
    return Actor("", "")
