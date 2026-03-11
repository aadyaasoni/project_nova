# Phase 1: Data Ingestion and Validation

## Overview

Phase 1 is responsible for ingesting raw data, validating its structure, and separating valid records from anomalous ones. This module ensures data quality before processing in downstream phases.

## Module Location

- **Main Module**: `phases/phase1_ingestion.py`
- **Schema Config**: `config/schema.json`
- **Test Data Generator**: `utils/generate_sample_data.py`

## Architecture

### Key Components

1. **Schema Validation**
   - Validates that required columns exist
   - Checks that column data types match expected schema
   - Enforces uniqueness constraints where defined

2. **Row-Level Validation**
   - Detects missing/null values in required fields
   - Validates data types for each column
   - Performs range checks on numerical fields
   - Identifies duplicate records

3. **Data Separation**
   - Splits data into clean and anomalous subsets
   - Preserves row-level error information for anomalies
   - Maintains referential integrity

4. **Logging & Audit Trail**
   - Comprehensive logging of all validation steps
   - Timestamp and hash-based reproducibility tracking
   - JSON context file with pipeline statistics

## Usage

### Quick Start

```bash
cd project_nova
python phases/phase1_ingestion.py
```

### Generate Sample Test Data

```bash
python utils/generate_sample_data.py
python phases/phase1_ingestion.py
```

### Programmatic Usage

```python
from phases.phase1_ingestion import ingest_and_validate

context = ingest_and_validate(
    raw_dir='data/raw',
    clean_dir='data/clean',
    anomalies_dir='data/anomalies',
    schema_path='config/schema.json'
)

print(f"Clean rows: {context['stats']['clean_rows']}")
print(f"Anomalous rows: {context['stats']['anomalous_rows']}")
```

## Input/Output

### Input
- **Location**: `data/raw/`
- **Format**: CSV files
- **Expected Schema**: Defined in `config/schema.json`

### Outputs

#### Clean Data
- **Location**: `data/clean/clean_data.csv`
- **Content**: Valid records that passed all validation checks
- **Columns**: Same as input schema

#### Anomalies
- **Location**: `data/anomalies/anomalies.csv`
- **Content**: Records that failed validation
- **Extra Column**: `_anomaly_reasons` - lists specific validation failures

#### Pipeline Context
- **Location**: `data/vault/phase1_context.json`
- **Content**: Statistics, status, and metadata from ingestion

#### Logs
- **Location**: `logs/phase1_YYYYMMDD_HHMMSS.log`
- **Content**: Detailed ingestion and validation event log

## Schema Configuration

The schema file (`config/schema.json`) defines:

```json
{
  "columns": {
    "column_name": {
      "type": "int|float|str|datetime",
      "required": true|false,
      "unique": true|false,
      "description": "Human-readable description"
    }
  },
  "row_checks": {
    "value_range": {
      "min": 0,
      "max": 1000
    }
  }
}
```

### Supported Data Types
- `int`: Integer values
- `float`: Floating-point numbers
- `str`: Text strings
- `datetime`: ISO format timestamps

## Validation Rules

### Schema Level
- ✓ All required columns must exist
- ✓ No required columns can be missing
- ✓ Column data types must match schema

### Row Level
- ✓ Required fields cannot be null
- ✓ Data types must be valid or convertible
- ✓ Numerical values must be within defined ranges
- ✓ Unique columns cannot have duplicate values
- ✓ Datetime fields must be in valid format

## Statistics and Monitoring

The pipeline context includes:

```json
{
  "phase": 1,
  "timestamp": "2026-03-10T10:30:00.000000",
  "status": "completed_success",
  "stats": {
    "total_rows": 100,
    "clean_rows": 75,
    "anomalous_rows": 25,
    "clean_data_hash": "abc123...",
    "raw_row_count": 100
  }
}
```

## Error Handling

The module handles:
- Missing input files
- Malformed CSV data
- Type conversion errors
- Schema mismatches
- Duplicate records
- Out-of-range values
- Null value violations

All errors are logged and aggregated in the anomalies dataset.

## Reproducibility

Phase 1 maintains reproducibility through:
- Deterministic row-by-row validation
- Data integrity hash of clean dataset
- Complete audit trail in logs
- Timestamped context metadata

## Constraints & Best Practices

- ✓ Raw data is never modified
- ✓ All operations are deterministic
- ✓ Comprehensive logging for audit trails
- ✓ Graceful error handling
- ✓ Configuration-driven schema validation
- ✓ Hash-based data integrity verification

## Next Steps

After Phase 1 completes successfully:
1. Clean data is ready for Phase 2 (transformation/enrichment)
2. Anomalies are available for Phase 3-4 (remediation/analysis)
3. Pipeline context is stored in `data/vault/` for future reference

## Troubleshooting

### No data loaded
- Check that `data/raw/` contains CSV files
- Run `python utils/generate_sample_data.py` to generate test data

### Schema validation fails
- Verify columns in raw data match `config/schema.json`
- Check for typos in column names

### All rows marked as anomalous
- Review specific row errors in logs
- Check data format matches schema expectations
- May need to adjust type conversion rules

## Dependencies

- `pandas`: Data manipulation
- `numpy`: Numerical operations
- Python 3.7+

