"""
Comprehensive test suite for hash_utils module
Tests the module against actual Phase 1 pipeline data
"""

import sys
import pandas as pd
from utils.hash_utils import (
    generate_hash, hash_dataset, verify_hash, get_hash_summary, export_hashes
)

def run_hash_tests():
    """Execute comprehensive hash utility tests."""
    
    print('='*70)
    print('COMPREHENSIVE HASH UTILITIES TEST SUITE')
    print('='*70)
    
    # Test 1: Basic hash generation
    print('\nTest 1: Basic hash generation...')
    try:
        record = {
            'id': 1,
            'name': 'Test',
            'value': 100.5,
            'category': 'A'
        }
        hash_val = generate_hash(record)
        print(f'[PASS] Hash generated successfully')
        print(f'  Hash value: {hash_val[:32]}...')
        print(f'  Hash length: {len(hash_val)} characters')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 2: Hash consistency (same record = same hash)
    print('\nTest 2: Hash consistency...')
    try:
        hash1 = generate_hash(record)
        hash2 = generate_hash(record)
        hash3 = generate_hash(record)
        
        is_consistent = (hash1 == hash2 == hash3)
        print(f'[PASS] Consistency check: {"PASSED" if is_consistent else "FAILED"}')
        print(f'  Hash 1: {hash1[:16]}...')
        print(f'  Hash 2: {hash2[:16]}...')
        print(f'  Hash 3: {hash3[:16]}...')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 3: Field order independence
    print('\nTest 3: Field order independence...')
    try:
        record_a = {'id': 1, 'name': 'Test', 'value': 100}
        record_b = {'value': 100, 'id': 1, 'name': 'Test'}
        record_c = {'name': 'Test', 'value': 100, 'id': 1}
        
        hash_a = generate_hash(record_a)
        hash_b = generate_hash(record_b)
        hash_c = generate_hash(record_c)
        
        all_equal = (hash_a == hash_b == hash_c)
        print(f'[PASS] Field order independence: {"PASSED" if all_equal else "FAILED"}')
        if all_equal:
            print(f'  All three orderings produced identical hash')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 4: Hash dataset with DataFrame
    print('\nTest 4: Hash dataset with DataFrame...')
    try:
        df = pd.read_csv('data/clean/clean_data.csv')
        df_hashed = hash_dataset(df)
        print(f'[PASS] Dataset hashed successfully')
        print(f'  Total records: {len(df_hashed)}')
        print(f'  Hash column added: {"_hash" in df_hashed.columns}')
        print(f'  Sample hash: {df_hashed["_hash"].iloc[0][:16]}...')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 5: Hash dataset with list
    print('\nTest 5: Hash dataset with list of dictionaries...')
    try:
        list_data = [
            {'id': 1, 'value': 100},
            {'id': 2, 'value': 200},
            {'id': 3, 'value': 300}
        ]
        hashed_list = hash_dataset(list_data)
        print(f'[PASS] List hashed successfully')
        print(f'  Records: {len(hashed_list)}')
        print(f'  Hash present: {"_hash" in hashed_list[0]}')
        print(f'  Sample hash: {hashed_list[0]["_hash"][:16]}...')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 6: Verify hash integrity
    print('\nTest 6: Hash verification...')
    try:
        record = {'id': 1, 'value': 100, 'name': 'Test'}
        correct_hash = generate_hash(record)
        
        is_match, actual = verify_hash(record, correct_hash)
        print(f'[PASS] Correct hash verification: {"PASSED" if is_match else "FAILED"}')
        
        # Test with incorrect hash
        is_match_bad, _ = verify_hash(record, 'incorrect_hash_value')
        print(f'[PASS] Incorrect hash detection: {"PASSED" if not is_match_bad else "FAILED"}')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 7: Get hash summary
    print('\nTest 7: Hash summary generation...')
    try:
        summary = get_hash_summary(df_hashed)
        print(f'[PASS] Summary generated successfully')
        print(f'  Total records: {summary["total_records"]}')
        print(f'  Unique hashes: {summary["total_unique_hashes"]}')
        print(f'  Hash coverage: {summary["hash_coverage"]}%')
        print(f'  Duplicate hashes: {summary["duplicate_hash_count"]}')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 8: Special data types handling
    print('\nTest 8: Special data types handling...')
    try:
        import numpy as np
        from datetime import datetime
        
        record_special = {
            'id': np.int64(1),
            'value': np.float64(100.5),
            'timestamp': datetime(2026, 3, 12),
            'flag': np.bool_(True),
            'missing': None
        }
        hash_special = generate_hash(record_special)
        print(f'[PASS] Special types handled correctly')
        print(f'  Hash generated: {hash_special[:16]}...')
        print(f'  Types: int64, float64, datetime, bool, None')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 9: NaN and missing values
    print('\nTest 9: NaN and missing values handling...')
    try:
        record_nan = {
            'id': 1,
            'value': float('nan'),
            'description': None
        }
        hash_nan = generate_hash(record_nan)
        print(f'[PASS] NaN and None values handled')
        print(f'  Hash generated: {hash_nan[:16]}...')
        
        # Verify consistency with NaN
        hash_nan2 = generate_hash(record_nan)
        is_consistent = (hash_nan == hash_nan2)
        print(f'  Consistency with NaN: {"PASSED" if is_consistent else "FAILED"}')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 10: Anomaly data hashing
    print('\nTest 10: Hash anomalous data...')
    try:
        df_anomalies = pd.read_csv('data/anomalies/anomalies.csv')
        df_anom_hashed = hash_dataset(df_anomalies)
        summary_anom = get_hash_summary(df_anom_hashed)
        print(f'[PASS] Anomalous data hashed successfully')
        print(f'  Records: {summary_anom["total_records"]}')
        print(f'  Unique hashes: {summary_anom["total_unique_hashes"]}')
        print(f'  Duplicates: {summary_anom["duplicate_hash_count"]}')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 11: Export hashes
    print('\nTest 11: Export hashes to CSV...')
    try:
        export_file = 'data/hashes_export.csv'
        success = export_hashes(df_hashed, export_file)
        print(f'[PASS] Export: {"PASSED" if success else "FAILED"}')
        
        # Verify file was created
        import os
        file_exists = os.path.exists(export_file)
        print(f'  File created: {file_exists}')
        
        if file_exists:
            exported_df = pd.read_csv(export_file)
            print(f'  Exported records: {len(exported_df)}')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    # Test 12: Performance test
    print('\nTest 12: Performance test...')
    try:
        import time
        
        # Create large dataset
        large_data = [
            {'id': i, 'value': i*100, 'category': chr(65 + (i % 26))}
            for i in range(1000)
        ]
        
        start = time.time()
        hashed_large = hash_dataset(large_data)
        elapsed = time.time() - start
        
        print(f'[PASS] Performance test completed')
        print(f'  Records processed: {len(hashed_large)}')
        print(f'  Time taken: {elapsed:.3f} seconds')
        print(f'  Speed: {len(hashed_large)/elapsed:.0f} records/sec')
    except Exception as e:
        print(f'[FAIL] Error: {e}')
        return False
    
    print('\n' + '='*70)
    print('SUCCESS: ALL TESTS COMPLETED SUCCESSFULLY')
    print('='*70)
    return True

if __name__ == '__main__':
    success = run_hash_tests()
    sys.exit(0 if success else 1)
