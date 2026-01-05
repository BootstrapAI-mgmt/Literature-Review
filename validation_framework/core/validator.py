"""
Core Validator Classes
Provides base classes for all validation operations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from pathlib import Path
import json
from datetime import datetime


class ValidationStatus(Enum):
    """Status of a validation check"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class ValidationResult:
    """Result of a single validation test"""
    test_id: str
    test_name: str
    status: ValidationStatus
    expected: Any
    actual: Any
    message: str = ""
    fix_suggestion: str = ""
    
    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASS
    
    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "status": self.status.value,
            "expected": str(self.expected),
            "actual": str(self.actual),
            "message": self.message,
            "fix_suggestion": self.fix_suggestion,
            "passed": self.passed,
        }


@dataclass
class ValidationReport:
    """Complete validation report containing multiple results"""
    tier: int
    validator_name: str
    results: List[ValidationResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def total_tests(self) -> int:
        return len(self.results)
    
    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_count / self.total_tests) * 100
    
    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)
    
    def add_result(self, result: ValidationResult):
        self.results.append(result)
    
    def to_dict(self) -> Dict:
        return {
            "tier": self.tier,
            "validator": self.validator_name,
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total_tests,
                "passed": self.passed_count,
                "failed": self.failed_count,
                "pass_rate": f"{self.pass_rate:.1f}%",
                "all_passed": self.all_passed,
            },
            "results": [r.to_dict() for r in self.results],
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class BaseValidator:
    """
    Base class for all validators.
    Subclasses implement specific validation logic.
    """
    
    tier: int = 0
    name: str = "BaseValidator"
    
    def __init__(self, repo_path: Path, gold_standard_path: Optional[Path] = None):
        self.repo_path = Path(repo_path)
        self.gold_standard_path = gold_standard_path
        self.gold_standard: Dict = {}
        self.report = ValidationReport(tier=self.tier, validator_name=self.name)
    
    def load_gold_standard(self) -> Dict:
        """Load the gold standard YAML file"""
        if self.gold_standard_path and self.gold_standard_path.exists():
            from .gold_standard_loader import GoldStandardLoader
            loader = GoldStandardLoader(self.gold_standard_path)
            self.gold_standard = loader.load()
        return self.gold_standard
    
    def validate(self) -> ValidationReport:
        """
        Run all validation checks.
        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement validate()")
    
    def add_pass(self, test_id: str, test_name: str, expected: Any, actual: Any, message: str = ""):
        """Add a passing result"""
        self.report.add_result(ValidationResult(
            test_id=test_id,
            test_name=test_name,
            status=ValidationStatus.PASS,
            expected=expected,
            actual=actual,
            message=message,
        ))
    
    def add_fail(self, test_id: str, test_name: str, expected: Any, actual: Any, 
                 message: str = "", fix_suggestion: str = ""):
        """Add a failing result"""
        self.report.add_result(ValidationResult(
            test_id=test_id,
            test_name=test_name,
            status=ValidationStatus.FAIL,
            expected=expected,
            actual=actual,
            message=message,
            fix_suggestion=fix_suggestion,
        ))
    
    def add_skip(self, test_id: str, test_name: str, reason: str):
        """Add a skipped result"""
        self.report.add_result(ValidationResult(
            test_id=test_id,
            test_name=test_name,
            status=ValidationStatus.SKIP,
            expected="N/A",
            actual="N/A",
            message=reason,
        ))
    
    def add_error(self, test_id: str, test_name: str, error: Exception):
        """Add an error result"""
        self.report.add_result(ValidationResult(
            test_id=test_id,
            test_name=test_name,
            status=ValidationStatus.ERROR,
            expected="No error",
            actual=str(error),
            message=f"Exception: {type(error).__name__}",
        ))
