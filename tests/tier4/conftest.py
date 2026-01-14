"""
Tier 4 Content Accuracy Test Fixtures
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validation_framework.validators.task_card_validator import TaskCardValidator
from validation_framework.validators.roadmap_validator import RoadmapValidator
from validation_framework.validators.staleness_validator import StalenessValidator
from validation_framework.validators.cascade_validator import CascadeValidator
from validation_framework.validators.architecture_validator import ArchitectureValidator


@pytest.fixture
def repo_path():
    """Path to the repository root"""
    return PROJECT_ROOT


@pytest.fixture
def gold_standards_path(repo_path):
    """Path to gold standards directory"""
    return repo_path / "gold_standards"


@pytest.fixture
def task_card_validator(repo_path):
    """TaskCardValidator instance - doesn't require gold standard file"""
    return TaskCardValidator(repo_path, None)


@pytest.fixture
def roadmap_validator(repo_path):
    """RoadmapValidator instance - doesn't require gold standard file"""
    return RoadmapValidator(repo_path, None)


@pytest.fixture
def staleness_validator(repo_path, gold_standards_path):
    """StalenessValidator instance - uses freshness_thresholds.yaml"""
    thresholds_file = gold_standards_path / "freshness_thresholds.yaml"
    return StalenessValidator(repo_path, thresholds_file if thresholds_file.exists() else None)


@pytest.fixture
def cascade_validator(repo_path):
    """CascadeValidator instance - doesn't require gold standard file"""
    return CascadeValidator(repo_path, None)


@pytest.fixture
def architecture_validator(repo_path):
    """ArchitectureValidator instance - doesn't require gold standard file"""
    return ArchitectureValidator(repo_path, None)

