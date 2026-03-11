"""
Project Nova - Main Pipeline Orchestrator

Entry point for the complete data processing pipeline.
Executes phases sequentially with proper error handling and logging.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

def setup_logging(log_dir=None):
    """Set up root logging configuration."""
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def run_phase1(project_root, logger):
    """Execute Phase 1: Data Ingestion and Validation."""
    logger.info("=" * 70)
    logger.info("EXECUTING: PHASE 1 - DATA INGESTION AND VALIDATION")
    logger.info("=" * 70)
    
    try:
        from phases.phase1_ingestion import ingest_and_validate, save_pipeline_context
        
        context = ingest_and_validate(
            raw_dir=os.path.join(project_root, 'data', 'raw'),
            clean_dir=os.path.join(project_root, 'data', 'clean'),
            anomalies_dir=os.path.join(project_root, 'data', 'anomalies'),
            schema_path=os.path.join(project_root, 'config', 'schema.json'),
            log_dir=os.path.join(project_root, 'logs')
        )
        
        context_file = os.path.join(project_root, 'data', 'vault', 'phase1_context.json')
        save_pipeline_context(context, context_file)
        
        return context
        
    except Exception as e:
        logger.error(f"Phase 1 failed: {str(e)}", exc_info=True)
        return {'status': 'failed', 'error': str(e)}

def main():
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(description='Project Nova Pipeline Orchestrator')
    parser.add_argument(
        '--phase',
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help='Starting phase (1-4)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run test pipeline with generated sample data'
    )
    
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    logger = setup_logging(os.path.join(project_root, 'logs'))
    
    logger.info("PROJECT NOVA - PIPELINE ORCHESTRATOR")
    logger.info(f"Project Root: {project_root}")
    logger.info(f"Starting from Phase: {args.phase}")
    if args.test:
        logger.info("Running in TEST mode (generating sample data)")
    
    # Generate test data if requested
    if args.test:
        logger.info("\nGenerating sample test data...")
        try:
            from utils.generate_sample_data import generate_sample_data
            generate_sample_data()
            logger.info("Sample data generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate sample data: {str(e)}")
            return 1
    
    # Execute Phase 1
    if args.phase <= 1:
        context = run_phase1(project_root, logger)
        if context.get('status') != 'completed_success':
            logger.error("Phase 1 did not complete successfully")
            return 1
    
    logger.info("\n" + "=" * 70)
    logger.info("PIPELINE ORCHESTRATOR COMPLETED")
    logger.info("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
