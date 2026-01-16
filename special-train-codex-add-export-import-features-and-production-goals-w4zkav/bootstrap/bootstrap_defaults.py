from __future__ import annotations

from typing import Iterable

from app import db
from app.populate_db import run as populate_run


TABLES_TO_CHECK = ("users", "parts", "tools")


def _table_empty(table: str) -> bool:
    with db.connect() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
        return int(row["cnt"]) == 0


def _all_tables_empty(tables: Iterable[str]) -> bool:
    return all(_table_empty(table) for table in tables)


def bootstrap_defaults_if_needed(db_module=db) -> None:
    """Load JSON defaults only when the DB tables are empty."""
    if not _all_tables_empty(TABLES_TO_CHECK):
        return
    populate_run()
