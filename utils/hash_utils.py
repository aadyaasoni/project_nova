"""
Module: HASHING AND IDEMPOTENCY
Owner: Aadyaa
Purpose:
- Generate hashes to avoid duplicate processing.
Responsibilities:
- Create row-level SHA256 hashes.
- Track processed rows.
- Support safe re-execution of pipeline.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List

import pandas as pd


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _normalize_value(v) for k, v in value.items()}
    return value


def _serialize_record(record: Dict[str, Any]) -> str:
    normalized = {str(k): _normalize_value(v) for k, v in record.items()}
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_hash(record: Dict[str, Any], algorithm: str = "sha256") -> str:
    """Generate a deterministic hash for a record."""
    serialized = _serialize_record(record)
    hasher = hashlib.new(algorithm)
    hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()


def hash_dataset(
    data: pd.DataFrame | List[Dict[str, Any]],
    hash_column: str = "_hash",
    algorithm: str = "sha256",
) -> pd.DataFrame | List[Dict[str, Any]]:
    """Add hash values to a dataset."""
    if isinstance(data, pd.DataFrame):
        df = data.copy()
        df[hash_column] = df.apply(
            lambda row: generate_hash(row.to_dict(), algorithm=algorithm), axis=1
        )
        return df

    if isinstance(data, list):
        hashed: List[Dict[str, Any]] = []
        for record in data:
            record_copy = dict(record)
            record_copy[hash_column] = generate_hash(record_copy, algorithm=algorithm)
            hashed.append(record_copy)
        return hashed

    raise TypeError("Unsupported data type for hashing")


def verify_hash(
    record: Dict[str, Any],
    expected_hash: str,
    algorithm: str = "sha256",
) -> tuple[bool, str]:
    """Verify a hash matches the record."""
    actual = generate_hash(record, algorithm=algorithm)
    return actual == expected_hash, actual


def get_hash_summary(df: pd.DataFrame, hash_column: str = "_hash") -> Dict[str, Any]:
    """Generate summary statistics for hashes."""
    if hash_column not in df.columns:
        raise ValueError(f"Hash column '{hash_column}' not found")
    total = len(df)
    unique = df[hash_column].nunique(dropna=False)
    duplicates = total - unique
    coverage = (unique / total * 100) if total else 0.0
    return {
        "total_records": total,
        "total_unique_hashes": unique,
        "hash_coverage": round(coverage, 2),
        "duplicate_hash_count": duplicates,
    }


def export_hashes(df: pd.DataFrame, export_file: str, hash_column: str = "_hash") -> bool:
    """Export hashes to a CSV file."""
    try:
        if hash_column in df.columns:
            df[[hash_column]].to_csv(export_file, index=False)
        else:
            df.to_csv(export_file, index=False)
        return True
    except Exception:
        return False
