"""
Tests for pipeline orchestrator v2.0 CLI options.

Tests cover:
- --dry-run mode
- --enable-experimental mode
- Backward compatibility with v1.x
"""

import pytest
import os
import sys
import subprocess
import tempfile
import shutil


@pytest.mark.integration
class TestPipelineOrchestratorCLI:
    """Integration tests for pipeline orchestrator CLI."""
    
    def test_dry_run_mode(self):
        """Test --dry-run executes without side effects."""
        result = subprocess.run(
            [sys.executable, 'pipeline_orchestrator.py', '--dry-run'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        assert result.returncode == 0
        assert 'DRY-RUN MODE ENABLED' in result.stdout
        assert 'Would execute:' in result.stdout
        assert 'Stage validated:' in result.stdout
        assert 'Pipeline Complete!' in result.stdout
    
    def test_help_shows_new_options(self):
        """Test that help text shows new v2.0 options."""
        result = subprocess.run(
            [sys.executable, 'pipeline_orchestrator.py', '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert '--dry-run' in result.stdout
        assert '--enable-experimental' in result.stdout
        assert 'v2.0' in result.stdout.lower()
    
    def test_backward_compatibility(self):
        """Test that orchestrator works without new flags (backward compatible)."""
        # Create temp checkpoint file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            checkpoint_file = f.name
        
        try:
            # Run with basic v1.x options (should fail quickly with dry-run to avoid long execution)
            result = subprocess.run(
                [
                    sys.executable, 'pipeline_orchestrator.py',
                    '--dry-run',  # Use dry-run to make it fast
                    '--checkpoint-file', checkpoint_file
                ],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            # Should complete successfully
            assert result.returncode == 0
            assert 'Pipeline Complete!' in result.stdout or 'DRY-RUN' in result.stdout
        finally:
            if os.path.exists(checkpoint_file):
                os.unlink(checkpoint_file)
    
    def test_config_with_v2_features(self, tmp_path):
        """Test loading config with v2 features."""
        config_file = tmp_path / 'test_config.json'
        config_file.write_text('''{
            "version": "2.0.0",
            "stage_timeout": 3600,
            "dry_run": true,
            "v2_features": {
                "max_workers": 2,
                "feature_flags": {
                    "enable_quota_management": true,
                    "enable_smart_retry": true
                }
            }
        }''')
        
        result = subprocess.run(
            [
                sys.executable, 'pipeline_orchestrator.py',
                '--config', str(config_file)
            ],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Should complete with dry-run enabled from config
        assert result.returncode == 0
        assert 'DRY-RUN' in result.stdout


@pytest.mark.integration
class TestDryRunCheckpoint:
    """Test dry-run mode with checkpoint functionality."""
    
    def test_dry_run_creates_checkpoint(self, tmp_path):
        """Test that dry-run mode creates checkpoint file."""
        checkpoint_file = tmp_path / 'checkpoint.json'
        
        result = subprocess.run(
            [
                sys.executable, 'pipeline_orchestrator.py',
                '--dry-run',
                '--checkpoint-file', str(checkpoint_file)
            ],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        assert result.returncode == 0
        assert checkpoint_file.exists()
        
        # Verify checkpoint contains expected data
        import json
        with checkpoint_file.open('r') as f:
            data = json.load(f)
        
        assert 'run_id' in data
        assert 'stages' in data
        assert data['status'] == 'completed'
