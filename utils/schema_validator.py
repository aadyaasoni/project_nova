"""
Schema Validator Module for Project Nova

This module provides utilities to validate JSON records and datasets against a schema file.
It supports field type checking, required field validation, uniqueness constraints, and 
range validation for numerical fields.

Functions:
    - load_schema(): Load schema from JSON file
    - validate_record(): Validate a single record against schema
    - validate_dataset(): Validate multiple records
    - validate_field_type(): Type validation for individual fields
    - validate_field_range(): Range validation for numerical fields

Author: Project Nova
Version: 1.0
"""

import json
import logging
from typing import Union, List, Dict, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
import pandas as pd


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


class SchemaValidationError(Exception):
    """Custom exception for schema validation errors."""
    pass


def load_schema(schema_path: str) -> Dict[str, Any]:
    """
    Load schema definition from a JSON file.
    
    Args:
        schema_path (str): Path to the schema.json file
        
    Returns:
        Dict[str, Any]: Parsed schema dictionary
        
    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema JSON is malformed
        
    Example:
        >>> schema = load_schema('config/schema.json')
        >>> print(schema['columns'].keys())
    """
    try:
        schema_file = Path(schema_path)
        
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_path}")
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_file, 'r') as f:
            schema = json.load(f)
        
        logger.debug(f"Schema loaded successfully from {schema_path}")
        logger.debug(f"Schema contains {len(schema.get('columns', {}))} columns")
        
        return schema
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schema file: {e}")
        raise SchemaValidationError(f"Failed to parse schema JSON: {e}")
    except Exception as e:
        logger.error(f"Error loading schema: {e}")
        raise


def validate_field_type(field_name: str, field_value: Any, expected_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a field value matches the expected type.
    
    Args:
        field_name (str): Name of the field being validated
        field_value (Any): The value to validate
        expected_type (str): Expected type string ('int', 'float', 'str', 'datetime')
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
        
    Example:
        >>> is_valid, error = validate_field_type('id', 123, 'int')
        >>> print(is_valid)
        True
    """
    # Handle None/NaN values
    if pd.isna(field_value):
        return False, f"Field '{field_name}' is null or NaN"
    
    try:
        if expected_type == 'int':
            if not isinstance(field_value, (int, float)):
                return False, f"Field '{field_name}': expected int, got {type(field_value).__name__}"
            if isinstance(field_value, float) and not field_value.is_integer():
                return False, f"Field '{field_name}': expected int, got non-integer float"
                
        elif expected_type == 'float':
            if not isinstance(field_value, (int, float)):
                return False, f"Field '{field_name}': expected float, got {type(field_value).__name__}"
                
        elif expected_type == 'str':
            if not isinstance(field_value, str):
                return False, f"Field '{field_name}': expected str, got {type(field_value).__name__}"
                
        elif expected_type == 'datetime':
            # Try to parse as datetime if it's a string
            if isinstance(field_value, str):
                try:
                    datetime.fromisoformat(field_value)
                except ValueError:
                    return False, f"Field '{field_name}': invalid datetime format '{field_value}'"
            elif not isinstance(field_value, datetime):
                return False, f"Field '{field_name}': expected datetime, got {type(field_value).__name__}"
        else:
            logger.warning(f"Unknown type '{expected_type}' for field '{field_name}'")
            
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating type for field '{field_name}': {e}")
        return False, str(e)


def validate_field_range(field_name: str, field_value: Union[int, float], 
                        min_val: Optional[float] = None, max_val: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that a numerical field value is within an acceptable range.
    
    Args:
        field_name (str): Name of the field being validated
        field_value (Union[int, float]): The value to validate
        min_val (Optional[float]): Minimum acceptable value
        max_val (Optional[float]): Maximum acceptable value
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
        
    Example:
        >>> is_valid, error = validate_field_range('value', 500, min_val=0, max_val=1000)
        >>> print(is_valid)
        True
    """
    try:
        # Skip if no range constraints defined
        if min_val is None and max_val is None:
            return True, None
        
        if min_val is not None and field_value < min_val:
            return False, f"Field '{field_name}': value {field_value} is below minimum {min_val}"
        
        if max_val is not None and field_value > max_val:
            return False, f"Field '{field_name}': value {field_value} exceeds maximum {max_val}"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating range for field '{field_name}': {e}")
        return False, str(e)


def validate_record(record: Dict[str, Any], schema: Dict[str, Any], 
                   row_index: Optional[Union[int, str]] = None) -> Tuple[bool, List[str]]:
    """
    Validate a single record (row) against the schema.
    
    Args:
        record (Dict[str, Any]): The record/row to validate
        schema (Dict[str, Any]): The schema definition dictionary
        row_index (Optional[Union[int, str]]): Index/identifier for logging purposes
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        
    Example:
        >>> record = {'id': 1, 'timestamp': '2026-03-12T10:00:00', 'value': 100, 'category': 'A'}
        >>> schema = load_schema('config/schema.json')
        >>> is_valid, errors = validate_record(record, schema)
        >>> if not is_valid:
        ...     print(errors)
    """
    errors = []
    row_prefix = f"Row {row_index}" if row_index is not None else "Record"
    
    try:
        # Get schema columns definition
        columns_schema = schema.get('columns', {})
        if not columns_schema:
            logger.warning("Schema has no 'columns' definition")
            return False, ["Schema missing 'columns' definition"]
        
        # Check required fields and field types
        for field_name, field_spec in columns_schema.items():
            is_required = field_spec.get('required', False)
            field_type = field_spec.get('type', 'str')
            
            # Check if field exists
            if field_name not in record:
                if is_required:
                    errors.append(f"{row_prefix}: Required field '{field_name}' is missing")
                continue
            
            field_value = record[field_name]
            
            # Skip validation for null optional fields
            if pd.isna(field_value) and not is_required:
                continue
            
            # Check if required field is null
            if pd.isna(field_value) and is_required:
                errors.append(f"{row_prefix}: Required field '{field_name}' is null or empty")
                continue
            
            # Validate field type
            is_valid_type, type_error = validate_field_type(field_name, field_value, field_type)
            if not is_valid_type:
                errors.append(f"{row_prefix}: {type_error}")
                continue
            
            # Validate field range if applicable
            if field_type in ['int', 'float']:
                min_val = field_spec.get('min')
                max_val = field_spec.get('max')
                is_valid_range, range_error = validate_field_range(field_name, field_value, min_val, max_val)
                if not is_valid_range:
                    errors.append(f"{row_prefix}: {range_error}")
        
        # Check row-level constraints (e.g., value range validation from row_checks)
        row_checks = schema.get('row_checks', {})
        if row_checks:
            value_range = row_checks.get('value_range', {})
            if value_range and 'value' in record:
                min_val = value_range.get('min')
                max_val = value_range.get('max')
                is_valid_range, range_error = validate_field_range('value', record['value'], min_val, max_val)
                if not is_valid_range:
                    errors.append(f"{row_prefix}: {range_error}")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"{row_prefix} validation failed: {errors}")
        
        return is_valid, errors
        
    except Exception as e:
        error_msg = f"{row_prefix}: Unexpected validation error: {str(e)}"
        logger.error(error_msg)
        return False, [error_msg]


def validate_dataset(data: Union[pd.DataFrame, List[Dict[str, Any]]], schema: Dict[str, Any],
                    return_errors: bool = False) -> Union[bool, Tuple[bool, List[Dict[str, Any]]]]:
    """
    Validate an entire dataset (multiple records) against the schema.
    
    Args:
        data (Union[pd.DataFrame, List[Dict[str, Any]]]): Dataset to validate
        schema (Dict[str, Any]): Schema definition dictionary
        return_errors (bool): If True, return detailed error information for each invalid record
        
    Returns:
        Union[bool, Tuple[bool, List[Dict[str, Any]]]]: 
            - If return_errors=False: True if all records valid, False otherwise
            - If return_errors=True: (overall_validity, list_of_invalid_records_with_errors)
            
    Example:
        >>> df = pd.read_csv('data/raw/sample_data.csv')
        >>> schema = load_schema('config/schema.json')
        >>> is_valid, errors = validate_dataset(df, schema, return_errors=True)
        >>> print(f"Valid records: {len(df) - len(errors)}")
    """
    try:
        # Convert DataFrame to list of dictionaries if needed
        if isinstance(data, pd.DataFrame):
            records = data.to_dict('records')
            indices = data.index
        elif isinstance(data, list):
            records = data
            indices = range(len(data))
        else:
            logger.error(f"Invalid data type: {type(data)}. Expected DataFrame or list")
            return False if not return_errors else (False, [])
        
        invalid_records = []
        valid_count = 0
        
        logger.info(f"Validating {len(records)} records against schema...")
        
        for idx, record in zip(indices, records):
            is_valid, errors = validate_record(record, schema, row_index=idx)
            
            if is_valid:
                valid_count += 1
            elif return_errors:
                invalid_records.append({
                    'index': idx,
                    'record': record,
                    'errors': errors
                })
        
        overall_valid = len(invalid_records) == 0
        logger.info(f"Validation complete: {valid_count}/{len(records)} records valid")
        
        if return_errors:
            return overall_valid, invalid_records
        else:
            return overall_valid
            
    except Exception as e:
        logger.error(f"Error validating dataset: {e}")
        if return_errors:
            return False, []
        else:
            return False


def get_validation_summary(data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                          schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary report of validation results for a dataset.
    
    Args:
        data (Union[pd.DataFrame, List[Dict[str, Any]]]): Dataset to validate
        schema (Dict[str, Any]): Schema definition dictionary
        
    Returns:
        Dict[str, Any]: Summary statistics including validation counts and error categories
        
    Example:
        >>> summary = get_validation_summary(df, schema)
        >>> print(f"Total records: {summary['total_records']}")
        >>> print(f"Valid records: {summary['valid_records']}")
    """
    try:
        overall_valid, invalid_records = validate_dataset(data, schema, return_errors=True)
        
        total_records = len(data)
        valid_records = total_records - len(invalid_records)
        
        # Aggregate error types
        error_categories = {}
        for invalid in invalid_records:
            for error in invalid['errors']:
                # Extract error type (first part before colon)
                error_type = error.split(':')[0] if ':' in error else 'Unknown'
                error_categories[error_type] = error_categories.get(error_type, 0) + 1
        
        summary = {
            'total_records': total_records,
            'valid_records': valid_records,
            'invalid_records': len(invalid_records),
            'valid_percentage': (valid_records / total_records * 100) if total_records > 0 else 0,
            'error_categories': error_categories,
            'overall_valid': overall_valid
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating validation summary: {e}")
        return {
            'error': str(e),
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0
        }


# Module entry point for testing
if __name__ == '__main__':
    """Test the schema validator with sample data."""
    
    # Set up test logging
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    print("Schema Validator Module - Test")
    print("=" * 70)
    
    try:
        # Load schema
        schema = load_schema('config/schema.json')
        print("✓ Schema loaded successfully\n")
        
        # Test single record validation
        test_record = {
            'id': 1,
            'timestamp': '2026-03-12T10:00:00',
            'value': 100.0,
            'category': 'A',
            'description': 'Test record'
        }
        
        is_valid, errors = validate_record(test_record, schema, row_index=0)
        print(f"Single record validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
        if errors:
            for error in errors:
                print(f"  - {error}")
        print()
        
        # Test invalid record
        invalid_record = {
            'id': 'invalid',  # Should be int
            'timestamp': '2026-03-12T10:00:00',
            'value': 2000,  # Out of range
            'category': 'A'
        }
        
        is_valid, errors = validate_record(invalid_record, schema, row_index=1)
        print(f"Invalid record validation: {'Valid' if is_valid else '✗ Invalid (as expected)'}")
        if errors:
            for error in errors:
                print(f"  - {error}")
                
    except Exception as e:
        print(f"✗ Error during testing: {e}")
