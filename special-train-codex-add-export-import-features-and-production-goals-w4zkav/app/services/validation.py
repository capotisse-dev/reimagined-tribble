from __future__ import annotations

from typing import Any, Dict, Iterable

from ..exceptions import ValidationError


REQUIRED_TOOL_CHANGE_FIELDS = {
    "ID",
    "Date",
    "Time",
    "Line",
    "Machine",
    "Tool_Num",
    "Reason",
}

REQUIRED_SCRAP_FIELDS = {"scrap_id", "part_number", "line", "qty", "reported_by"}
REQUIRED_GAGE_CHECK_FIELDS = {"Verify_ID", "Gage_ID", "Result", "Verified_By"}
REQUIRED_PROGRAM_REV_FIELDS = {"filename", "scope_type"}
REQUIRED_PRINT_REV_FIELDS = {"filename", "scope_type"}
REQUIRED_MACHINE_HISTORY_FIELDS = {"line", "machine", "doc_type", "doc_name"}


def _missing_fields(data: Dict[str, Any], required: Iterable[str]) -> list[str]:
    missing = []
    for field in required:
        value = data.get(field)
        if value is None or str(value).strip() == "":
            missing.append(field)
    return missing


def validate_tool_change_entry(entry: Dict[str, Any]) -> None:
    missing = _missing_fields(entry, REQUIRED_TOOL_CHANGE_FIELDS)
    if missing:
        raise ValidationError(f"Missing required tool change fields: {', '.join(missing)}")


def validate_scrap_event(entry: Dict[str, Any]) -> None:
    missing = _missing_fields(entry, REQUIRED_SCRAP_FIELDS)
    if missing:
        raise ValidationError(f"Missing required scrap fields: {', '.join(missing)}")


def validate_gage_check(entry: Dict[str, Any]) -> None:
    missing = _missing_fields(entry, REQUIRED_GAGE_CHECK_FIELDS)
    if missing:
        raise ValidationError(f"Missing required gage check fields: {', '.join(missing)}")


def validate_program_revision(payload: Dict[str, Any]) -> None:
    missing = _missing_fields(payload, REQUIRED_PROGRAM_REV_FIELDS)
    if missing:
        raise ValidationError(f"Missing required program revision fields: {', '.join(missing)}")


def validate_print_revision(payload: Dict[str, Any]) -> None:
    missing = _missing_fields(payload, REQUIRED_PRINT_REV_FIELDS)
    if missing:
        raise ValidationError(f"Missing required print revision fields: {', '.join(missing)}")


def validate_machine_history_entry(entry: Dict[str, Any]) -> None:
    missing = _missing_fields(entry, REQUIRED_MACHINE_HISTORY_FIELDS)
    if missing:
        raise ValidationError(f"Missing required machine history fields: {', '.join(missing)}")
