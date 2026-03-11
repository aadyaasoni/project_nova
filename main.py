"""
PROJECT NOVA - MAIN ENTRY POINT

Main execution script for the Project Nova data processing pipeline.
Orchestrates all phases: data ingestion, validation, hashing, and deduplication.

Usage:
    python main.py
"""

import sys
import logging
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from phases.phase4_execution import run_pipeline, PipelineConfig


def configure_logging() -> logging.Logger:
    """Configure logging for main execution."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point for Project Nova pipeline execution.
    
    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    logger = configure_logging()
    
    try:
        logger.info("=" * 80)
        logger.info("PROJECT NOVA - MAIN PIPELINE EXECUTION")
        logger.info("=" * 80)
        
        # Initialize pipeline configuration with project root
        config = PipelineConfig(project_root=str(PROJECT_ROOT))
        
        logger.info(f"Configuration:")
        logger.info(f"  Project root: {config.project_root}")
        logger.info(f"  Raw data directory: {config.raw_dir}")
        logger.info(f"  Schema path: {config.schema_path}")
        logger.info(f"  Output directory: {config.output_dir}")
        logger.info("")
        
        # Run the pipeline
        logger.info("Starting pipeline execution...")
        result = run_pipeline(config)
        
        # Report results
        logger.info("")
        logger.info("=" * 80)
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info("=" * 80)
        
        if result['status'] == 'completed_success':
            logger.info("✓ Pipeline executed successfully!")
            logger.info("")
            logger.info("Output Summary:")
            
            phases = result.get('phases', {})
            if 'phase1_data' in phases:
                phase1 = phases['phase1_data']
                logger.info(f"  Phase 1 - Records loaded: {phase1.get('total_records', 0)}")
                logger.info(f"  Phase 1 - Valid records: {phase1.get('valid_records', 0)}")
            
            if 'phase2_data' in phases:
                phase2 = phases['phase2_data']
                logger.info(f"  Phase 2 - Hashes generated: {phase2.get('hash_count', 0)}")
            
            if 'phase3_data' in phases:
                phase3 = phases['phase3_data']
                logger.info(f"  Phase 3 - Final records: {phase3.get('final_count', 0)}")
            
            output_files = result.get('output_files', {})
            if output_files:
                logger.info("")
                logger.info("Output Files:")
                for filename, filepath in output_files.items():
                    logger.info(f"  - {filepath}")
            
            logger.info("")
            logger.info("=" * 80)
            return 0
        else:
            logger.error(f"✗ Pipeline execution failed with status: {result['status']}")
            if 'errors' in result:
                logger.error("Errors encountered:")
                for phase, errors in result['errors'].items():
                    for error in errors:
                        logger.error(f"  [{phase}] {error}")
            return 1
            
    except Exception as e:
        logger.exception(f"Unexpected error during pipeline execution: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
