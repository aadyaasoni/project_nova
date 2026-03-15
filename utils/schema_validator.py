"""
Module: SCHEMA VALIDATION
Owner: Aadyaa
Purpose:
- Validate incoming dataset schema.
Responsibilities:
- Compare source schema with expected schema.
- Detect missing columns.
- Detect datatype mismatches.
- Prevent schema drift before pipeline runs.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd

try:
    from dateutil import parser as date_parser
except Exception:  # pragma: no cover - fallback if dateutil is unavailable
    date_parser = None


def load_schema(schema_path: str) -> Dict[str, Any]:
    """Load a JSON schema file."""
    with open(schema_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return pd.isna(value)
    except Exception:
        return False


def _parse_datetime(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    if isinstance(value, str):
        if date_parser is not None:
            try:
                date_parser.parse(value)
                return True
            except Exception:
                return False
        try:
            datetime.fromisoformat(value)
            return True
        except Exception:
            return False
    return False


def _validate_type(value: Any, expected_type: str) -> bool:
    if expected_type == "int":
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        if isinstance(value, float) and value.is_integer():
            return True
        if isinstance(value, str):
            return value.strip().lstrip("-").isdigit()
        return False
    if expected_type == "float":
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value)
                return True
            except Exception:
                return False
        return False
    if expected_type == "str":
        return isinstance(value, str)
    if expected_type == "datetime":
        return _parse_datetime(value)
    return False


def validate_record(
    record: Dict[str, Any],
    schema: Dict[str, Any],
    row_index: int | None = None,
) -> Tuple[bool, List[str]]:
    """Validate a single record against the schema."""
    errors: List[str] = []
    columns = schema.get("columns", {})

    for column, rules in columns.items():
        required = rules.get("required", False)
        expected_type = rules.get("type")
        value = record.get(column)

        if required and _is_missing(value):
            errors.append(f"missing_required:{column}")
            continue

        if _is_missing(value):
            continue

        if expected_type and not _validate_type(value, expected_type):
            errors.append(f"type_mismatch:{column}")

    # Row-level range checks
    row_checks = schema.get("row_checks", {})
    value_range = row_checks.get("value_range")
    if value_range and "value" in record and not _is_missing(record.get("value")):
        try:
            numeric_value = float(record.get("value"))
            min_val = value_range.get("min")
            max_val = value_range.get("max")
            if min_val is not None and numeric_value < min_val:
                errors.append("range_violation:value")
            if max_val is not None and numeric_value > max_val:
                errors.append("range_violation:value")
        except Exception:
            errors.append("type_mismatch:value")

    if errors:
        prefix = f"row {row_index}:" if row_index is not None else "row:"
        errors = [f"{prefix}{error}" for error in errors]

    return len(errors) == 0, errors


def validate_dataset(
    df: pd.DataFrame,
    schema: Dict[str, Any],
    return_errors: bool = False,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Validate a dataset against the schema."""
    invalid_records: List[Dict[str, Any]] = []
    columns = schema.get("columns", {})

    unique_columns = [col for col, rules in columns.items() if rules.get("unique")]
    duplicate_mask = pd.Series(False, index=df.index)
    duplicate_columns: Dict[int, List[str]] = {}

    for column in unique_columns:
        if column in df.columns:
            dupes = df[column].duplicated(keep=False)
            duplicate_mask = duplicate_mask | dupes
            for idx in df[dupes].index.tolist():
                duplicate_columns.setdefault(idx, []).append(column)

    for idx, row in df.iterrows():
        record = row.to_dict()
        is_valid, errors = validate_record(record, schema, row_index=int(idx))

        if idx in duplicate_columns:
            for column in duplicate_columns[idx]:
                errors.append(f"row {idx}:duplicate_value:{column}")
            is_valid = False

        if not is_valid:
            invalid_records.append({"index": int(idx), "record": record, "errors": errors})

    is_dataset_valid = len(invalid_records) == 0
    if return_errors:
        return is_dataset_valid, invalid_records
    return is_dataset_valid, []


def get_validation_summary(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate summary statistics for dataset validation."""
    is_valid, invalid_records = validate_dataset(df, schema, return_errors=True)
    total = len(df)
    invalid = len(invalid_records)
    valid = total - invalid

    error_categories: Dict[str, int] = {}
    for record in invalid_records:
        for error in record.get("errors", []):
            category = error.split(":", 1)[-1].split(":", 1)[0]
            error_categories[category] = error_categories.get(category, 0) + 1

    return {
        "total_records": total,
        "valid_records": valid,
        "invalid_records": invalid,
        "valid_percentage": (valid / total * 100) if total else 0.0,
        "error_categories": error_categories,
        "is_valid": is_valid,
    }
