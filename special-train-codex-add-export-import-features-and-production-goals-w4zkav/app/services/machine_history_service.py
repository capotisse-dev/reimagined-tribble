from __future__ import annotations

from typing import Dict, List, Optional

from . import Actor, ensure_actor, require_permission
from .validation import validate_machine_history_entry
from ..audit import log_audit
from ..db import (
    create_machine_document,
    add_machine_document_revision,
    get_next_machine_document_revision_number,
    list_machine_document_revisions,
    list_machine_documents,
    set_machine_document_active,
)


PERMISSION_KEY = "manage_documents"


def list_documents(line: str, machine: str, doc_type: Optional[str] = None, search: str = "") -> List[Dict]:
    return list_machine_documents(line, machine, doc_type=doc_type, search=search)


def list_revisions(document_id: int) -> List[Dict]:
    return list_machine_document_revisions(document_id)


def create_document(
    line: str,
    machine: str,
    doc_type: str,
    doc_name: str,
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> int:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "create_document", "Machine History")
    validate_machine_history_entry({
        "line": line,
        "machine": machine,
        "doc_type": doc_type,
        "doc_name": doc_name,
    })
    document_id = create_machine_document(line, machine, doc_type, doc_name, actor.username)
    log_audit(actor.username, f"Created document {doc_name} ({doc_type})")
    return document_id


def add_revision(
    document_id: int,
    stored_path: str,
    original_filename: str,
    file_hash: str,
    notes: str | None,
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> int:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "add_revision", "Machine History")
    revision_number = get_next_machine_document_revision_number(document_id)
    add_machine_document_revision(
        document_id=document_id,
        revision_number=revision_number,
        stored_path=stored_path,
        original_filename=original_filename,
        file_hash=file_hash,
        created_by=actor.username,
        notes=notes,
    )
    log_audit(actor.username, f"Added revision {revision_number} to document {document_id}")
    return revision_number


def update_document_active(document_id: int, is_active: bool, *, actor_user: Actor | Dict[str, str] | None) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "update_document_active", "Machine History")
    set_machine_document_active(document_id, is_active)
    log_audit(actor.username, f"Updated document {document_id} active={int(is_active)}")


def get_document(document_id: int) -> Optional[Dict]:
    revisions = list_machine_document_revisions(document_id)
    return revisions[0] if revisions else None
