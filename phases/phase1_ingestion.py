"""
Phase 1 - Data Ingestion and Validation Module

Objective:
Ingest raw data, validate its structure, and separate valid records from anomalous ones.

Responsibilities:
1. Load raw dataset from data/raw/
2. Validate dataset schema using predefined rules
3. Perform row-level validation checks
4. Separate rows into clean and anomalous groups
5. Save output datasets to data/clean/ and data/anomalies/
6. Log all ingestion events
7. Update pipeline context with statistics
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Any, List
import hashlib

# Configure logging
def setup_logger(log_dir: str = None) -> logging.Logger:
    """Set up logging for Phase 1 ingestion."""
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger('phase1_ingestion')
    logger.setLevel(logging.DEBUG)
    
    # File handler
    log_file = os.path.join(log_dir, f'phase1_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


logger = setup_logger()


# ============================================================================
# Configuration and Schema Definition
# ============================================================================

def get_default_schema() -> Dict[str, Any]:
    """
    Define the expected schema for the raw dataset.
    
    Can be extended or loaded from a JSON config file.
    Update this to match your actual data structure.
    """
    return {
        'columns': {
            'id': {'type': 'int', 'required': True, 'unique': True},
            'timestamp': {'type': 'datetime', 'required': True},
            'value': {'type': 'float', 'required': True},
            'category': {'type': 'str', 'required': True},
            'description': {'type': 'str', 'required': False},
        },
        'row_checks': {
            'value_range': {'min': 0, 'max': 1000},  # Example range check
        }
    }


def load_schema(schema_path: str = None) -> Dict[str, Any]:
    """
    Load schema from JSON file or use default schema.
    
    Args:
        schema_path: Path to JSON schema file
        
    Returns:
        Dictionary containing schema definition
    """
    if schema_path and os.path.exists(schema_path):
        logger.info(f"Loading schema from {schema_path}")
        with open(schema_path, 'r') as f:
            return json.load(f)
    else:
        logger.info("Using default schema")
        return get_default_schema()


# ============================================================================
# Validation Functions
# ============================================================================

def validate_schema(df: pd.DataFrame, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that the dataframe schema matches the expected schema.
    
    Args:
        df: Dataframe to validate
        schema: Schema definition
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required columns exist
    required_columns = [
        col for col, config in schema['columns'].items()
        if config.get('required', False)
    ]
    
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
    
    # Check that all columns in DataFrame are expected
    expected_columns = set(schema['columns'].keys())
    unexpected_columns = set(df.columns) - expected_columns
    if unexpected_columns:
        logger.warning(f"Unexpected columns found: {unexpected_columns}")
    
    return len(errors) == 0, errors


def validate_row(row: pd.Series, schema: Dict[str, Any], row_index: int) -> Tuple[bool, List[str]]:
    """
    Validate a single row against the schema.
    
    Args:
        row: Row to validate
        schema: Schema definition
        row_index: Index of the row (for error reporting)
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Column-level validation
    for col, col_config in schema['columns'].items():
        if col not in row.index:
            continue
        
        value = row[col]
        is_required = col_config.get('required', False)
        expected_type = col_config.get('type', 'str')
        
        # Check for missing/null values
        if pd.isna(value):
            if is_required:
                errors.append(f"Row {row_index}, Column '{col}': Required field is null")
            continue
        
        # Type validation
        try:
            if expected_type == 'int':
                if not isinstance(value, (int, np.integer)):
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        errors.append(f"Row {row_index}, Column '{col}': Expected int, got {type(value).__name__}")
            
            elif expected_type == 'float':
                if not isinstance(value, (float, int, np.number)):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        errors.append(f"Row {row_index}, Column '{col}': Expected float, got {type(value).__name__}")
            
            elif expected_type == 'str':
                if not isinstance(value, str):
                    errors.append(f"Row {row_index}, Column '{col}': Expected str, got {type(value).__name__}")
            
            elif expected_type == 'datetime':
                try:
                    pd.to_datetime(value)
                except Exception:
                    errors.append(f"Row {row_index}, Column '{col}': Invalid datetime format")
        
        except Exception as e:
            errors.append(f"Row {row_index}, Column '{col}': Type validation error - {str(e)}")
    
    # Row-level range checks
    if 'value_range' in schema.get('row_checks', {}):
        if 'value' in row and not pd.isna(row['value']):
            val_range = schema['row_checks']['value_range']
            value = row['value']
            try:
                value_float = float(value)
                if not (val_range['min'] <= value_float <= val_range['max']):
                    errors.append(
                        f"Row {row_index}, 'value': Out of range "
                        f"[{val_range['min']}, {val_range['max']}], got {value_float}"
                    )
            except (ValueError, TypeError):
                errors.append(f"Row {row_index}, 'value': Cannot convert to float for range check")
    
    return len(errors) == 0, errors


def validate_uniqueness(df: pd.DataFrame, schema: Dict[str, Any]) -> Tuple[pd.DataFrame, List[int]]:
    """
    Check for duplicate entries based on unique column constraints.
    
    Args:
        df: Dataframe to validate
        schema: Schema definition
        
    Returns:
        Tuple of (dataframe_with_dup_flags, duplicate_indices)
    """
    duplicate_indices = []
    
    unique_columns = [
        col for col, config in schema['columns'].items()
        if config.get('unique', False)
    ]
    
    if unique_columns:
        duplicates = df[unique_columns].duplicated(keep=False)
        duplicate_indices = df[duplicates].index.tolist()
    
    return duplicate_indices


# ============================================================================
# Main Ingestion Pipeline
# ============================================================================

def load_raw_data(raw_dir: str) -> pd.DataFrame:
    """
    Load all CSV files from the raw data directory.
    
    Args:
        raw_dir: Path to raw data directory
        
    Returns:
        Concatenated dataframe from all CSV files
    """
    logger.info(f"Loading raw data from {raw_dir}")
    
    if not os.path.exists(raw_dir):
        raise ValueError(f"Raw data directory does not exist: {raw_dir}")
    
    csv_files = [f for f in os.listdir(raw_dir) if f.endswith('.csv')]
    
    if not csv_files:
        logger.warning(f"No CSV files found in {raw_dir}")
        return pd.DataFrame()
    
    logger.info(f"Found {len(csv_files)} CSV file(s): {csv_files}")
    
    dataframes = []
    for csv_file in csv_files:
        file_path = os.path.join(raw_dir, csv_file)
        logger.info(f"Reading {csv_file}")
        try:
            df = pd.read_csv(file_path)
            dataframes.append(df)
            logger.info(f"  - Loaded {len(df)} rows, {len(df.columns)} columns")
        except Exception as e:
            logger.error(f"  - Error reading {csv_file}: {str(e)}")
    
    if not dataframes:
        raise ValueError("No valid CSV files could be loaded")
    
    combined_df = pd.concat(dataframes, ignore_index=True)
    logger.info(f"Total rows after combining: {len(combined_df)}")
    
    return combined_df


def ingest_and_validate(
    raw_dir: str,
    clean_dir: str,
    anomalies_dir: str,
    schema_path: str = None,
    log_dir: str = None
) -> Dict[str, Any]:
    """
    Complete Phase 1 ingestion and validation pipeline.
    
    Args:
        raw_dir: Path to raw data directory
        clean_dir: Path to clean data output directory
        anomalies_dir: Path to anomalies output directory
        schema_path: Optional path to schema JSON file
        log_dir: Optional path to logs directory
        
    Returns:
        Dictionary containing pipeline statistics and metadata
    """
    context = {
        'phase': 1,
        'timestamp': datetime.now().isoformat(),
        'status': 'in_progress',
        'stats': {
            'total_rows': 0,
            'clean_rows': 0,
            'anomalous_rows': 0,
        },
        'errors': []
    }
    
    try:
        logger.info("=" * 70)
        logger.info("PHASE 1 - DATA INGESTION AND VALIDATION")
        logger.info("=" * 70)
        
        # Load schema
        schema = load_schema(schema_path)
        
        # Load raw data
        raw_df = load_raw_data(raw_dir)
        context['stats']['total_rows'] = len(raw_df)
        
        if len(raw_df) == 0:
            logger.warning("No data loaded. Exiting.")
            context['status'] = 'completed_empty'
            return context
        
        logger.info(f"\nValidating schema...")
        schema_valid, schema_errors = validate_schema(raw_df, schema)
        if not schema_valid:
            for error in schema_errors:
                logger.error(f"  - {error}")
                context['errors'].append(error)
            raise ValueError("Schema validation failed")
        logger.info("  Schema validation: PASSED")
        
        # Check for duplicates based on unique constraints
        logger.info(f"\nChecking for duplicate records...")
        duplicate_indices = validate_uniqueness(raw_df, schema)
        
        # Validate each row
        logger.info(f"\nValidating {len(raw_df)} rows...")
        clean_mask = []
        anomaly_reasons = []
        
        for idx, row in raw_df.iterrows():
            is_valid, row_errors = validate_row(row, schema, idx)
            
            # Mark as anomalous if it has duplicate ID or validation errors
            if idx in duplicate_indices:
                is_valid = False
                row_errors.append(f"Row {idx}: Duplicate record detected")
            
            clean_mask.append(is_valid)
            anomaly_reasons.append(row_errors if not is_valid else [])
            
            if not is_valid and len(row_errors) <= 3:  # Log only first few errors
                logger.debug(f"  Row {idx} marked as anomalous: {row_errors}")
        
        clean_mask = pd.Series(clean_mask, index=raw_df.index)
        
        # Separate clean and anomalous data
        clean_df = raw_df[clean_mask].copy()
        anomalous_df = raw_df[~clean_mask].copy()
        
        context['stats']['clean_rows'] = len(clean_df)
        context['stats']['anomalous_rows'] = len(anomalous_df)
        
        logger.info(f"\nValidation Results:")
        logger.info(f"  - Total rows: {len(raw_df)}")
        logger.info(f"  - Clean rows: {len(clean_df)} ({len(clean_df)/len(raw_df)*100:.2f}%)")
        logger.info(f"  - Anomalous rows: {len(anomalous_df)} ({len(anomalous_df)/len(raw_df)*100:.2f}%)")
        
        # Save outputs
        logger.info(f"\nSaving outputs...")
        os.makedirs(clean_dir, exist_ok=True)
        os.makedirs(anomalies_dir, exist_ok=True)
        
        clean_output = os.path.join(clean_dir, 'clean_data.csv')
        anomalies_output = os.path.join(anomalies_dir, 'anomalies.csv')
        
        clean_df.to_csv(clean_output, index=False)
        logger.info(f"  - Saved clean data to {clean_output}")
        
        if len(anomalous_df) > 0:
            # Add error reasons column for anomalies
            anomalous_df = anomalous_df.copy()
            # Get indices where clean_mask is False
            anomalous_indices = clean_mask[~clean_mask].index
            # Map these indices to positions in the anomaly_reasons list
            anomalous_df['_anomaly_reasons'] = [
                str(anomaly_reasons[i]) for i in anomalous_indices
            ]
            anomalous_df.to_csv(anomalies_output, index=False)
            logger.info(f"  - Saved anomalies to {anomalies_output}")
        
        # Generate data integrity hash for reproducibility
        clean_hash = hashlib.md5(
            pd.util.hash_pandas_object(clean_df, index=True).values
        ).hexdigest()
        
        context['stats']['clean_data_hash'] = clean_hash
        context['stats']['raw_row_count'] = len(raw_df)
        context['status'] = 'completed_success'
        
        logger.info(f"\nClean data integrity hash: {clean_hash}")
        logger.info("=" * 70)
        logger.info("PHASE 1 COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"\nERROR during Phase 1: {str(e)}", exc_info=True)
        context['status'] = 'failed'
        context['errors'].append(str(e))
    
    return context


def save_pipeline_context(context: Dict[str, Any], context_file: str) -> None:
    """
    Save pipeline context to JSON file.
    
    Args:
        context: Pipeline context dictionary
        context_file: Path to save context JSON
    """
    os.makedirs(os.path.dirname(context_file), exist_ok=True)
    with open(context_file, 'w') as f:
        json.dump(context, f, indent=2)
    logger.info(f"Pipeline context saved to {context_file}")


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == '__main__':
    # Set up paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(project_root, 'data', 'raw')
    clean_dir = os.path.join(project_root, 'data', 'clean')
    anomalies_dir = os.path.join(project_root, 'data', 'anomalies')
    log_dir = os.path.join(project_root, 'logs')
    
    # Optional: specify schema file if it exists
    schema_file = os.path.join(project_root, 'config', 'schema.json')
    if not os.path.exists(schema_file):
        schema_file = None
    
    # Run ingestion
    context = ingest_and_validate(
        raw_dir=raw_dir,
        clean_dir=clean_dir,
        anomalies_dir=anomalies_dir,
        schema_path=schema_file,
        log_dir=log_dir
    )
    
    # Save context
    context_file = os.path.join(project_root, 'data', 'vault', 'phase1_context.json')
    save_pipeline_context(context, context_file)
    
    # Exit with appropriate status
    sys.exit(0 if context['status'] == 'completed_success' else 1)
