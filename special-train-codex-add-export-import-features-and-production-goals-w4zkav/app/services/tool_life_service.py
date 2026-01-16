from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import Actor, ensure_actor, require_permission
from .validation import validate_tool_change_entry
from ..audit import log_audit
from ..db import (
    apply_tool_change,
    fetch_tool_entries,
    get_tool,
    get_production_goal,
    list_cells_for_line,
    list_downtime_codes,
    list_lines,
    list_machines_for_line,
    list_parts_for_line,
    list_tool_inserts,
    list_tools_for_line,
    upsert_tool_entry_with_downtime,
)


PERMISSION_KEY = "manage_tools"


def list_lines_service() -> List[str]:
    return list_lines()


def list_cells(line: str) -> List[str]:
    return list_cells_for_line(line)


def list_machines(line: str) -> List[str]:
    return list_machines_for_line(line)


def list_parts(line: str) -> List[str]:
    return list_parts_for_line(line)


def list_downtime_codes_service() -> List[Dict[str, Any]]:
    return list_downtime_codes()


def list_tools(line: str, include_unassigned: bool = True) -> List[str]:
    return list_tools_for_line(line, include_unassigned=include_unassigned)


def get_tool_info(tool_num: str) -> Optional[Dict[str, Any]]:
    return get_tool(tool_num)


def get_tool_inserts(tool_num: str) -> List[Dict[str, Any]]:
    return list_tool_inserts(tool_num)


def _calculate_insert_cost(inserts: List[Dict[str, Any]]) -> float:
    total = 0.0
    for ins in inserts:
        count = float(ins.get("insert_count", 0) or 0)
        price = float(ins.get("price_per_insert", 0) or 0)
        life = float(ins.get("tool_life", 0) or 0)
        sides = float(ins.get("sides_per_insert", 1) or 1)
        if life <= 0 or sides <= 0:
            continue
        total += ((count * price) / life) / sides
    return total


def create_tool_change_entry(
    entry: Dict[str, Any],
    *,
    tool_num: str,
    new_stock_qty: Optional[int],
    actor_user: Actor | Dict[str, str] | None,
) -> float:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "create_tool_change_entry", "Tool Changer")
    validate_tool_change_entry(entry)

    inserts = list_tool_inserts(tool_num)
    cost = _calculate_insert_cost(inserts)
    info = get_tool(tool_num)
    if info and not inserts:
        cost = float(info.get("unit_cost", 0.0) or 0.0)

    apply_tool_change(entry, tool_num=tool_num, new_stock_qty=new_stock_qty, updated_by=actor.username)
    log_audit(actor.username, f"Tool change entry {entry.get('ID')} saved")
    return cost


def create_shift_report(
    entry: Dict[str, Any],
    downtime_entries: List[Dict[str, Any]],
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "create_shift_report", "Operator")
    validate_tool_change_entry(entry)
    upsert_tool_entry_with_downtime(entry, downtime_entries)
    log_audit(actor.username, f"Shift production entry {entry.get('ID')} saved")


def update_tool_change_entry(
    entry: Dict[str, Any],
    *,
    actor_user: Actor | Dict[str, str] | None,
) -> None:
    actor = ensure_actor(actor_user)
    require_permission(actor, PERMISSION_KEY, "update_tool_change_entry", "Tool Changer")
    upsert_tool_entry_with_downtime(entry, [])
    log_audit(actor.username, f"Updated tool change entry {entry.get('ID')}")


def list_tool_change_entries() -> List[Dict[str, Any]]:
    return fetch_tool_entries()


def get_tool_change_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    for row in fetch_tool_entries():
        if row.get("id") == entry_id:
            return row
    return None


def get_production_goal_value(
    *, line: str, cell: str = "", machine: str = "", part_number: str = ""
) -> float:
    return get_production_goal(line, cell, machine, part_number)
