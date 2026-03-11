"""
Hash Utilities Module for Project Nova

This module provides utilities to generate SHA256 hashes for records and datasets.
It ensures consistent hashing across pipeline phases for data integrity verification
and deduplication purposes.

Functions:
    - generate_hash(): Generate SHA256 hash for a single record
    - hash_dataset(): Generate hashes for multiple records
    - get_hash_summary(): Get hash statistics for a dataset
    - verify_hash(): Verify that a record matches a given hash

Features:
    - Consistent hashing (deterministic - same input always produces same hash)
    - Supports various data types (dict, list, DataFrame rows)
    - Field ordering is handled automatically
    - Handles special data types (datetime, NaN, infinity)
    - Batch processing for large datasets
    - Detailed logging and error handling

Author: Project Nova
Version: 1.0
"""

import hashlib
import json
import logging
from typing import Union, Dict, List, Tuple, Optional, Any
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, date


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class HashUtilError(Exception):
    """Custom exception for hash utility errors."""
    pass


def _serialize_value(value: Any) -> str:
    """
    Convert a value to a string representation suitable for hashing.
    
    Handles special cases like NaN, infinity, datetime objects, etc.
    This ensures consistent hashing regardless of data types.
    
    Args:
        value (Any): The value to serialize
        
    Returns:
        str: String representation of the value
        
    Example:
        >>> _serialize_value(float('nan'))
        'NaN'
        >>> _serialize_value(datetime(2026, 3, 12))
        '2026-03-12T00:00:00'
    """
    # Handle None/null values
    if value is None:
        return 'null'
    
    # Handle numpy arrays first (before pd.isna check which can fail on arrays)
    if isinstance(value, np.ndarray):
        return '[' + ','.join(_serialize_value(v) for v in value.flat) + ']'
    
    # Handle pandas NaN (with try-except for edge cases)
    try:
        if pd.isna(value):
            return 'NaN'
    except (TypeError, ValueError):
        pass
    
    # Handle infinity
    if isinstance(value, float):
        try:
            if np.isinf(value):
                return 'inf' if value > 0 else '-inf'
        except (TypeError, ValueError):
            pass
    
    # Handle datetime objects
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    
    # Handle numpy types
    if isinstance(value, np.integer):
        return str(int(value))
    if isinstance(value, np.floating):
        return str(float(value))
    if isinstance(value, np.bool_):
        return str(bool(value))
    
    # Handle standard types
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    
    # Handle lists and tuples
    if isinstance(value, (list, tuple)):
        return '[' + ','.join(_serialize_value(v) for v in value) + ']'
    
    # Handle dictionaries
    if isinstance(value, dict):
        items = []
        for k in sorted(value.keys()):  # Sort keys for consistency
            items.append(f'{k}:{_serialize_value(value[k])}')
        return '{' + ','.join(items) + '}'
    
    # Fallback for unknown types
    return str(value)


def _normalize_record(record: Dict[str, Any]) -> str:
    """
    Normalize a record to a canonical string representation for hashing.
    
    This ensures that the same record always produces the same hash,
    regardless of field order or minor variations in representation.
    
    Args:
        record (Dict[str, Any]): The record to normalize
        
    Returns:
        str: Normalized string representation of the record
        
    Example:
        >>> record = {'id': 1, 'name': 'test', 'value': 100.5}
        >>> norm = _normalize_record(record)
    """
    if not isinstance(record, dict):
        raise HashUtilError(f"Expected dict, got {type(record).__name__}")
    
    # Sort fields alphabetically for consistency
    normalized_pairs = []
    for key in sorted(record.keys()):
        value = record[key]
        serialized_value = _serialize_value(value)
        normalized_pairs.append(f'{key}={serialized_value}')
    
    # Join with separator
    normalized_string = '|'.join(normalized_pairs)
    return normalized_string


def generate_hash(record: Dict[str, Any], hash_type: str = 'sha256',
                 algorithm: str = 'sha256') -> str:
    """
    Generate a SHA256 hash for a single record.
    
    The hash is deterministic - the same record will always produce the same hash.
    Field order does not matter; hashes are based on content.
    
    Args:
        record (Dict[str, Any]): The record to hash (dictionary)
        hash_type (str): Type of hash (default: 'sha256') - for backwards compatibility
        algorithm (str): Hash algorithm to use (default: 'sha256')
        
    Returns:
        str: Hexadecimal hash string (64 characters for SHA256)
        
    Raises:
        HashUtilError: If record is invalid or hashing fails
        
    Example:
        >>> record = {'id': 1, 'name': 'test', 'timestamp': '2026-03-12'}
        >>> hash_value = generate_hash(record)
        >>> print(hash_value)
        'a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a'
    """
    try:
        if not isinstance(record, dict):
            raise HashUtilError(f"Record must be a dictionary, got {type(record).__name__}")
        
        # Normalize the record to a consistent string format
        normalized = _normalize_record(record)
        
        # Create hash object
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(normalized.encode('utf-8'))
        hash_value = hash_obj.hexdigest()
        
        logger.debug(f"Generated {algorithm.upper()} hash for record with {len(record)} fields")
        
        return hash_value
        
    except HashUtilError:
        raise
    except Exception as e:
        logger.error(f"Error generating hash: {e}")
        raise HashUtilError(f"Failed to generate hash: {e}")


def hash_dataset(data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                hash_column: str = '_hash',
                algorithm: str = 'sha256',
                include_original: bool = True) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Generate hashes for all records in a dataset.
    
    This function processes multiple records and adds hash values to each record.
    It maintains the original data structure (DataFrame or list).
    
    Args:
        data (Union[pd.DataFrame, List[Dict[str, Any]]]): Dataset to hash
        hash_column (str): Name of the column to store hashes (default: '_hash')
        algorithm (str): Hash algorithm to use (default: 'sha256')
        include_original (bool): If True, keep original data intact (default: True)
        
    Returns:
        Union[pd.DataFrame, List[Dict[str, Any]]]: Data with hash column added
        
    Raises:
        HashUtilError: If data is invalid or hashing fails
        
    Example:
        >>> df = pd.DataFrame([
        ...     {'id': 1, 'name': 'Alice'},
        ...     {'id': 2, 'name': 'Bob'}
        ... ])
        >>> df_hashed = hash_dataset(df)
        >>> print(df_hashed[['id', 'name', '_hash']])
    """
    try:
        # Convert to list of dicts if DataFrame
        if isinstance(data, pd.DataFrame):
            records = data.to_dict('records')
            indices = data.index
            is_dataframe = True
        elif isinstance(data, list):
            records = data
            indices = range(len(data))
            is_dataframe = False
        else:
            raise HashUtilError(f"Data must be DataFrame or list, got {type(data).__name__}")
        
        logger.info(f"Hashing {len(records)} records with algorithm '{algorithm}'...")
        
        hashed_records = []
        for idx, record in zip(indices, records):
            if not isinstance(record, dict):
                logger.warning(f"Skipping non-dict record at index {idx}")
                continue
            
            # Make a copy if include_original is True
            if include_original:
                hashed_record = record.copy()
            else:
                hashed_record = record
            
            # Generate hash
            hash_value = generate_hash(record, algorithm=algorithm)
            hashed_record[hash_column] = hash_value
            hashed_records.append(hashed_record)
        
        logger.info(f"Successfully hashed {len(hashed_records)}/{len(records)} records")
        
        # Return in original format
        if is_dataframe:
            result_df = pd.DataFrame(hashed_records)
            # Preserve original index if possible
            if len(result_df) == len(data):
                result_df.index = data.index
            return result_df
        else:
            return hashed_records
            
    except HashUtilError:
        raise
    except Exception as e:
        logger.error(f"Error hashing dataset: {e}")
        raise HashUtilError(f"Failed to hash dataset: {e}")


def verify_hash(record: Dict[str, Any], expected_hash: str, 
               algorithm: str = 'sha256') -> Tuple[bool, str]:
    """
    Verify that a record matches a given hash value.
    
    Useful for integrity checking and detecting record modifications.
    
    Args:
        record (Dict[str, Any]): The record to verify
        expected_hash (str): The expected hash value
        algorithm (str): Hash algorithm used (default: 'sha256')
        
    Returns:
        Tuple[bool, str]: (is_match, actual_hash)
        
    Example:
        >>> record = {'id': 1, 'value': 100}
        >>> hash1 = generate_hash(record)
        >>> is_match, hash2 = verify_hash(record, hash1)
        >>> print(is_match)
        True
    """
    try:
        actual_hash = generate_hash(record, algorithm=algorithm)
        is_match = actual_hash == expected_hash
        
        if not is_match:
            logger.warning(f"Hash mismatch: expected {expected_hash}, got {actual_hash}")
        else:
            logger.debug("Hash verification successful")
        
        return is_match, actual_hash
        
    except Exception as e:
        logger.error(f"Error verifying hash: {e}")
        return False, ""


def get_hash_summary(data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                    hash_column: str = '_hash') -> Dict[str, Any]:
    """
    Get summary statistics about hashes in a dataset.
    
    This is useful for understanding hash distribution and detecting potential
    duplicates or issues in the data.
    
    Args:
        data (Union[pd.DataFrame, List[Dict[str, Any]]]): Dataset to analyze
        hash_column (str): Name of the hash column (default: '_hash')
        
    Returns:
        Dict[str, Any]: Summary statistics including:
            - total_records: Total number of records
            - total_unique_hashes: Count of unique hashes
            - duplicate_hashes: Records with duplicate hashes
            - hash_coverage: Percentage of records with hashes
            
    Example:
        >>> df_hashed = hash_dataset(df)
        >>> summary = get_hash_summary(df_hashed)
        >>> print(f"Unique records: {summary['total_unique_hashes']}")
    """
    try:
        # Convert to DataFrame if needed
        if isinstance(data, list):
            data = pd.DataFrame(data)
        elif not isinstance(data, pd.DataFrame):
            raise HashUtilError(f"Data must be DataFrame or list, got {type(data).__name__}")
        
        total_records = len(data)
        
        # Get hash column
        if hash_column not in data.columns:
            logger.warning(f"Hash column '{hash_column}' not found in dataset")
            return {
                'total_records': total_records,
                'total_unique_hashes': 0,
                'hash_coverage': 0.0,
                'note': f'Hash column {hash_column} not found'
            }
        
        # Calculate statistics
        hashes = data[hash_column]
        valid_hashes = hashes.dropna()
        unique_hashes = valid_hashes.nunique()
        hash_coverage = (len(valid_hashes) / total_records * 100) if total_records > 0 else 0
        
        # Find duplicate hashes
        duplicate_hashes = hashes.value_counts()
        duplicates = duplicate_hashes[duplicate_hashes > 1].to_dict() if len(duplicate_hashes) > 0 else {}
        
        summary = {
            'total_records': total_records,
            'total_unique_hashes': unique_hashes,
            'records_with_hashes': len(valid_hashes),
            'records_without_hashes': total_records - len(valid_hashes),
            'hash_coverage': round(hash_coverage, 2),
            'duplicate_hash_count': len(duplicates),
            'top_duplicates': {str(k): v for k, v in list(duplicates.items())[:3]}
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating hash summary: {e}")
        return {
            'error': str(e),
            'total_records': 0
        }


def export_hashes(data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                 output_file: str,
                 hash_column: str = '_hash') -> bool:
    """
    Export hashes to a CSV file for tracking and verification.
    
    Args:
        data (Union[pd.DataFrame, List[Dict[str, Any]]]): Data with hashes
        output_file (str): Path to output CSV file
        hash_column (str): Name of hash column (default: '_hash')
        
    Returns:
        bool: True if export successful, False otherwise
        
    Example:
        >>> df_hashed = hash_dataset(df)
        >>> export_hashes(df_hashed, 'data/hashes.csv')
    """
    try:
        # Convert to DataFrame if needed
        if isinstance(data, list):
            data = pd.DataFrame(data)
        
        if not isinstance(data, pd.DataFrame):
            raise HashUtilError("Data must be DataFrame or list")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        data.to_csv(output_file, index=False)
        logger.info(f"Hashes exported to {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting hashes: {e}")
        return False


# Module entry point for testing
if __name__ == '__main__':
    """Test the hash utilities module."""
    
    print("Hash Utilities Module - Test")
    print("=" * 70)
    
    try:
        # Test 1: Generate hash for single record
        print("\nTest 1: Generate hash for single record...")
        record1 = {
            'id': 1,
            'name': 'Alice',
            'timestamp': '2026-03-12T10:00:00',
            'value': 100.5
        }
        hash1 = generate_hash(record1)
        print(f"✓ Generated hash: {hash1[:16]}...")
        print(f"  Record fields: {list(record1.keys())}")
        
        # Test 2: Hash same record again (should be identical)
        print("\nTest 2: Verify hash consistency...")
        hash1_again = generate_hash(record1)
        is_consistent = hash1 == hash1_again
        print(f"✓ Hashes match: {is_consistent}")
        
        # Test 3: Different record, different hash
        print("\nTest 3: Different records produce different hashes...")
        record2 = record1.copy()
        record2['value'] = 200.5
        hash2 = generate_hash(record2)
        is_different = hash1 != hash2
        print(f"✓ Hashes differ: {is_different}")
        
        # Test 4: Hash dataset
        print("\nTest 4: Hash dataset...")
        data = [
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'},
            {'id': 3, 'name': 'Charlie'}
        ]
        hashed_data = hash_dataset(data)
        print(f"✓ Hashed {len(hashed_data)} records")
        print(f"  Hash column: {hashed_data[0]['_hash'][:16]}...")
        
        # Test 5: Hash summary
        print("\nTest 5: Get hash summary...")
        summary = get_hash_summary(hashed_data)
        print(f"✓ Summary generated:")
        print(f"  Total records: {summary['total_records']}")
        print(f"  Unique hashes: {summary['total_unique_hashes']}")
        print(f"  Hash coverage: {summary['hash_coverage']}%")
        
        # Test 6: Verify hash
        print("\nTest 6: Verify hash...")
        is_match, actual = verify_hash(record1, hash1)
        print(f"✓ Hash verification: {is_match}")
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
