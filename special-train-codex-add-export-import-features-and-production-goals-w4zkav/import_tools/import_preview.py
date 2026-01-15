from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd


@dataclass
class PreviewRow:
    status: str
    data: Dict[str, Any]
    diffs: Dict[str, Tuple[Any, Any]]
    error: str = ""


def load_import_file(path: str) -> pd.DataFrame:
    if path.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(path)
    return pd.read_csv(path)


def normalize_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in mapping:
            rename[col] = mapping[key]
    return df.rename(columns=rename)


def build_preview(
    *,
    df: pd.DataFrame,
    mapping: Dict[str, str],
    required_fields: List[str],
    existing_records: Dict[str, Dict[str, Any]],
    key_field: str,
) -> Tuple[List[PreviewRow], Dict[str, int]]:
    df = normalize_columns(df, mapping)
    rows: List[PreviewRow] = []
    summary = {"NEW": 0, "UPDATE": 0, "DUPLICATE": 0, "ERROR": 0}

    for _, row in df.iterrows():
        data = {k: (row.get(k) if k in row else None) for k in mapping.values()}
        missing = [field for field in required_fields if not str(data.get(field, "")).strip()]
        if missing:
            rows.append(PreviewRow(status="ERROR", data=data, diffs={}, error=f"Missing {', '.join(missing)}"))
            summary["ERROR"] += 1
            continue

        key = str(data.get(key_field, "")).strip()
        existing = existing_records.get(key)
        if not existing:
            rows.append(PreviewRow(status="NEW", data=data, diffs={}))
            summary["NEW"] += 1
            continue

        diffs = {}
        for field in data.keys():
            old_val = existing.get(field)
            new_val = data.get(field)
            if str(old_val) != str(new_val):
                diffs[field] = (old_val, new_val)
        if diffs:
            rows.append(PreviewRow(status="UPDATE", data=data, diffs=diffs))
            summary["UPDATE"] += 1
        else:
            rows.append(PreviewRow(status="DUPLICATE", data=data, diffs={}))
            summary["DUPLICATE"] += 1

    return rows, summary
