"""
Phase 4 - Pipeline Execution Module for Project Nova

This module serves as the main orchestrator for the entire Project Nova data pipeline.
It integrates all previous phases and utilities:
- Phase 1: Data Ingestion & Validation
- Schema Validator: JSON schema validation
- Hash Utils: Record deduplication via SHA256 hashing

Pipeline Flow:
    1. Load raw data from data/raw/
    2. Validate records against schema
    3. Generate SHA256 hashes for each record
    4. Identify and remove duplicate records
    5. Save deduplicated final dataset
    6. Generate execution report

Usage:
    from phases.phase4_execution import run_pipeline
    result = run_pipeline(config={...})
    
    Or from command line:
    python -m phases.phase4_execution

Author: Project Nova
Version: 1.0
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import pipeline modules
from phases.phase1_ingestion import ingest_and_validate, save_pipeline_context
from utils.schema_validator import (
    load_schema, validate_dataset, get_validation_summary
)
from utils.hash_utils import (
    generate_hash, hash_dataset, get_hash_summary, verify_hash
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class PipelineConfig:
    """Configuration container for phase4 pipeline execution."""
    
    def __init__(self, project_root: str = project_root, **kwargs):
        """
        Initialize pipeline configuration.
        
        Args:
            project_root (str): Project root directory
            **kwargs: Additional configuration parameters
        """
        self.project_root = project_root
        self.raw_dir = os.path.join(project_root, 'data', 'raw')
        self.clean_dir = os.path.join(project_root, 'data', 'clean')
        self.anomalies_dir = os.path.join(project_root, 'data', 'anomalies')
        self.output_dir = os.path.join(project_root, 'data', 'processed')
        self.schema_path = os.path.join(project_root, 'config', 'schema.json')
        self.vault_dir = os.path.join(project_root, 'data', 'vault')
        
        # Additional config
        self.remove_duplicates = kwargs.get('remove_duplicates', True)
        self.save_hashes = kwargs.get('save_hashes', True)
        self.verbose = kwargs.get('verbose', True)
    
    def validate_paths(self) -> bool:
        """
        Validate that required directories exist.
        
        Returns:
            bool: True if all required paths exist, False otherwise
        """
        required_paths = [self.raw_dir, self.schema_path]
        
        for path in required_paths:
            if not os.path.exists(path):
                logger.error(f"Required path not found: {path}")
                return False
        
        # Create output directories if they don't exist
        for directory in [self.output_dir, self.vault_dir]:
            os.makedirs(directory, exist_ok=True)
        
        return True


class PipelineExecutor:
    """Main pipeline executor orchestrating all phases."""
    
    def __init__(self, config: PipelineConfig):
        """
        Initialize pipeline executor.
        
        Args:
            config (PipelineConfig): Pipeline configuration
        """
        self.config = config
        self.execution_log = {
            'start_time': None,
            'end_time': None,
            'phases': {},
            'statistics': {},
            'errors': []
        }
    
    def log_phase(self, phase_name: str, data: Dict[str, Any]) -> None:
        """
        Log phase execution data.
        
        Args:
            phase_name (str): Name of the phase
            data (Dict): Phase data to log
        """
        self.execution_log['phases'][phase_name] = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
    
    def log_error(self, error_msg: str) -> None:
        """
        Log an error message.
        
        Args:
            error_msg (str): Error message to log
        """
        self.execution_log['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'message': error_msg
        })
        logger.error(error_msg)
    
    def phase1_load_and_validate(self) -> Tuple[pd.DataFrame, Dict[str, Any], bool]:
        """
        Phase 1: Load raw data and validate using schema.
        
        Returns:
            Tuple containing:
                - DataFrame with validated data
                - Validation report
                - Success status (bool)
        """
        logger.info("="*70)
        logger.info("PHASE 1: DATA LOADING AND SCHEMA VALIDATION")
        logger.info("="*70)
        
        try:
            # Run Phase 1 ingestion
            logger.info("Running Phase 1 ingestion pipeline...")
            context = ingest_and_validate(
                raw_dir=self.config.raw_dir,
                clean_dir=self.config.clean_dir,
                anomalies_dir=self.config.anomalies_dir,
                schema_path=self.config.schema_path
            )
            
            # Load clean data
            clean_file = os.path.join(self.config.clean_dir, 'clean_data.csv')
            df = pd.read_csv(clean_file)
            
            # Validate dataset
            logger.info("Validating dataset against schema...")
            schema = load_schema(self.config.schema_path)
            summary = get_validation_summary(df, schema)
            
            phase_data = {
                'phase1_status': context['status'],
                'total_input_rows': context['stats']['total_rows'],
                'clean_rows': context['stats']['clean_rows'],
                'anomalous_rows': context['stats']['anomalous_rows'],
                'validation_summary': summary
            }
            
            self.log_phase('phase1_load_and_validate', phase_data)
            
            logger.info(f"Phase 1 Complete: {len(df)} records loaded and validated")
            logger.info(f"  Valid records: {summary['valid_records']}/{summary['total_records']}")
            
            return df, phase_data, True
            
        except Exception as e:
            error_msg = f"Phase 1 Error: {str(e)}"
            self.log_error(error_msg)
            return pd.DataFrame(), {}, False
    
    def phase2_hash_generation(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any], bool]:
        """
        Phase 2: Generate SHA256 hashes for record deduplication.
        
        Args:
            df (pd.DataFrame): Input DataFrame
            
        Returns:
            Tuple containing:
                - DataFrame with hash column added
                - Hash statistics
                - Success status (bool)
        """
        logger.info("\n" + "="*70)
        logger.info("PHASE 2: HASH GENERATION FOR DEDUPLICATION")
        logger.info("="*70)
        
        try:
            logger.info(f"Generating SHA256 hashes for {len(df)} records...")
            
            # Add hashes
            df_hashed = hash_dataset(df, hash_column='_hash')
            
            # Get hash statistics
            hash_summary = get_hash_summary(df_hashed)
            
            phase_data = {
                'total_records': hash_summary['total_records'],
                'unique_hashes': hash_summary['total_unique_hashes'],
                'hash_coverage': hash_summary['hash_coverage'],
                'duplicate_hashes': hash_summary['duplicate_hash_count']
            }
            
            self.log_phase('phase2_hash_generation', phase_data)
            
            logger.info(f"Phase 2 Complete: {hash_summary['total_unique_hashes']} unique hashes")
            logger.info(f"  Hash coverage: {hash_summary['hash_coverage']:.1f}%")
            logger.info(f"  Duplicate hashes found: {hash_summary['duplicate_hash_count']}")
            
            return df_hashed, phase_data, True
            
        except Exception as e:
            error_msg = f"Phase 2 Error: {str(e)}"
            self.log_error(error_msg)
            return df, {}, False
    
    def phase3_deduplication(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any], bool]:
        """
        Phase 3: Remove duplicate records based on hash values.
        
        Args:
            df (pd.DataFrame): Input DataFrame with hashes
            
        Returns:
            Tuple containing:
                - Deduplicated DataFrame
                - Deduplication statistics
                - Success status (bool)
        """
        logger.info("\n" + "="*70)
        logger.info("PHASE 3: DUPLICATE RECORD REMOVAL")
        logger.info("="*70)
        
        try:
            if '_hash' not in df.columns:
                raise ValueError("Hash column '_hash' not found in DataFrame")
            
            initial_count = len(df)
            
            if self.config.remove_duplicates:
                logger.info(f"Removing duplicates from {initial_count} records...")
                
                # Keep first occurrence of each hash
                df_deduplicated = df.drop_duplicates(subset=['_hash'], keep='first')
                
                final_count = len(df_deduplicated)
                duplicates_removed = initial_count - final_count
                
                logger.info(f"Duplicates removed: {duplicates_removed}")
                logger.info(f"Final record count: {final_count}")
                
                phase_data = {
                    'initial_count': initial_count,
                    'final_count': final_count,
                    'duplicates_removed': duplicates_removed,
                    'deduplication_rate': duplicates_removed / initial_count * 100 if initial_count > 0 else 0
                }
            else:
                logger.info("Deduplication disabled - keeping all records")
                df_deduplicated = df
                phase_data = {
                    'initial_count': initial_count,
                    'final_count': initial_count,
                    'duplicates_removed': 0,
                    'deduplication_rate': 0.0
                }
            
            self.log_phase('phase3_deduplication', phase_data)
            
            return df_deduplicated, phase_data, True
            
        except Exception as e:
            error_msg = f"Phase 3 Error: {str(e)}"
            self.log_error(error_msg)
            return df, {}, False
    
    def phase4_save_output(self, df: pd.DataFrame) -> Tuple[Dict[str, str], Dict[str, Any], bool]:
        """
        Phase 4: Save final processed dataset.
        
        Args:
            df (pd.DataFrame): Final processed DataFrame
            
        Returns:
            Tuple containing:
                - Output file paths dictionary
                - File statistics
                - Success status (bool)
        """
        logger.info("\n" + "="*70)
        logger.info("PHASE 4: SAVING PROCESSED DATA")
        logger.info("="*70)
        
        try:
            # Create output paths
            os.makedirs(self.config.output_dir, exist_ok=True)
            
            # Save main dataset
            output_file = os.path.join(self.config.output_dir, 'final_processed_data.csv')
            df.to_csv(output_file, index=False)
            logger.info(f"Saved processed data to: {output_file}")
            
            # Save hash index if requested
            hash_file = None
            if self.config.save_hashes and '_hash' in df.columns:
                hash_file = os.path.join(self.config.output_dir, 'record_hashes.csv')
                df[['_hash']].to_csv(hash_file, index=False)
                logger.info(f"Saved hash index to: {hash_file}")
            
            # Save metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'total_records': len(df),
                'total_columns': len(df.columns),
                'columns': list(df.columns),
                'file_size_bytes': os.path.getsize(output_file)
            }
            
            metadata_file = os.path.join(self.config.output_dir, 'metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to: {metadata_file}")
            
            phase_data = {
                'main_file': output_file,
                'hash_file': hash_file,
                'metadata_file': metadata_file,
                'total_records': len(df),
                'total_columns': len(df.columns),
                'file_size_bytes': metadata['file_size_bytes']
            }
            
            self.log_phase('phase4_save_output', phase_data)
            
            output_files = {
                'main': output_file,
                'hashes': hash_file,
                'metadata': metadata_file
            }
            
            return output_files, phase_data, True
            
        except Exception as e:
            error_msg = f"Phase 4 Error: {str(e)}"
            self.log_error(error_msg)
            return {}, {}, False
    
    def save_execution_report(self) -> bool:
        """
        Save execution report and logs.
        
        Returns:
            bool: Success status
        """
        try:
            self.execution_log['end_time'] = datetime.now().isoformat()
            
            # Calculate execution time
            if self.execution_log['start_time']:
                start = datetime.fromisoformat(self.execution_log['start_time'])
                end = datetime.fromisoformat(self.execution_log['end_time'])
                duration = (end - start).total_seconds()
                self.execution_log['duration_seconds'] = duration
            
            # Save report
            report_file = os.path.join(self.config.vault_dir, 'phase4_execution_report.json')
            with open(report_file, 'w') as f:
                json.dump(self.execution_log, f, indent=2)
            
            logger.info(f"\nExecution report saved to: {report_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving execution report: {e}")
            return False
    
    def run_pipeline(self) -> Dict[str, Any]:
        """
        Run the complete pipeline from raw data to processed output.
        
        Returns:
            Dict containing pipeline execution results
        """
        logger.info("\n" + "="*80)
        logger.info(" PROJECT NOVA - PHASE 4 PIPELINE EXECUTION")
        logger.info("="*80)
        
        self.execution_log['start_time'] = datetime.now().isoformat()
        
        try:
            # Validate configuration
            if not self.config.validate_paths():
                self.log_error("Invalid pipeline configuration")
                return {'status': 'failed', 'reason': 'Invalid configuration'}
            
            # Phase 1: Load and validate
            df, phase1_data, success1 = self.phase1_load_and_validate()
            if not success1 or df.empty:
                return {'status': 'failed', 'reason': 'Phase 1 failed', 'phase1_data': phase1_data}
            
            # Phase 2: Generate hashes
            df_hashed, phase2_data, success2 = self.phase2_hash_generation(df)
            if not success2:
                return {'status': 'failed', 'reason': 'Phase 2 failed', 'phase2_data': phase2_data}
            
            # Phase 3: Deduplication
            df_dedup, phase3_data, success3 = self.phase3_deduplication(df_hashed)
            if not success3:
                return {'status': 'failed', 'reason': 'Phase 3 failed', 'phase3_data': phase3_data}
            
            # Phase 4: Save output
            output_files, phase4_data, success4 = self.phase4_save_output(df_dedup)
            if not success4:
                return {'status': 'failed', 'reason': 'Phase 4 failed', 'phase4_data': phase4_data}
            
            # Save execution report
            self.save_execution_report()
            
            # Build final result
            result = {
                'status': 'completed_success',
                'phases': {
                    'phase1': phase1_data,
                    'phase2': phase2_data,
                    'phase3': phase3_data,
                    'phase4': phase4_data
                },
                'output_files': output_files,
                'errors': self.execution_log['errors']
            }
            
            # Print summary
            self._print_summary(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Critical pipeline error: {str(e)}"
            self.log_error(error_msg)
            self.save_execution_report()
            return {'status': 'failed', 'reason': 'Critical error', 'error': str(e)}
    
    def _print_summary(self, result: Dict[str, Any]) -> None:
        """
        Print execution summary.
        
        Args:
            result (Dict): Execution result dictionary
        """
        logger.info("\n" + "="*80)
        logger.info(" EXECUTION SUMMARY")
        logger.info("="*80)
        
        if result['status'] == 'completed_success':
            logger.info("\n✓ Pipeline Execution Successful!\n")
            
            phases = result['phases']
            
            logger.info("Phase 1 - Data Loading & Validation:")
            logger.info(f"  Input records: {phases['phase1']['total_input_rows']}")
            logger.info(f"  Valid records: {phases['phase1']['clean_rows']}")
            
            logger.info("\nPhase 2 - Hash Generation:")
            logger.info(f"  Unique hashes: {phases['phase2']['unique_hashes']}")
            logger.info(f"  Hash coverage: {phases['phase2']['hash_coverage']:.1f}%")
            
            logger.info("\nPhase 3 - Deduplication:")
            logger.info(f"  Initial records: {phases['phase3']['initial_count']}")
            logger.info(f"  Final records: {phases['phase3']['final_count']}")
            logger.info(f"  Duplicates removed: {phases['phase3']['duplicates_removed']}")
            logger.info(f"  Dedup rate: {phases['phase3']['deduplication_rate']:.1f}%")
            
            logger.info("\nPhase 4 - Output Saved:")
            logger.info(f"  Main file: {result['output_files']['main']}")
            if result['output_files']['hashes']:
                logger.info(f"  Hash file: {result['output_files']['hashes']}")
            logger.info(f"  Metadata: {result['output_files']['metadata']}")
            
        else:
            logger.error(f"\n✗ Pipeline Execution Failed!")
            logger.error(f"  Reason: {result['reason']}")


def run_pipeline(config: Optional[PipelineConfig] = None) -> Dict[str, Any]:
    """
    Main pipeline execution function.
    
    Args:
        config (Optional[PipelineConfig]): Pipeline configuration
        
    Returns:
        Dict containing execution results
        
    Example:
        >>> from phases.phase4_execution import run_pipeline
        >>> result = run_pipeline()
        >>> print(result['status'])
        'completed_success'
    """
    if config is None:
        config = PipelineConfig()
    
    executor = PipelineExecutor(config)
    return executor.run_pipeline()


def main():
    """Main entry point for command line execution."""
    logger.info("Starting Project Nova Phase 4 Pipeline Execution")
    
    config = PipelineConfig(verbose=True, remove_duplicates=True, save_hashes=True)
    result = run_pipeline(config)
    
    # Exit with appropriate code
    if result['status'] == 'completed_success':
        logger.info("\nPipeline execution completed successfully!")
        sys.exit(0)
    else:
        logger.error("\nPipeline execution failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
