"""
Utility script to generate sample test data for Phase 1 validation testing.

This script creates sample CSV files in data/raw/ with various data quality issues
to test the Phase 1 ingestion and validation pipeline.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

def generate_sample_data():
    """Generate sample data with various quality issues for testing."""
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(project_root, 'data', 'raw')
    os.makedirs(raw_dir, exist_ok=True)
    
    # Generate base data
    np.random.seed(42)
    n_records = 100
    
    # Create good records
    good_records = {
        'id': np.arange(1, 76),  # 75 good records
        'timestamp': [
            datetime.now() - timedelta(hours=i % 48) for i in range(75)
        ],
        'value': np.random.uniform(10, 500, 75),
        'category': np.random.choice(['A', 'B', 'C', 'D'], 75)
    }
    good_records['description'] = [f'Record {i}' for i in range(75)]
    
    # Create records with issues
    bad_records = {
        'id': np.arange(1, 26),  # IDs 1-25 (duplicates!)
        'timestamp': [
            datetime.now() - timedelta(hours=i % 48) for i in range(25)
        ],
        'value': np.concatenate([
            np.random.uniform(10, 500, 15),  # Some valid
            [np.nan] * 5,  # Missing values
            [2000, 3000, -100, -500, -150]  # Out of range
        ]),
        'category': np.concatenate([
            np.random.choice(['A', 'B', 'C', 'D'], 15),
            ['X', 'Y', 'Z', 'INVALID', 'BAD', 'E', 'F', 'G', 'H', 'I']  # Some invalid categories (for visual purposes)
        ])
    }
    bad_records['description'] = [None] * 25  # All null descriptions (allowed since not required)
    
    # Combine and shuffle
    df_good = pd.DataFrame(good_records)
    df_bad = pd.DataFrame(bad_records)
    df_combined = pd.concat([df_good, df_bad], ignore_index=True)
    df_combined = df_combined.sample(frac=1, random_state=42).reset_index(drop=True)
    
    output_file = os.path.join(raw_dir, 'sample_data.csv')
    df_combined.to_csv(output_file, index=False)
    
    print(f"✓ Generated sample data: {output_file}")
    print(f"  Total records: {len(df_combined)}")
    print(f"  - Good records: {len(df_good)}")
    print(f"  - Problematic records: {len(df_bad)}")
    print(f"\nData sample:")
    print(df_combined.head(10).to_string())
    print(f"\nData info:")
    print(df_combined.info())

if __name__ == '__main__':
    generate_sample_data()
