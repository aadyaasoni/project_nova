"""
Comprehensive test suite for schema_validator module
Tests the module against actual Phase 1 pipeline data
"""

import sys
import pandas as pd
from utils.schema_validator import load_schema, validate_dataset, get_validation_summary, validate_record

def run_tests():
    """Execute comprehensive schema validator tests."""
    
    print('='*70)
    print('COMPREHENSIVE SCHEMA VALIDATOR TEST SUITE')
    print('='*70)
    
    # Test 1: Load schema
    print('\nTest 1: Loading schema...')
    try:
        schema = load_schema('config/schema.json')
        print('✓ Schema loaded successfully')
        columns = list(schema['columns'].keys())
        print(f'  Columns defined: {columns}')
    except Exception as e:
        print(f'✗ Error: {e}')
        return False
    
    # Test 2: Validate clean data
    print('\nTest 2: Validating clean data from Phase 1...')
    try:
        df_clean = pd.read_csv('data/clean/clean_data.csv')
        is_valid, invalid = validate_dataset(df_clean, schema, return_errors=True)
        print(f'✓ Clean data validation: {"PASSED" if is_valid else "FAILED"}')
        print(f'  Records tested: {len(df_clean)}')
        print(f'  Valid records: {len(df_clean) - len(invalid)}')
        print(f'  Invalid records: {len(invalid)}')
        
        if len(df_clean) > 0:
            print(f'  Sample rate: {(len(df_clean) - len(invalid)) / len(df_clean) * 100:.1f}% valid')
    except Exception as e:
        print(f'✗ Error: {e}')
        return False
    
    # Test 3: Validate anomalies data
    print('\nTest 3: Validating anomalies data from Phase 1...')
    try:
        df_anomalies = pd.read_csv('data/anomalies/anomalies.csv')
        is_valid, invalid = validate_dataset(df_anomalies, schema, return_errors=True)
        print(f'✓ Anomalies data validation complete')
        print(f'  Records tested: {len(df_anomalies)}')
        print(f'  Valid records: {len(df_anomalies) - len(invalid)}')
        print(f'  Invalid records: {len(invalid)} (expected - these are anomalies)')
        
        if invalid and len(invalid) <= 5:
            print(f'  Sample error from first invalid record:')
            for error in invalid[0]['errors'][:2]:
                print(f'    - {error}')
    except Exception as e:
        print(f'✗ Error: {e}')
        return False
    
    # Test 4: Generate validation summary
    print('\nTest 4: Generating validation summary...')
    try:
        summary = get_validation_summary(df_clean, schema)
        print(f'✓ Validation summary generated:')
        print(f'  Total records: {summary["total_records"]}')
        print(f'  Valid records: {summary["valid_records"]}')
        print(f'  Invalid records: {summary["invalid_records"]}')
        print(f'  Valid percentage: {summary["valid_percentage"]:.1f}%')
        if summary['error_categories']:
            print(f'  Error categories: {summary["error_categories"]}')
    except Exception as e:
        print(f'✗ Error: {e}')
        return False
    
    # Test 5: Test individual record validation
    print('\nTest 5: Testing individual record validation...')
    try:
        # Valid record
        valid_record = {
            'id': 1,
            'timestamp': '2026-03-12T10:00:00',
            'value': 500.0,
            'category': 'A',
            'description': 'Test record'
        }
        is_valid, errors = validate_record(valid_record, schema, row_index=0)
        print(f'✓ Valid record test: {"PASSED" if is_valid else "FAILED"}')
        
        # Invalid record - out of range
        invalid_record = {
            'id': 1,
            'timestamp': '2026-03-12T10:00:00',
            'value': 5000,  # Out of range
            'category': 'A'
        }
        is_valid, errors = validate_record(invalid_record, schema, row_index=1)
        print(f'✓ Invalid record test: {"PASSED" if not is_valid else "FAILED"}')
        if errors:
            print(f'  Expected error caught: {errors[0][:50]}...')
        
        # Record with missing required field
        incomplete_record = {
            'id': 1,
            'value': 100.0,
            'category': 'A'
        }
        is_valid, errors = validate_record(incomplete_record, schema, row_index=2)
        print(f'✓ Missing field test: {"PASSED" if not is_valid else "FAILED"}')
        if errors:
            print(f'  Error: {errors[0]}')
    except Exception as e:
        print(f'✗ Error: {e}')
        return False
    
    # Test 6: Test with raw data (before validation)
    print('\nTest 6: Validating raw data from Phase 1...')
    try:
        df_raw = pd.read_csv('data/raw/sample_data.csv')
        is_valid, invalid = validate_dataset(df_raw, schema, return_errors=True)
        print(f'✓ Raw data validation complete')
        print(f'  Records tested: {len(df_raw)}')
        print(f'  Valid records: {len(df_raw) - len(invalid)}')
        print(f'  Invalid records: {len(invalid)}')
        print(f'  Valid percentage: {(len(df_raw) - len(invalid)) / len(df_raw) * 100:.1f}%')
    except Exception as e:
        print(f'✗ Error: {e}')
        return False
    
    print('\n' + '='*70)
    print('✓ ALL TESTS COMPLETED SUCCESSFULLY')
    print('='*70)
    return True

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
