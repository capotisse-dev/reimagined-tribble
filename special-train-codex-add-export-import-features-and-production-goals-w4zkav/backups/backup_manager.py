from __future__ import annotations

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.audit import log_audit
from app.config import BACKUPS_DIR, DATA_DIR, DB_PATH
from app.services import Actor, ensure_actor, require_permission

PERMISSION_KEY = "manage_backups"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_backup_now(actor_user: Actor | dict | None = None) -> Path:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "create_backup_now", "Admin")
    backup_dir = Path(BACKUPS_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = _timestamp()
    db_target = backup_dir / f"backup_{stamp}.db"
    shutil.copy2(DB_PATH, db_target)

    uploads_dir = Path(DATA_DIR) / "storage"
    if uploads_dir.exists():
        zip_path = backup_dir / f"uploads_{stamp}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(uploads_dir):
                for filename in files:
                    full_path = Path(root) / filename
                    zf.write(full_path, full_path.relative_to(uploads_dir))

    _prune_old_backups(backup_dir, keep=14)
    log_audit(actor.username, f"Created backup {db_target.name}")
    return db_target


def _prune_old_backups(backup_dir: Path, keep: int) -> None:
    backups = sorted(backup_dir.glob("backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[keep:]:
        old.unlink(missing_ok=True)


def restore_backup(backup_file: str, actor_user: Actor | dict | None = None) -> Optional[Path]:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "restore_backup", "Admin")
    backup_path = Path(backup_file)
    if not backup_path.exists():
        return None
    shutil.copy2(backup_path, DB_PATH)
    log_audit(actor.username, f"Restored backup from {backup_path.name}")
    return backup_path
