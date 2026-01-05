"""
Validation Framework CLI
Command-line interface for running validation tests.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from .core.validator import ValidationReport
from .validators.architecture_validator import ArchitectureValidator
from .validators.roadmap_validator import RoadmapValidator
from .validators.task_card_validator import TaskCardValidator
from .validators.cascade_validator import CascadeValidator
from .validators.staleness_validator import StalenessValidator
from .reporters.console_reporter import ConsoleReporter
from .reporters.json_reporter import JSONReporter
from .reporters.html_reporter import HTMLReporter


def get_validators(tier: str, repo_path: Path, gold_standard_dir: Path = None):
    """Get validators based on tier selection"""
    validators = []
    
    # Tier 4 validators
    tier4 = [
        ArchitectureValidator(repo_path),
        RoadmapValidator(repo_path),
        TaskCardValidator(repo_path),
        StalenessValidator(repo_path),
    ]
    
    # Tier 5 validators
    tier5 = [
        CascadeValidator(repo_path),
    ]
    
    if tier == "4":
        validators = tier4
    elif tier == "5":
        validators = tier5
    elif tier == "all":
        validators = tier4 + tier5
    else:
        # Default to tier 4
        validators = tier4
    
    return validators


def run_validation(args) -> int:
    """Run validation and return exit code"""
    repo_path = Path(args.repo_path).resolve()
    
    if not repo_path.exists():
        print(f"Error: Repository path not found: {repo_path}", file=sys.stderr)
        return 1
    
    # Get validators
    validators = get_validators(args.tier, repo_path)
    
    # Run validations
    reports: List[ValidationReport] = []
    all_passed = True
    
    for validator in validators:
        try:
            report = validator.validate()
            reports.append(report)
            
            if not report.all_passed:
                all_passed = False
                if args.fail_fast:
                    break
        except Exception as e:
            print(f"Error running {validator.name}: {e}", file=sys.stderr)
            all_passed = False
            if args.fail_fast:
                break
    
    # Output results
    if args.output == "console":
        reporter = ConsoleReporter(verbose=args.verbose)
        for report in reports:
            reporter.report(report)
    elif args.output == "json":
        output_path = Path(args.report_path) / f"tier{args.tier}_report.json" if args.report_path else None
        reporter = JSONReporter(output_path)
        result = reporter.report_multiple(reports)
        if not output_path:
            print(result)
    elif args.output == "html":
        for i, report in enumerate(reports):
            output_path = Path(args.report_path) / f"tier{args.tier}_{report.validator_name}.html" if args.report_path else None
            reporter = HTMLReporter(output_path)
            result = reporter.report(report)
            if not output_path:
                print(result)
    
    return 0 if all_passed else 1


def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description="Validation Framework - Documentation Accuracy Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m validation_framework.cli --tier 4 --output console
  python -m validation_framework.cli --tier all --output json --report-path reports/
  python -m validation_framework.cli --tier 5 --output html --verbose
        """
    )
    
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "5", "all", "regression"],
        default="4",
        help="Validation tier to run (default: 4)"
    )
    
    parser.add_argument(
        "--document",
        choices=["architecture", "roadmap", "tasks", "all"],
        default="all",
        help="Document type to validate (default: all)"
    )
    
    parser.add_argument(
        "--output",
        choices=["console", "json", "html"],
        default="console",
        help="Output format (default: console)"
    )
    
    parser.add_argument(
        "--report-path",
        type=str,
        default=None,
        help="Directory to save reports (default: stdout)"
    )
    
    parser.add_argument(
        "--repo-path",
        type=str,
        default=".",
        help="Repository path (default: current directory)"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    sys.exit(run_validation(args))


if __name__ == "__main__":
    main()
