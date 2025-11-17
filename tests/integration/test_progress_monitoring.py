"""
Integration tests for Progress Monitoring System

Tests cover:
- ProgressTracker event emission
- ProgressEvent dataclass functionality
- ETACalculator estimation accuracy
- Progress percentage calculation
- Stage tracking and completion
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Import classes to test
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator import ProgressTracker, ProgressEvent, ETACalculator


class TestProgressEvent:
    """Test ProgressEvent dataclass"""
    
    def test_progress_event_creation(self):
        """Test that ProgressEvent can be created with required fields"""
        event = ProgressEvent(
            timestamp=datetime.utcnow().isoformat(),
            stage="judge",
            phase="starting",
            message="Starting Judge",
            percentage=15.0,
            metadata={"iteration": 1}
        )
        
        assert event.stage == "judge"
        assert event.phase == "starting"
        assert event.message == "Starting Judge"
        assert event.percentage == 15.0
        assert event.metadata["iteration"] == 1
    
    def test_progress_event_minimal(self):
        """Test ProgressEvent with minimal required fields"""
        event = ProgressEvent(
            timestamp=datetime.utcnow().isoformat(),
            stage="initialization",
            phase="complete",
            message="Initialized"
        )
        
        assert event.stage == "initialization"
        assert event.phase == "complete"
        assert event.percentage is None
        assert event.metadata is None


class TestProgressTracker:
    """Test ProgressTracker functionality"""
    
    def test_progress_tracker_initialization(self):
        """Test that ProgressTracker initializes correctly"""
        tracker = ProgressTracker()
        
        assert tracker.current_stage is None
        assert tracker.stages_completed == []
        assert len(tracker.stage_weights) == 6
        assert tracker.eta_calculator is not None
    
    def test_progress_tracker_emits_events(self):
        """Test that ProgressTracker emits events correctly"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        tracker.emit("judge", "starting", "Starting Judge")
        tracker.emit("judge", "complete", "Judge complete")
        
        assert len(events) == 2
        assert events[0].stage == "judge"
        assert events[0].phase == "starting"
        assert events[1].phase == "complete"
    
    def test_progress_percentage_calculation(self):
        """Test that progress percentage is calculated correctly"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        # Test initialization complete (5% weight)
        tracker.emit("initialization", "starting", "Starting...")
        tracker.emit("initialization", "complete", "Complete")
        
        # Check that initialization complete gives 5% progress
        assert events[-1].percentage == 5.0
        
        # Test judge complete (5% + 15% = 20%)
        tracker.emit("judge", "starting", "Starting Judge")
        tracker.emit("judge", "complete", "Judge complete")
        
        # Check that judge complete gives 20% progress
        assert events[-1].percentage == 20.0
    
    def test_progress_percentage_running_stage(self):
        """Test progress percentage for running (in-progress) stages"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        # Complete initialization (5%)
        tracker.emit("initialization", "complete", "Complete")
        
        # Start gap_analysis (35% weight, 50% complete = 17.5%)
        tracker.emit("gap_analysis", "running", "Running analysis")
        
        # Total should be 5% (initialization) + 17.5% (half of gap_analysis)
        assert abs(events[-1].percentage - 22.5) < 0.1
    
    def test_progress_iteration_metadata(self):
        """Test that iteration metadata is included in events"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        tracker.emit(
            "gap_analysis",
            "running",
            "Iteration 2 starting",
            iteration=2,
            completeness_scores={"pillar1": 75.0}
        )
        
        assert events[-1].metadata is not None
        assert events[-1].metadata["iteration"] == 2
        assert "completeness_scores" in events[-1].metadata


class TestETACalculator:
    """Test ETACalculator functionality"""
    
    def test_eta_calculator_initialization(self):
        """Test ETACalculator initializes with empty history"""
        calculator = ETACalculator()
        assert calculator.stage_history == {}
    
    def test_eta_calculator_records_duration(self):
        """Test that ETACalculator records stage durations"""
        calculator = ETACalculator()
        
        calculator.record_stage_duration("judge", 120)
        calculator.record_stage_duration("judge", 130)
        calculator.record_stage_duration("judge", 110)
        
        assert len(calculator.stage_history["judge"]) == 3
        assert calculator.stage_history["judge"] == [120, 130, 110]
    
    def test_eta_calculator_limits_history(self):
        """Test that ETACalculator keeps only last 10 measurements"""
        calculator = ETACalculator()
        
        # Record 15 durations
        for i in range(15):
            calculator.record_stage_duration("judge", 100 + i)
        
        # Should only keep last 10
        assert len(calculator.stage_history["judge"]) == 10
        # Should have values 105-114 (last 10 of 0-14)
        assert calculator.stage_history["judge"][0] == 105
        assert calculator.stage_history["judge"][-1] == 114
    
    def test_eta_estimate_with_history(self):
        """Test ETA estimation with historical data"""
        calculator = ETACalculator()
        
        # Record some stage durations (in seconds)
        calculator.record_stage_duration("judge", 120)
        calculator.record_stage_duration("judge", 130)
        calculator.record_stage_duration("judge", 110)
        
        # Estimate ETA for a stage that started 60 seconds ago
        start_time = datetime.utcnow() - timedelta(seconds=60)
        eta = calculator.estimate_eta(
            current_stage="judge",
            stage_started_at=start_time,
            remaining_stages=["gap_analysis", "visualization"]
        )
        
        assert eta is not None
        assert isinstance(eta, timedelta)
        # ETA should be positive (remaining time)
        assert eta.total_seconds() > 0
        
        # Average judge duration is 120s, 60s elapsed, so ~60s remaining
        # Plus defaults for gap_analysis (240s) and visualization (60s)
        # Total ~360s
        assert 300 < eta.total_seconds() < 400
    
    def test_eta_estimate_without_history(self):
        """Test ETA estimation without historical data (uses defaults)"""
        calculator = ETACalculator()
        
        # No history recorded
        start_time = datetime.utcnow() - timedelta(seconds=30)
        eta = calculator.estimate_eta(
            current_stage="judge",
            stage_started_at=start_time,
            remaining_stages=["gap_analysis"]
        )
        
        assert eta is not None
        # Should use default (60s for judge + 240s for gap_analysis)
        # Minus 30s elapsed = ~270s
        assert 200 < eta.total_seconds() < 350
    
    def test_eta_estimate_elapsed_exceeds_average(self):
        """Test ETA when elapsed time exceeds average duration"""
        calculator = ETACalculator()
        
        # Record historical data showing stage usually takes 60s
        calculator.record_stage_duration("judge", 60)
        calculator.record_stage_duration("judge", 60)
        
        # But current stage has been running for 90s
        start_time = datetime.utcnow() - timedelta(seconds=90)
        eta = calculator.estimate_eta(
            current_stage="judge",
            stage_started_at=start_time,
            remaining_stages=["visualization"]
        )
        
        assert eta is not None
        # Current stage remaining should be 0 (elapsed > average)
        # Only visualization remaining (60s default)
        assert 40 < eta.total_seconds() < 80


class TestProgressTrackerWithETA:
    """Test ProgressTracker integration with ETACalculator"""
    
    def test_progress_tracker_includes_eta(self):
        """Test that ProgressTracker includes ETA in metadata"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        # Emit some events
        tracker.emit("initialization", "starting", "Starting")
        time.sleep(0.1)  # Small delay
        tracker.emit("initialization", "complete", "Complete")
        
        tracker.emit("judge", "starting", "Starting Judge")
        
        # Check that running stage has ETA
        assert events[-1].metadata is not None
        assert "eta_seconds" in events[-1].metadata
        assert events[-1].metadata["eta_seconds"] > 0
    
    def test_progress_tracker_improves_eta_with_history(self):
        """Test that ETA improves as more stages complete"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        # Complete first stage
        tracker.emit("initialization", "starting", "Starting")
        time.sleep(0.05)
        tracker.emit("initialization", "complete", "Complete")
        
        # The next stage should have ETA based on recorded duration
        tracker.emit("judge", "starting", "Starting Judge")
        
        # ETA should be present and reflect recorded initialization time
        last_event = events[-1]
        assert last_event.metadata is not None
        assert "eta_seconds" in last_event.metadata


@pytest.mark.integration
class TestProgressMonitoringIntegration:
    """Integration tests for full progress monitoring flow"""
    
    def test_full_pipeline_progress_tracking(self):
        """Test progress tracking through a simulated pipeline"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        # Simulate a full pipeline run with all stages
        stages = [
            ("initialization", "Starting pipeline"),
            ("judge", "Validating claims"),
            ("deep_review", "Deep reviewing papers"),
            ("gap_analysis", "Analyzing gaps"),
            ("visualization", "Creating visualizations"),
            ("finalization", "Finalizing output")
        ]
        
        for stage, message in stages:
            tracker.emit(stage, "starting", f"Starting {message}")
            time.sleep(0.01)  # Simulate work
            tracker.emit(stage, "complete", f"Completed {message}")
        
        # Check that we got events for all stages
        assert len(events) == 12  # 2 events per stage (starting, complete)
        
        # Check that final event shows 100% completion
        final_event = events[-1]
        assert final_event.percentage == 100.0
        assert final_event.stage == "finalization"
        assert final_event.phase == "complete"
    
    def test_error_handling_in_progress_tracking(self):
        """Test progress tracking when an error occurs"""
        events = []
        
        def callback(event):
            events.append(event)
        
        tracker = ProgressTracker(callback=callback)
        
        # Start and complete initialization
        tracker.emit("initialization", "starting", "Starting")
        tracker.emit("initialization", "complete", "Complete")
        
        # Start judge and encounter error
        tracker.emit("judge", "starting", "Starting Judge")
        tracker.emit("judge", "error", "Judge failed")
        
        # Check error event
        error_event = events[-1]
        assert error_event.phase == "error"
        assert error_event.stage == "judge"
        
        # Progress should be between 5% (init complete) and 20% (init+judge complete)
        assert 5.0 <= error_event.percentage < 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
