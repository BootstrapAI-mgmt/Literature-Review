#!/usr/bin/env python3
"""
Migration script for orchestrator state files.

Migrates existing orchestrator_state.json files from v1 to v2 format.
This is a standalone script that can be run independently.

Usage:
    python migrate_state.py [state_file]

If no file is specified, defaults to 'orchestrator_state.json'
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from literature_review.utils.state_manager import StateManager


def backup_state_file(state_file: Path) -> Path:
    """
    Create a backup of the state file.
    
    Args:
        state_file: Path to state file
    
    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = state_file.with_suffix(f'.backup_{timestamp}.json')
    
    if state_file.exists():
        import shutil
        shutil.copy2(state_file, backup_file)
        print(f"📦 Backup created: {backup_file}")
    
    return backup_file


def migrate_state_file(state_file: str, create_backup: bool = True):
    """
    Migrate a state file from v1 to v2 format.
    
    Args:
        state_file: Path to state file
        create_backup: Whether to create a backup before migration
    """
    state_path = Path(state_file)
    
    if not state_path.exists():
        print(f"❌ State file not found: {state_file}")
        return False
    
    # Create backup if requested
    if create_backup:
        backup_state_file(state_path)
    
    # Load state with StateManager (triggers migration if needed)
    print(f"🔄 Loading state file: {state_file}")
    manager = StateManager(state_file)
    state = manager.load_state()
    
    if state is None:
        print(f"❌ Failed to load state file")
        return False
    
    # Check if already v2
    if state.schema_version == "2.0":
        # Re-save to ensure format is correct
        print(f"✅ State is already v2.0 format")
        print(f"   Re-saving to ensure format consistency...")
        success = manager.save_state(state)
        
        if success:
            print(f"✅ Migration complete!")
            print_state_summary(state)
            return True
        else:
            print(f"❌ Failed to save migrated state")
            return False
    
    print(f"❌ Unexpected schema version: {state.schema_version}")
    return False


def print_state_summary(state):
    """Print summary of state."""
    print(f"\n📊 State Summary:")
    print(f"   Job ID: {state.job_id}")
    print(f"   Job Type: {state.job_type.value}")
    print(f"   Total Pillars: {state.total_pillars}")
    print(f"   Overall Coverage: {state.overall_coverage:.2f}%")
    print(f"   Analysis Completed: {state.analysis_completed}")
    print(f"   Total Gaps: {state.gap_metrics.total_gaps}")
    if state.parent_job_id:
        print(f"   Parent Job: {state.parent_job_id}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate orchestrator state files from v1 to v2 format'
    )
    parser.add_argument(
        'state_file',
        nargs='?',
        default='orchestrator_state.json',
        help='Path to state file (default: orchestrator_state.json)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backup before migration'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  Orchestrator State Migration Script")
    print("  v1.0 → v2.0")
    print("=" * 60)
    print()
    
    success = migrate_state_file(args.state_file, create_backup=not args.no_backup)
    
    if success:
        print("✅ Migration successful!")
        return 0
    else:
        print("❌ Migration failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
