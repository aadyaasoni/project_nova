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

from utils.schema_validator import load_schema, validate_record, validate_schema, halt_on_drift, SchemaViolationError
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


def run(ctx):
    import os
    from datetime import datetime
    source_file = ctx.get('source_file', '')
    source_name = ctx.get('source_name', 'default')
    pk_columns = ctx.get('pk_columns', [])
    required_columns = ctx.get('required_columns', pk_columns)
    if not os.path.exists(source_file):
        ctx['phase1_status'] = 'error'
        ctx['phase1_error'] = f'File not found: {source_file}'
        ctx['phase1_row_counts'] = {'total': 0, 'clean': 0, 'anomalies': 0}
        ctx['phase1_clean_file'] = None
        ctx['phase1_anomaly_file'] = None
        return ctx
    try:
        df = pd.read_csv(source_file, dtype=str, keep_default_na=False, na_values=[''])
        schema_result = validate_schema(source_name, df)
        halt_on_drift(schema_result)
        if required_columns:
            valid_req = [c for c in required_columns if c in df.columns]
            has_null = df[valid_req].isnull().any(axis=1) if valid_req else pd.Series([False]*len(df))
        else:
            has_null = pd.Series([False]*len(df))
        clean_df = df[~has_null].copy()
        anomaly_df = df[has_null].copy()
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        clean_file = None
        anomaly_file = None
        if len(clean_df) > 0:
            os.makedirs('data/clean', exist_ok=True)
            clean_file = f'data/clean/{source_name}_clean_{ts}.csv'
            clean_df.to_csv(clean_file, index=False)
        if len(anomaly_df) > 0:
            anomaly_df['Validation_Status'] = 'NEEDS_AI'
            os.makedirs('data/anomalies', exist_ok=True)
            anomaly_file = f'data/anomalies/{source_name}_anomalies_{ts}.csv'
            anomaly_df.to_csv(anomaly_file, index=False)
        ctx['phase1_status'] = 'ok'
        ctx['phase1_clean_file'] = clean_file
        ctx['phase1_anomaly_file'] = anomaly_file
        ctx['phase1_row_counts'] = {'total': len(df), 'clean': len(clean_df), 'anomalies': len(anomaly_df)}
    except SchemaViolationError as e:
        ctx['phase1_status'] = 'schema_drift'
        ctx['phase1_error'] = str(e)
        ctx['phase1_clean_file'] = None
        ctx['phase1_anomaly_file'] = None
        ctx['phase1_row_counts'] = {'total': 0, 'clean': 0, 'anomalies': 0}
    except Exception as e:
        ctx['phase1_status'] = 'error'
        ctx['phase1_error'] = str(e)
        ctx['phase1_clean_file'] = None
        ctx['phase1_anomaly_file'] = None
        ctx['phase1_row_counts'] = {'total': 0, 'clean': 0, 'anomalies': 0}
    return ctx
