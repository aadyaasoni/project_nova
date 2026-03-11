"""
Phase 1 Test Runner - Demonstrates and validates Phase 1 ingestion pipeline.

This script:
1. Generates sample test data
2. Runs the Phase 1 ingestion and validation
3. Reports results and statistics
4. Validates output files
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_test():
    """Execute Phase 1 test pipeline."""
    
    project_root = get_project_root()
    sys.path.insert(0, project_root)
    
    print("\n" + "=" * 70)
    print("PHASE 1 - DATA INGESTION & VALIDATION TEST RUNNER")
    print("=" * 70 + "\n")
    
    # Step 1: Generate sample data
    print("Step 1: Generating sample test data...")
    print("-" * 70)
    try:
        from utils.generate_sample_data import generate_sample_data
        generate_sample_data()
        print("✓ Sample data generated successfully\n")
    except Exception as e:
        print(f"✗ Error generating sample data: {str(e)}\n")
        return False
    
    # Step 2: Run Phase 1 ingestion
    print("Step 2: Running Phase 1 ingestion and validation...")
    print("-" * 70)
    try:
        from phases.phase1_ingestion import ingest_and_validate, save_pipeline_context
        
        context = ingest_and_validate(
            raw_dir=os.path.join(project_root, 'data', 'raw'),
            clean_dir=os.path.join(project_root, 'data', 'clean'),
            anomalies_dir=os.path.join(project_root, 'data', 'anomalies'),
            schema_path=os.path.join(project_root, 'config', 'schema.json')
        )
        
        # Save context
        context_file = os.path.join(project_root, 'data', 'vault', 'phase1_context.json')
        save_pipeline_context(context, context_file)
        print()
    except Exception as e:
        print(f"✗ Error during Phase 1 ingestion: {str(e)}\n")
        return False
    
    # Step 3: Validate outputs
    print("Step 3: Validating outputs...")
    print("-" * 70)
    
    clean_file = os.path.join(project_root, 'data', 'clean', 'clean_data.csv')
    anomalies_file = os.path.join(project_root, 'data', 'anomalies', 'anomalies.csv')
    context_file = os.path.join(project_root, 'data', 'vault', 'phase1_context.json')
    
    success = True
    
    # Check clean data
    if os.path.exists(clean_file):
        df_clean = pd.read_csv(clean_file)
        print(f"✓ Clean data file exists: {len(df_clean)} records")
    else:
        print(f"✗ Clean data file not found: {clean_file}")
        success = False
    
    # Check anomalies
    if os.path.exists(anomalies_file):
        df_anomalies = pd.read_csv(anomalies_file)
        print(f"✓ Anomalies file exists: {len(df_anomalies)} records")
    else:
        print(f"✗ Anomalies file not found: {anomalies_file}")
    
    # Check context
    if os.path.exists(context_file):
        with open(context_file, 'r') as f:
            saved_context = json.load(f)
        print(f"✓ Pipeline context saved")
        success = success and saved_context['status'] == 'completed_success'
    else:
        print(f"✗ Context file not found: {context_file}")
        success = False
    
    print()
    
    # Step 4: Report summary
    print("Step 4: Test Summary")
    print("-" * 70)
    print(f"Phase Status: {context['status']}")
    print(f"Total input rows: {context['stats']['total_rows']}")
    print(f"Clean rows: {context['stats']['clean_rows']} "
          f"({context['stats']['clean_rows']/context['stats']['total_rows']*100:.1f}%)")
    print(f"Anomalous rows: {context['stats']['anomalous_rows']} "
          f"({context['stats']['anomalous_rows']/context['stats']['total_rows']*100:.1f}%)")
    if 'clean_data_hash' in context['stats']:
        print(f"Clean data hash: {context['stats']['clean_data_hash']}")
    
    print("\n" + "=" * 70)
    if success and context['status'] == 'completed_success':
        print("✓ ALL TESTS PASSED - Phase 1 pipeline is working correctly!")
    else:
        print("✗ TESTS FAILED - Please review logs for details")
    print("=" * 70 + "\n")
    
    return success and context['status'] == 'completed_success'

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
