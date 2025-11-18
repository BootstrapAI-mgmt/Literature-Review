"""Unit tests for field-specific half-life presets."""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.decay_presets import (
    get_preset,
    suggest_field_from_papers,
    list_all_presets,
    FIELD_PRESETS
)
from literature_review.utils.evidence_decay import EvidenceDecayTracker


class TestGetPreset:
    """Tests for get_preset function."""
    
    def test_get_preset_ai_ml(self):
        """Test retrieval of AI/ML preset."""
        preset = get_preset('ai_ml')
        
        assert preset['name'] == 'AI & Machine Learning'
        assert preset['half_life_years'] == 3.0
        assert 'description' in preset
        assert 'examples' in preset
        assert len(preset['examples']) > 0
    
    def test_get_preset_mathematics(self):
        """Test retrieval of mathematics preset."""
        preset = get_preset('mathematics')
        
        assert preset['name'] == 'Mathematics'
        assert preset['half_life_years'] == 10.0
        assert 'theorem' in preset['description'].lower()
    
    def test_get_preset_software_engineering(self):
        """Test retrieval of software engineering preset."""
        preset = get_preset('software_engineering')
        
        assert preset['name'] == 'Software Engineering'
        assert preset['half_life_years'] == 5.0
    
    def test_get_preset_nonexistent_field(self):
        """Test custom preset fallback for nonexistent field."""
        preset = get_preset('nonexistent_field')
        
        assert preset['name'] == 'Custom'
        assert preset['half_life_years'] == 5.0
    
    def test_all_presets_have_required_fields(self):
        """Test that all presets have required fields."""
        required_fields = ['name', 'half_life_years', 'description', 'examples', 'recommended_for']
        
        for field_key, preset in FIELD_PRESETS.items():
            for field in required_fields:
                assert field in preset, f"Field '{field}' missing from preset '{field_key}'"
            
            # Validate data types
            assert isinstance(preset['name'], str)
            assert isinstance(preset['half_life_years'], (int, float))
            assert preset['half_life_years'] > 0
            assert isinstance(preset['description'], str)
            assert isinstance(preset['examples'], list)
            assert isinstance(preset['recommended_for'], list)


class TestSuggestFieldFromPapers:
    """Tests for suggest_field_from_papers function."""
    
    def test_suggest_ai_ml_field(self):
        """Test auto-detection of AI/ML field."""
        papers = [
            {'title': 'Deep Learning for Image Recognition', 'abstract': 'Neural networks...'},
            {'title': 'Attention Mechanisms in NLP', 'abstract': 'Machine learning techniques...'},
            {'title': 'Reinforcement Learning Algorithms', 'abstract': 'AI agent training...'}
        ]
        
        suggested = suggest_field_from_papers(papers)
        
        assert suggested == 'ai_ml'
    
    def test_suggest_mathematics_field(self):
        """Test detection of mathematics field."""
        papers = [
            {'title': 'Proof of the Riemann Hypothesis', 'abstract': 'Mathematical theorem...'},
            {'title': 'Number Theory Applications', 'abstract': 'Proof techniques in mathematics...'}
        ]
        
        suggested = suggest_field_from_papers(papers)
        
        assert suggested == 'mathematics'
    
    def test_suggest_biology_field(self):
        """Test detection of biology field."""
        papers = [
            {'title': 'Genetic Markers in Disease', 'abstract': 'Molecular biology research...'},
            {'title': 'Cell Biology Studies', 'abstract': 'Biological processes...'}
        ]
        
        suggested = suggest_field_from_papers(papers)
        
        assert suggested == 'biology'
    
    def test_suggest_physics_field(self):
        """Test detection of physics field."""
        papers = [
            {'title': 'Quantum Mechanics Principles', 'abstract': 'Physical theories...'},
            {'title': 'Particle Physics Experiments', 'abstract': 'Quantum phenomena...'}
        ]
        
        suggested = suggest_field_from_papers(papers)
        
        assert suggested == 'physics'
    
    def test_suggest_with_empty_papers(self):
        """Test suggestion with empty paper list."""
        suggested = suggest_field_from_papers([])
        
        assert suggested == 'custom'
    
    def test_suggest_with_no_matching_keywords(self):
        """Test suggestion when no keywords match."""
        papers = [
            {'title': 'Random Paper Title', 'abstract': 'Random content...'}
        ]
        
        suggested = suggest_field_from_papers(papers)
        
        assert suggested == 'custom'
    
    def test_suggest_with_missing_fields(self):
        """Test suggestion with papers missing title/abstract."""
        papers = [
            {'title': 'Deep learning neural networks'},  # No abstract
            {'abstract': 'Machine learning and artificial intelligence'},  # No title
            {}  # Empty paper
        ]
        
        suggested = suggest_field_from_papers(papers)
        
        assert suggested == 'ai_ml'
    
    def test_suggest_mixed_fields_picks_dominant(self):
        """Test that dominant field is selected when papers span multiple fields."""
        papers = [
            {'title': 'Machine Learning', 'abstract': 'Neural networks'},
            {'title': 'Deep Learning', 'abstract': 'AI systems'},
            {'title': 'Artificial Intelligence', 'abstract': 'Machine learning'},
            {'title': 'Mathematical Proof', 'abstract': 'Theorem'}  # One math paper
        ]
        
        suggested = suggest_field_from_papers(papers)
        
        # Should suggest AI/ML since it dominates
        assert suggested == 'ai_ml'


class TestListAllPresets:
    """Tests for list_all_presets function."""
    
    def test_list_all_presets(self):
        """Test that all presets are returned."""
        presets = list_all_presets()
        
        assert isinstance(presets, dict)
        assert len(presets) >= 9  # At least 8 fields + custom
        assert 'ai_ml' in presets
        assert 'mathematics' in presets
        assert 'custom' in presets
    
    def test_list_all_presets_returns_copy(self):
        """Test that modifying returned dict doesn't affect original."""
        presets = list_all_presets()
        presets['test_field'] = {'name': 'Test'}
        
        # Original should not be modified
        assert 'test_field' not in FIELD_PRESETS


class TestEvidenceDecayTrackerWithPresets:
    """Tests for EvidenceDecayTracker integration with presets."""
    
    def test_config_with_preset(self):
        """Test configuration using preset."""
        config = {
            'evidence_decay': {
                'research_field': 'ai_ml',
                'half_life_years': None  # Use preset
            }
        }
        
        tracker = EvidenceDecayTracker(config=config)
        
        assert tracker.half_life == 3.0
        assert tracker.field_name == 'AI & Machine Learning'
        assert tracker.research_field == 'ai_ml'
    
    def test_config_with_custom_override(self):
        """Test custom half-life override."""
        config = {
            'evidence_decay': {
                'research_field': 'ai_ml',
                'half_life_years': 7.5  # Custom override
            }
        }
        
        tracker = EvidenceDecayTracker(config=config)
        
        assert tracker.half_life == 7.5  # Uses custom value
        assert tracker.field_name == 'Custom'
        assert tracker.research_field == 'custom'
    
    def test_config_with_mathematics_preset(self):
        """Test mathematics preset configuration."""
        config = {
            'evidence_decay': {
                'research_field': 'mathematics',
                'half_life_years': None
            }
        }
        
        tracker = EvidenceDecayTracker(config=config)
        
        assert tracker.half_life == 10.0
        assert tracker.field_name == 'Mathematics'
    
    def test_config_with_invalid_preset_defaults_to_custom(self):
        """Test that invalid preset falls back to custom."""
        config = {
            'evidence_decay': {
                'research_field': 'invalid_field',
                'half_life_years': None
            }
        }
        
        tracker = EvidenceDecayTracker(config=config)
        
        # Should use custom preset values
        assert tracker.half_life == 5.0
        assert tracker.field_name == 'Custom'
    
    def test_config_without_research_field(self):
        """Test backward compatibility without research_field."""
        config = {
            'evidence_decay': {
                'half_life_years': 6.0
            }
        }
        
        tracker = EvidenceDecayTracker(config=config)
        
        # Should use explicit half_life_years
        assert tracker.half_life == 6.0
        assert tracker.field_name == 'Custom'
    
    def test_no_config_uses_defaults(self):
        """Test that tracker works without config."""
        tracker = EvidenceDecayTracker(half_life_years=4.0)
        
        assert tracker.half_life == 4.0
        assert tracker.field_name == 'Custom'
        assert tracker.research_field == 'custom'
    
    def test_preset_affects_decay_calculation(self):
        """Test that different presets produce different decay weights."""
        # Fast decay (AI/ML)
        config_fast = {
            'evidence_decay': {
                'research_field': 'ai_ml',
                'half_life_years': None
            }
        }
        tracker_fast = EvidenceDecayTracker(config=config_fast)
        
        # Slow decay (Mathematics)
        config_slow = {
            'evidence_decay': {
                'research_field': 'mathematics',
                'half_life_years': None
            }
        }
        tracker_slow = EvidenceDecayTracker(config=config_slow)
        
        # For a 6-year-old paper
        year = tracker_fast.current_year - 6
        weight_fast = tracker_fast.calculate_decay_weight(year)
        weight_slow = tracker_slow.calculate_decay_weight(year)
        
        # Fast decay should result in lower weight
        assert weight_fast < weight_slow
        
        # Fast: 6 years = 2 half-lives (3 years each) = 0.25
        assert abs(weight_fast - 0.25) < 0.01
        
        # Slow: 6 years = 0.6 half-lives (10 years each) ≈ 0.66
        assert weight_slow > 0.6


class TestPresetHalfLifeValues:
    """Tests to verify preset half-life values are reasonable."""
    
    def test_all_half_lives_positive(self):
        """Test that all half-life values are positive."""
        for field_key, preset in FIELD_PRESETS.items():
            assert preset['half_life_years'] > 0
    
    def test_half_lives_in_reasonable_range(self):
        """Test that half-life values are in a reasonable range."""
        for field_key, preset in FIELD_PRESETS.items():
            half_life = preset['half_life_years']
            # Should be between 1 and 15 years
            assert 1 <= half_life <= 15
    
    def test_ai_ml_has_shortest_half_life(self):
        """Test that AI/ML has one of the shortest half-lives."""
        ai_ml_half_life = FIELD_PRESETS['ai_ml']['half_life_years']
        
        # Should be among the shortest (3 years or less)
        assert ai_ml_half_life <= 3.0
    
    def test_mathematics_has_longest_half_life(self):
        """Test that mathematics has one of the longest half-lives."""
        math_half_life = FIELD_PRESETS['mathematics']['half_life_years']
        
        # Should be among the longest (8+ years)
        assert math_half_life >= 8.0
