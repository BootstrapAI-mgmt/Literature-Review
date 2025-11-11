#!/usr/bin/env python3
"""
Pipeline Orchestrator v1.0 - Basic Sequential Execution

Runs the full Literature Review pipeline automatically:
1. Journal-Reviewer → 2. Judge → 3. DRA (conditional) → 4. Sync → 5. Orchestrator

Usage:
    python pipeline_orchestrator.py
    python pipeline_orchestrator.py --log-file pipeline.log
    python pipeline_orchestrator.py --config pipeline_config.json
"""

import subprocess
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class PipelineOrchestrator:
    """Orchestrates the full literature review pipeline."""
    
    def __init__(self, log_file: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.log_file = log_file
        self.config = config or {}
        self.start_time = datetime.now()
    
    def log(self, message: str, level: str = "INFO"):
        """Log message to console and optionally to file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(log_message + '\n')
    
    def run_stage(self, script: str, description: str, required: bool = True) -> bool:
        """
        Run a pipeline stage.
        
        Args:
            script: Python script to run
            description: Human-readable stage description
            required: If True, exit on failure; if False, continue
        
        Returns:
            True if successful, False otherwise
        """
        self.log(f"Starting stage: {description}", "INFO")
        
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=self.config.get('stage_timeout', 3600)  # 1 hour default
            )
            
            if result.returncode == 0:
                self.log(f"✅ Stage complete: {description}", "SUCCESS")
                return True
            else:
                self.log(f"❌ Stage failed: {description}", "ERROR")
                self.log(f"Error output:\n{result.stderr}", "ERROR")
                
                if required:
                    self.log("Pipeline halted due to required stage failure", "ERROR")
                    sys.exit(1)
                return False
                
        except subprocess.TimeoutExpired:
            self.log(f"⏱️ Stage timeout: {description}", "ERROR")
            if required:
                sys.exit(1)
            return False
        except Exception as e:
            self.log(f"💥 Stage exception: {description} - {e}", "ERROR")
            if required:
                sys.exit(1)
            return False
    
    def check_for_rejections(self) -> bool:
        """Check if version history has rejected claims."""
        version_history_path = self.config.get(
            'version_history_path',
            'review_version_history.json'
        )
        
        try:
            with open(version_history_path, 'r') as f:
                history = json.load(f)
            
            for filename, versions in history.items():
                if not versions:
                    continue
                latest = versions[-1].get('review', {})
                for claim in latest.get('Requirement(s)', []):
                    if claim.get('status') == 'rejected':
                        self.log(f"Found rejection in {filename}", "INFO")
                        return True
            
            return False
            
        except FileNotFoundError:
            self.log(f"Version history not found: {version_history_path}", "WARNING")
            return False
        except Exception as e:
            self.log(f"Error checking rejections: {e}", "WARNING")
            return False
    
    def run(self):
        """Execute the full pipeline."""
        self.log("="*70, "INFO")
        self.log("Literature Review Pipeline Orchestrator v1.0", "INFO")
        self.log("="*70, "INFO")
        
        # Stage 1: Journal Reviewer
        self.run_stage('Journal-Reviewer.py', 'Stage 1: Initial Paper Review')
        
        # Stage 2: Judge
        self.run_stage('Judge.py', 'Stage 2: Judge Claims')
        
        # Stage 3: DRA (conditional)
        if self.check_for_rejections():
            self.log("Rejections detected, running DRA appeal process", "INFO")
            self.run_stage('DeepRequirementsAnalyzer.py', 'Stage 3: DRA Appeal')
            self.run_stage('Judge.py', 'Stage 3b: Re-judge DRA Claims')
        else:
            self.log("No rejections found, skipping DRA", "INFO")
        
        # Stage 4: Sync to Database
        self.run_stage('sync_history_to_db.py', 'Stage 4: Sync to Database')
        
        # Stage 5: Orchestrator
        self.run_stage('Orchestrator.py', 'Stage 5: Gap Analysis & Convergence')
        
        # Summary
        elapsed = datetime.now() - self.start_time
        self.log("="*70, "INFO")
        self.log(f"🎉 Pipeline Complete!", "SUCCESS")
        self.log(f"Total time: {elapsed}", "INFO")
        self.log("="*70, "INFO")


def main():
    parser = argparse.ArgumentParser(
        description='Run the full Literature Review pipeline automatically'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Path to log file (default: no file logging)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration JSON file'
    )
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)
    
    # Run pipeline
    orchestrator = PipelineOrchestrator(
        log_file=args.log_file,
        config=config
    )
    orchestrator.run()


if __name__ == '__main__':
    main()
