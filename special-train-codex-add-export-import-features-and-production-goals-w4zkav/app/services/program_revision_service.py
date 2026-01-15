from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import Actor, ensure_actor, require_permission
from .validation import validate_program_revision
from ..audit import log_audit
from ..config import DATA_DIR
from ..db import (
    add_program_file,
    deactivate_program_revisions,
    get_active_program,
    list_program_revisions,
)


PERMISSION_KEY = "manage_documents"


def _safe_folder_name(value: str) -> str:
    return "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in value.strip()]) or "document"


def _hash_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _store_file(source_path: str, scope: str, filename: str, revision: int) -> str:
    ext = Path(source_path).suffix
    target_dir = Path(DATA_DIR) / "storage" / "programs" / _safe_folder_name(scope) / _safe_folder_name(filename)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"rev_{revision}{ext}"
    target_path.write_bytes(Path(source_path).read_bytes())
    return str(target_path.relative_to(DATA_DIR))


def create_program_file(
    *,
    source_path: str,
    filename: str,
    scope_type: str,
    machine_id: Optional[int],
    actor_user: Actor | Dict[str, str] | None,
) -> Tuple[str, Optional[int]]:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "add_program_file", "Machine History")
    validate_program_revision({"filename": filename, "scope_type": scope_type})

    file_hash = _hash_file(source_path)
    revisions = list_program_revisions(scope_type, filename, machine_id)
    for rev in revisions:
        if rev.get("file_hash") == file_hash:
            return "DUPLICATE", None

    next_revision = (revisions[0]["revision"] + 1) if revisions else 1
    deactivate_program_revisions(scope_type, filename, machine_id)
    stored_path = _store_file(source_path, scope_type, filename, next_revision)
    parent_id = revisions[0]["id"] if revisions else None
    new_id = add_program_file(
        scope_type=scope_type,
        machine_id=machine_id,
        filename=filename,
        file_path=stored_path,
        file_hash=file_hash,
        revision=next_revision,
        parent_id=parent_id,
        created_by=actor.username,
        is_active=1,
    )
    log_audit(actor.username, f"Added program file {filename} rev {next_revision}")
    return "CREATED", new_id


def list_program_revisions_service(
    scope_type: str,
    filename: str,
    machine_id: Optional[int],
) -> List[Dict]:
    return list_program_revisions(scope_type, filename, machine_id)


def get_active_program_service(
    scope_type: str,
    filename: str,
    machine_id: Optional[int],
) -> Optional[Dict]:
    return get_active_program(scope_type, filename, machine_id)


def rollback_program_revision(
    *,
    scope_type: str,
    filename: str,
    machine_id: Optional[int],
    target_revision_id: int,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "rollback_program_revision", "Machine History")
    deactivate_program_revisions(scope_type, filename, machine_id)
    from ..db import activate_program_revision

    activate_program_revision(target_revision_id)
    log_audit(actor.username, f"Rolled back program {filename} to revision {target_revision_id}")


def update_program_file(*args, **kwargs) -> None:
    return None


def get_program_file(*args, **kwargs) -> Optional[Dict]:
    return None
