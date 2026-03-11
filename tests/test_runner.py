"""
Comprehensive Test Runner for Project Nova

This script orchestrates testing across all major modules:
- phase1_ingestion: Data ingestion and validation pipeline
- schema_validator: JSON schema validation utilities
- hash_utils: SHA256 hashing utilities

Usage:
    python tests/test_runner.py

Output:
    - Detailed test results for each module
    - Pass/Fail indicators
    - Summary report
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import modules to test
from phases.phase1_ingestion import ingest_and_validate, save_pipeline_context
from utils.schema_validator import load_schema, validate_dataset, validate_record, get_validation_summary
from utils.hash_utils import generate_hash, hash_dataset, get_hash_summary, verify_hash


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Main test runner class orchestrating all module tests."""
    
    def __init__(self):
        """Initialize test runner."""
        self.project_root = project_root
        self.results = {}
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        self.start_time = None
        self.end_time = None
    
    def print_header(self, title):
        """Print formatted section header."""
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80)
    
    def print_test(self, test_name, status, details=""):
        """Print test result."""
        status_str = "[PASS]" if status else "[FAIL]"
        print(f"\n{status_str} {test_name}")
        if details:
            for line in details.split('\n'):
                if line.strip():
                    print(f"      {line}")
    
    def print_summary(self):
        """Print overall test summary."""
        self.print_header("TEST SUMMARY")
        
        total = self.passed_count + self.failed_count
        pass_rate = (self.passed_count / total * 100) if total > 0 else 0
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed:      {self.passed_count} ({pass_rate:.1f}%)")
        print(f"Failed:      {self.failed_count}")
        
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            print(f"Duration:    {duration:.2f} seconds")
        
        status = "[SUCCESS]" if self.failed_count == 0 else "[FAILURE]"
        print(f"\nOverall Status: {status}")
    
    def update_result(self, module_name, test_name, passed):
        """Track test result."""
        if module_name not in self.results:
            self.results[module_name] = {}
        
        self.results[module_name][test_name] = passed
        self.test_count += 1
        
        if passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
    
    def test_schema_validator(self):
        """Test schema_validator module."""
        self.print_header("TEST 1: SCHEMA VALIDATOR MODULE")
        
        module_name = "schema_validator"
        
        try:
            # Test 1.1: Load schema
            print("\n1.1: Testing schema loading...")
            try:
                schema_path = os.path.join(self.project_root, 'config', 'schema.json')
                schema = load_schema(schema_path)
                
                details = f"Schema columns: {list(schema['columns'].keys())}\n"
                details += f"Total columns: {len(schema['columns'])}"
                
                self.print_test("Load schema from config/schema.json", True, details)
                self.update_result(module_name, "load_schema", True)
            except Exception as e:
                self.print_test("Load schema from config/schema.json", False, str(e))
                self.update_result(module_name, "load_schema", False)
                return
            
            # Test 1.2: Validate single record
            print("\n1.2: Testing single record validation...")
            try:
                valid_record = {
                    'id': 1,
                    'timestamp': '2026-03-12T10:00:00',
                    'value': 100.5,
                    'category': 'A',
                    'description': 'Test record'
                }
                
                is_valid, errors = validate_record(valid_record, schema, row_index=0)
                
                details = f"Record valid: {is_valid}\n"
                if errors:
                    details += f"Errors: {errors}"
                else:
                    details += "No validation errors"
                
                self.print_test("Validate valid record", is_valid, details)
                self.update_result(module_name, "validate_valid_record", is_valid)
            except Exception as e:
                self.print_test("Validate valid record", False, str(e))
                self.update_result(module_name, "validate_valid_record", False)
            
            # Test 1.3: Validate dataset
            print("\n1.3: Testing dataset validation...")
            try:
                clean_data_path = os.path.join(self.project_root, 'data', 'clean', 'clean_data.csv')
                if os.path.exists(clean_data_path):
                    df_clean = pd.read_csv(clean_data_path)
                    is_valid, invalid_records = validate_dataset(df_clean, schema, return_errors=True)
                    
                    details = f"Total records: {len(df_clean)}\n"
                    details += f"Valid records: {len(df_clean) - len(invalid_records)}\n"
                    details += f"Invalid records: {len(invalid_records)}"
                    
                    self.print_test("Validate dataset", is_valid, details)
                    self.update_result(module_name, "validate_dataset", is_valid)
                else:
                    self.print_test("Validate dataset", False, "Clean data file not found")
                    self.update_result(module_name, "validate_dataset", False)
            except Exception as e:
                self.print_test("Validate dataset", False, str(e))
                self.update_result(module_name, "validate_dataset", False)
            
            # Test 1.4: Get validation summary
            print("\n1.4: Testing validation summary...")
            try:
                summary = get_validation_summary(df_clean, schema)
                
                details = f"Total records: {summary['total_records']}\n"
                details += f"Valid records: {summary['valid_records']}\n"
                details += f"Valid percentage: {summary['valid_percentage']:.1f}%"
                
                test_passed = summary['overall_valid']
                self.print_test("Generate validation summary", test_passed, details)
                self.update_result(module_name, "validation_summary", test_passed)
            except Exception as e:
                self.print_test("Generate validation summary", False, str(e))
                self.update_result(module_name, "validation_summary", False)
        
        except Exception as e:
            logger.error(f"Unexpected error in schema_validator tests: {e}")
    
    def test_hash_utils(self):
        """Test hash_utils module."""
        self.print_header("TEST 2: HASH UTILITIES MODULE")
        
        module_name = "hash_utils"
        
        try:
            # Test 2.1: Generate single hash
            print("\n2.1: Testing hash generation...")
            try:
                record = {
                    'id': 1,
                    'name': 'Test',
                    'value': 100.5,
                    'category': 'A'
                }
                
                hash_val = generate_hash(record)
                
                details = f"Hash value: {hash_val[:32]}...\n"
                details += f"Hash length: {len(hash_val)} characters\n"
                details += "Algorithm: SHA256"
                
                is_valid = len(hash_val) == 64  # SHA256 produces 64 hex characters
                self.print_test("Generate hash for single record", is_valid, details)
                self.update_result(module_name, "generate_hash", is_valid)
            except Exception as e:
                self.print_test("Generate hash for single record", False, str(e))
                self.update_result(module_name, "generate_hash", False)
            
            # Test 2.2: Hash consistency
            print("\n2.2: Testing hash consistency...")
            try:
                hash1 = generate_hash(record)
                hash2 = generate_hash(record)
                hash3 = generate_hash(record)
                
                is_consistent = (hash1 == hash2 == hash3)
                
                details = f"Hash 1: {hash1[:16]}...\n"
                details += f"Hash 2: {hash2[:16]}...\n"
                details += f"Hash 3: {hash3[:16]}...\n"
                details += f"Consistent: {is_consistent}"
                
                self.print_test("Verify hash consistency", is_consistent, details)
                self.update_result(module_name, "hash_consistency", is_consistent)
            except Exception as e:
                self.print_test("Verify hash consistency", False, str(e))
                self.update_result(module_name, "hash_consistency", False)
            
            # Test 2.3: Hash dataset
            print("\n2.3: Testing dataset hashing...")
            try:
                clean_data_path = os.path.join(self.project_root, 'data', 'clean', 'clean_data.csv')
                if os.path.exists(clean_data_path):
                    df_clean = pd.read_csv(clean_data_path)
                    df_hashed = hash_dataset(df_clean)
                    
                    has_hash_column = '_hash' in df_hashed.columns
                    all_hashes_unique = df_hashed['_hash'].nunique() == len(df_hashed)
                    
                    details = f"Total records: {len(df_hashed)}\n"
                    details += f"Hash column present: {has_hash_column}\n"
                    details += f"Unique hashes: {df_hashed['_hash'].nunique()}\n"
                    details += f"Sample hash: {df_hashed['_hash'].iloc[0][:16]}..."
                    
                    is_valid = has_hash_column and all_hashes_unique
                    self.print_test("Hash dataset", is_valid, details)
                    self.update_result(module_name, "hash_dataset", is_valid)
                else:
                    self.print_test("Hash dataset", False, "Clean data file not found")
                    self.update_result(module_name, "hash_dataset", False)
            except Exception as e:
                self.print_test("Hash dataset", False, str(e))
                self.update_result(module_name, "hash_dataset", False)
            
            # Test 2.4: Hash summary
            print("\n2.4: Testing hash summary...")
            try:
                summary = get_hash_summary(df_hashed)
                
                details = f"Total records: {summary['total_records']}\n"
                details += f"Unique hashes: {summary['total_unique_hashes']}\n"
                details += f"Hash coverage: {summary['hash_coverage']}%\n"
                details += f"Duplicates: {summary['duplicate_hash_count']}"
                
                is_valid = summary['total_records'] > 0
                self.print_test("Generate hash summary", is_valid, details)
                self.update_result(module_name, "hash_summary", is_valid)
            except Exception as e:
                self.print_test("Generate hash summary", False, str(e))
                self.update_result(module_name, "hash_summary", False)
            
            # Test 2.5: Verify hash
            print("\n2.5: Testing hash verification...")
            try:
                test_record = {'id': 1, 'value': 100}
                test_hash = generate_hash(test_record)
                
                is_match, actual = verify_hash(test_record, test_hash)
                
                details = f"Hash match: {is_match}\n"
                details += f"Expected: {test_hash[:16]}...\n"
                details += f"Actual: {actual[:16]}..."
                
                self.print_test("Verify hash integrity", is_match, details)
                self.update_result(module_name, "verify_hash", is_match)
            except Exception as e:
                self.print_test("Verify hash integrity", False, str(e))
                self.update_result(module_name, "verify_hash", False)
        
        except Exception as e:
            logger.error(f"Unexpected error in hash_utils tests: {e}")
    
    def test_phase1_ingestion(self):
        """Test phase1_ingestion module."""
        self.print_header("TEST 3: PHASE 1 INGESTION PIPELINE")
        
        module_name = "phase1_ingestion"
        
        try:
            # Test 3.1: Data loading
            print("\n3.1: Testing data loading...")
            try:
                raw_dir = os.path.join(self.project_root, 'data', 'raw')
                raw_files = [f for f in os.listdir(raw_dir) if f.endswith('.csv')]
                
                details = f"Raw data directory: {raw_dir}\n"
                details += f"CSV files found: {len(raw_files)}\n"
                details += f"Files: {', '.join(raw_files[:2])}"
                
                self.print_test("Load raw data files", len(raw_files) > 0, details)
                self.update_result(module_name, "load_data", len(raw_files) > 0)
            except Exception as e:
                self.print_test("Load raw data files", False, str(e))
                self.update_result(module_name, "load_data", False)
            
            # Test 3.2: Run ingestion pipeline
            print("\n3.2: Testing ingestion pipeline...")
            try:
                raw_dir = os.path.join(self.project_root, 'data', 'raw')
                clean_dir = os.path.join(self.project_root, 'data', 'clean')
                anomalies_dir = os.path.join(self.project_root, 'data', 'anomalies')
                schema_path = os.path.join(self.project_root, 'config', 'schema.json')
                
                context = ingest_and_validate(
                    raw_dir=raw_dir,
                    clean_dir=clean_dir,
                    anomalies_dir=anomalies_dir,
                    schema_path=schema_path
                )
                
                details = f"Pipeline status: {context['status']}\n"
                details += f"Total input rows: {context['stats']['total_rows']}\n"
                details += f"Clean rows: {context['stats']['clean_rows']}\n"
                details += f"Anomalous rows: {context['stats']['anomalous_rows']}"
                
                is_valid = context['status'] == 'completed_success'
                self.print_test("Run ingestion pipeline", is_valid, details)
                self.update_result(module_name, "run_pipeline", is_valid)
            except Exception as e:
                self.print_test("Run ingestion pipeline", False, str(e))
                self.update_result(module_name, "run_pipeline", False)
                return
            
            # Test 3.3: Validate output files
            print("\n3.3: Testing output file generation...")
            try:
                clean_file = os.path.join(self.project_root, 'data', 'clean', 'clean_data.csv')
                anomalies_file = os.path.join(self.project_root, 'data', 'anomalies', 'anomalies.csv')
                
                clean_exists = os.path.exists(clean_file)
                anomalies_exists = os.path.exists(anomalies_file)
                
                details = f"Clean data file exists: {clean_exists}\n"
                details += f"Anomalies file exists: {anomalies_exists}"
                
                if clean_exists:
                    df_clean = pd.read_csv(clean_file)
                    details += f"\nClean records: {len(df_clean)}"
                
                if anomalies_exists:
                    df_anom = pd.read_csv(anomalies_file)
                    details += f"\nAnomaly records: {len(df_anom)}"
                
                is_valid = clean_exists and anomalies_exists
                self.print_test("Generate output files", is_valid, details)
                self.update_result(module_name, "output_files", is_valid)
            except Exception as e:
                self.print_test("Generate output files", False, str(e))
                self.update_result(module_name, "output_files", False)
            
            # Test 3.4: Save pipeline context
            print("\n3.4: Testing pipeline context persistence...")
            try:
                context_file = os.path.join(self.project_root, 'data', 'vault', 'phase1_context.json')
                
                context_exists = os.path.exists(context_file)
                
                details = f"Context file exists: {context_exists}\n"
                details += f"Context file path: {context_file}"
                
                if context_exists:
                    with open(context_file, 'r') as f:
                        saved_context = json.load(f)
                    details += f"\nContext status: {saved_context.get('status', 'Unknown')}\n"
                    details += f"Timestamp: {saved_context.get('timestamp', 'Unknown')}"
                
                self.print_test("Save pipeline context", context_exists, details)
                self.update_result(module_name, "save_context", context_exists)
            except Exception as e:
                self.print_test("Save pipeline context", False, str(e))
                self.update_result(module_name, "save_context", False)
        
        except Exception as e:
            logger.error(f"Unexpected error in phase1_ingestion tests: {e}")
    
    def run_all_tests(self):
        """Run all test suites."""
        self.start_time = datetime.now()
        
        self.print_header("PROJECT NOVA COMPREHENSIVE TEST SUITE")
        print(f"\nStarting tests at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test suites
        self.test_schema_validator()
        self.test_hash_utils()
        self.test_phase1_ingestion()
        
        self.end_time = datetime.now()
        
        # Print summary
        self.print_summary()
        
        # Return exit code
        return 0 if self.failed_count == 0 else 1


def main():
    """Main entry point."""
    try:
        runner = TestRunner()
        exit_code = runner.run_all_tests()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Fatal error in test runner: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
