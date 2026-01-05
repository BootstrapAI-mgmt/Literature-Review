"""
Console Reporter
Outputs validation results to terminal.
"""

from typing import TextIO
import sys
from ..core.validator import ValidationReport, ValidationStatus


class ConsoleReporter:
    """Formats validation results for terminal output"""
    
    def __init__(self, output: TextIO = None, verbose: bool = False):
        self.output = output or sys.stdout
        self.verbose = verbose
    
    def report(self, validation_report: ValidationReport):
        """Output the validation report to console"""
        self._print_header(validation_report)
        self._print_summary(validation_report)
        self._print_results(validation_report)
        self._print_footer(validation_report)
    
    def _print_header(self, report: ValidationReport):
        self._write("=" * 60)
        self._write(f"VALIDATION REPORT - Tier {report.tier}")
        self._write(f"Validator: {report.validator_name}")
        self._write(f"Timestamp: {report.timestamp}")
        self._write("=" * 60)
        self._write("")
    
    def _print_summary(self, report: ValidationReport):
        status = "PASS" if report.all_passed else "FAIL"
        self._write(f"Summary: {report.passed_count}/{report.total_tests} passed ({report.pass_rate:.1f}%)")
        self._write(f"Status: [{status}]")
        self._write("")
    
    def _print_results(self, report: ValidationReport):
        for result in report.results:
            icon = self._status_icon(result.status)
            self._write(f"  {icon} {result.test_id}: {result.test_name}")
            
            if self.verbose or not result.passed:
                self._write(f"      Expected: {result.expected}")
                self._write(f"      Actual: {result.actual}")
                if result.message:
                    self._write(f"      Message: {result.message}")
                if result.fix_suggestion:
                    self._write(f"      Fix: {result.fix_suggestion}")
            self._write("")
    
    def _print_footer(self, report: ValidationReport):
        self._write("-" * 60)
        if report.all_passed:
            self._write("[PASS] All tests passed!")
        else:
            self._write(f"[FAIL] {report.failed_count} test(s) failed")
        self._write("=" * 60)
    
    def _status_icon(self, status: ValidationStatus) -> str:
        icons = {
            ValidationStatus.PASS: "[PASS]",
            ValidationStatus.FAIL: "[FAIL]",
            ValidationStatus.SKIP: "[SKIP]",
            ValidationStatus.ERROR: "[ERR!]",
        }
        return icons.get(status, "[????]")
    
    def _write(self, text: str):
        print(text, file=self.output)
