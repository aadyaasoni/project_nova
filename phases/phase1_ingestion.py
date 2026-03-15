"""
Module: PHASE 1 - DATA INGESTION
Owner: Aadyaa
Purpose:
- Load raw data and perform deterministic validation.
Responsibilities:
- Read files from data/raw.
- Perform rule-based validation.
- Split dataset into clean and anomaly datasets.
- Save results to data/clean and data/anomalies.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

from utils.schema_validator import load_schema, validate_record
from utils.hash_utils import generate_hash


logger = logging.getLogger(__name__)


def _load_json_records(file_path: str) -> List[Dict[str, Any]]:
    """Load records from a JSON file (list, dict, or JSONL)."""
    with open(file_path, "r", encoding="utf-8") as handle:
        content = handle.read().strip()
        if not content:
            return []
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            records: List[Dict[str, Any]] = []
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
            return records

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("records"), list):
            return payload["records"]
        return [payload]
    return []


def _load_records_from_raw(raw_dir: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Load records from JSON files in the raw directory."""
    json_files = [
        os.path.join(raw_dir, name)
        for name in os.listdir(raw_dir)
        if name.lower().endswith(".json")
    ]
    records: List[Dict[str, Any]] = []
    sources: List[str] = []

    for file_path in json_files:
        file_records = _load_json_records(file_path)
        records.extend(file_records)
        sources.extend([file_path] * len(file_records))

    if records:
        return records, sources

    # Backward-compatible fallback for CSV input
    csv_files = [
        os.path.join(raw_dir, name)
        for name in os.listdir(raw_dir)
        if name.lower().endswith(".csv")
    ]
    for file_path in csv_files:
        df = pd.read_csv(file_path)
        file_records = df.to_dict(orient="records")
        records.extend(file_records)
        sources.extend([file_path] * len(file_records))

    return records, sources


def run_phase1(raw_dir: str, schema_path: str) -> Dict[str, Any]:
    """
    Load records, validate each record, and split clean vs anomalies.
    """
    schema = load_schema(schema_path)
    records, sources = _load_records_from_raw(raw_dir)

    clean_records: List[Dict[str, Any]] = []
    anomalies: List[Dict[str, Any]] = []

    columns = schema.get("columns", {})
    unique_columns = [col for col, rules in columns.items() if rules.get("unique")]
    seen_values = {col: set() for col in unique_columns}

    for index, record in enumerate(records):
        record_copy = dict(record)
        is_valid, errors = validate_record(record_copy, schema, row_index=index)

        for column in unique_columns:
            value = record_copy.get(column)
            if value is None:
                continue
            if value in seen_values[column]:
                errors.append(f"row {index}:duplicate_value:{column}")
                is_valid = False
            else:
                seen_values[column].add(value)

        if is_valid:
            record_copy["_hash"] = generate_hash(record_copy)
            clean_records.append(record_copy)
        else:
            record_copy["_anomaly_reasons"] = errors
            if index < len(sources):
                record_copy["_source_file"] = sources[index]
            anomalies.append(record_copy)

    stats = {
        "total_rows": len(records),
        "clean_rows": len(clean_records),
        "anomalous_rows": len(anomalies),
    }

    return {
        "status": "completed_success" if records else "completed_empty",
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "clean_records": clean_records,
        "anomalies": anomalies,
    }


def save_results(
    clean_records: List[Dict[str, Any]],
    anomalies: List[Dict[str, Any]],
    clean_path: str,
    anomalies_path: str,
) -> Dict[str, str]:
    """Save clean and anomaly records to JSON files."""
    os.makedirs(os.path.dirname(clean_path), exist_ok=True)
    os.makedirs(os.path.dirname(anomalies_path), exist_ok=True)

    with open(clean_path, "w", encoding="utf-8") as handle:
        json.dump(clean_records, handle, indent=2, ensure_ascii=False, default=str)

    with open(anomalies_path, "w", encoding="utf-8") as handle:
        json.dump(anomalies, handle, indent=2, ensure_ascii=False, default=str)

    return {"clean": clean_path, "anomalies": anomalies_path}


def _save_csv_results(
    clean_records: List[Dict[str, Any]],
    anomalies: List[Dict[str, Any]],
    clean_csv: str,
    anomalies_csv: str,
) -> None:
    os.makedirs(os.path.dirname(clean_csv), exist_ok=True)
    os.makedirs(os.path.dirname(anomalies_csv), exist_ok=True)

    pd.DataFrame(clean_records).to_csv(clean_csv, index=False)
    pd.DataFrame(anomalies).to_csv(anomalies_csv, index=False)


def execute_phase1(
    raw_dir: str = os.path.join("data", "raw"),
    clean_path: str = os.path.join("data", "clean", "clean_data.json"),
    anomalies_path: str = os.path.join("data", "anomalies", "anomalies.json"),
    schema_path: str = os.path.join("config", "schema.json"),
    save_csv: bool = False,
    clean_csv: str | None = None,
    anomalies_csv: str | None = None,
) -> Dict[str, Any]:
    """
    Execute Phase 1 ingestion and persistence.
    """
    context = run_phase1(raw_dir=raw_dir, schema_path=schema_path)
    save_results(
        context["clean_records"],
        context["anomalies"],
        clean_path=clean_path,
        anomalies_path=anomalies_path,
    )

    if save_csv:
        clean_csv = clean_csv or os.path.join(os.path.dirname(clean_path), "clean_data.csv")
        anomalies_csv = anomalies_csv or os.path.join(os.path.dirname(anomalies_path), "anomalies.csv")
        _save_csv_results(context["clean_records"], context["anomalies"], clean_csv, anomalies_csv)

    return context


def ingest_and_validate(
    raw_dir: str,
    clean_dir: str,
    anomalies_dir: str,
    schema_path: str,
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for Phase 1 ingestion (CSV + JSON outputs).
    """
    clean_json = os.path.join(clean_dir, "clean_data.json")
    anomalies_json = os.path.join(anomalies_dir, "anomalies.json")
    clean_csv = os.path.join(clean_dir, "clean_data.csv")
    anomalies_csv = os.path.join(anomalies_dir, "anomalies.csv")

    return execute_phase1(
        raw_dir=raw_dir,
        clean_path=clean_json,
        anomalies_path=anomalies_json,
        schema_path=schema_path,
        save_csv=True,
        clean_csv=clean_csv,
        anomalies_csv=anomalies_csv,
    )


def save_pipeline_context(context: Dict[str, Any], context_path: str) -> None:
    """Persist Phase 1 context to disk."""
    os.makedirs(os.path.dirname(context_path), exist_ok=True)
    with open(context_path, "w", encoding="utf-8") as handle:
        json.dump(context, handle, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    execute_phase1()
