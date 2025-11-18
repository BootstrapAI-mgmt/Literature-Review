"""
Adaptive ETA Calculator for Literature Review Pipeline

Calculates accurate ETAs using:
- Historical stage duration data
- Paper count scaling (time per paper)
- Confidence intervals based on data quality
- Fallback estimates for first runs
"""

from typing import Dict, Optional, Tuple
import statistics
import json
import os
from datetime import datetime, timezone
from pathlib import Path


class AdaptiveETACalculator:
    """Calculate ETA using historical data and paper count"""
    
    STAGE_ORDER = ['gap_analysis', 'deep_review', 'proof_generation', 'final_report']
    
    # Fallback estimates (used when no historical data) - seconds per paper
    FALLBACK_ESTIMATES = {
        'gap_analysis': 30,  # seconds per paper
        'deep_review': 120,  # seconds per paper
        'proof_generation': 45,
        'final_report': 15
    }
    
    def __init__(self, history_file: str = 'workspace/eta_history.json'):
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load historical stage durations"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_history(self):
        """Save historical data"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def record_stage_completion(self, stage_name: str, duration_seconds: float, paper_count: int):
        """Record completed stage for future ETA calculations"""
        if stage_name not in self.history:
            self.history[stage_name] = []
        
        # Store time per paper (normalizes for different paper counts)
        time_per_paper = duration_seconds / max(paper_count, 1)
        
        self.history[stage_name].append({
            'duration_seconds': duration_seconds,
            'paper_count': paper_count,
            'time_per_paper': time_per_paper,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only last 50 runs per stage (prevent unbounded growth)
        if len(self.history[stage_name]) > 50:
            self.history[stage_name] = self.history[stage_name][-50:]
        
        self._save_history()
    
    def calculate_eta(self, current_stage: str, paper_count: int) -> Dict:
        """
        Calculate ETA for remaining stages
        
        Args:
            current_stage: Current stage name
            paper_count: Number of papers being processed
            
        Returns:
            Dictionary with ETA information:
            {
                'total_eta_seconds': int,
                'min_eta_seconds': int,
                'max_eta_seconds': int,
                'confidence': str,  # 'high', 'medium', or 'low'
                'stage_breakdown': dict,
                'remaining_stages': list
            }
        """
        # Find remaining stages
        try:
            current_index = self.STAGE_ORDER.index(current_stage)
            remaining_stages = self.STAGE_ORDER[current_index + 1:]
        except ValueError:
            # Current stage not in order, return all stages
            remaining_stages = self.STAGE_ORDER
        
        total_eta_seconds = 0
        confidence = 'high'
        stage_etas = {}
        
        for stage in remaining_stages:
            eta, stage_confidence = self._estimate_stage_duration(stage, paper_count)
            stage_etas[stage] = eta
            total_eta_seconds += eta
            
            if stage_confidence == 'low':
                confidence = 'low'
            elif stage_confidence == 'medium' and confidence == 'high':
                confidence = 'medium'
        
        # Calculate confidence interval (±20% for low confidence)
        if confidence == 'low':
            min_eta = total_eta_seconds * 0.8
            max_eta = total_eta_seconds * 1.5
        elif confidence == 'medium':
            min_eta = total_eta_seconds * 0.9
            max_eta = total_eta_seconds * 1.2
        else:
            min_eta = total_eta_seconds * 0.95
            max_eta = total_eta_seconds * 1.05
        
        return {
            'total_eta_seconds': int(total_eta_seconds),
            'min_eta_seconds': int(min_eta),
            'max_eta_seconds': int(max_eta),
            'confidence': confidence,
            'stage_breakdown': stage_etas,
            'remaining_stages': remaining_stages
        }
    
    def _estimate_stage_duration(self, stage_name: str, paper_count: int) -> Tuple[float, str]:
        """
        Estimate duration for a stage
        
        Args:
            stage_name: Name of the stage
            paper_count: Number of papers
            
        Returns:
            Tuple of (estimated_duration, confidence_level)
        """
        historical_data = self.history.get(stage_name, [])
        
        if len(historical_data) >= 3:
            # Good historical data: use median time per paper
            times_per_paper = [d['time_per_paper'] for d in historical_data]
            median_time_per_paper = statistics.median(times_per_paper)
            estimated_duration = median_time_per_paper * paper_count
            
            # High confidence if we have 10+ data points
            confidence = 'high' if len(historical_data) >= 10 else 'medium'
            
            return estimated_duration, confidence
        
        elif len(historical_data) > 0:
            # Some data but not enough: blend with fallback
            avg_time_per_paper = statistics.mean([d['time_per_paper'] for d in historical_data])
            fallback_time_per_paper = self.FALLBACK_ESTIMATES.get(stage_name, 60)
            
            # Weighted average: 70% historical, 30% fallback
            blended_time_per_paper = (avg_time_per_paper * 0.7) + (fallback_time_per_paper * 0.3)
            estimated_duration = blended_time_per_paper * paper_count
            
            return estimated_duration, 'medium'
        
        else:
            # No historical data: use fallback
            fallback_time_per_paper = self.FALLBACK_ESTIMATES.get(stage_name, 60)
            estimated_duration = fallback_time_per_paper * paper_count
            
            return estimated_duration, 'low'
    
    def get_accuracy_report(self) -> Dict:
        """
        Generate report on ETA accuracy
        
        Returns:
            Dictionary with statistics per stage
        """
        report = {}
        
        for stage, data in self.history.items():
            if len(data) < 2:
                continue
            
            times = [d['duration_seconds'] for d in data]
            times_per_paper = [d['time_per_paper'] for d in data]
            
            report[stage] = {
                'sample_size': len(data),
                'avg_duration': statistics.mean(times),
                'median_duration': statistics.median(times),
                'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                'avg_time_per_paper': statistics.mean(times_per_paper),
                'min_duration': min(times),
                'max_duration': max(times)
            }
        
        return report
