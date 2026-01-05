"""
GitHub Reporter
Posts validation results to GitHub Issues/Comments.
"""

from ..core.validator import ValidationReport
from ..core.github_client import GitHubClient


class GitHubReporter:
    """Posts validation results to GitHub"""
    
    def __init__(self, client: GitHubClient = None):
        self.client = client or GitHubClient()
    
    def format_issue_body(self, report: ValidationReport) -> str:
        """Format validation report as GitHub issue body"""
        status = "✅ PASS" if report.all_passed else "❌ FAIL"
        
        body = f"""## Validation Report - Tier {report.tier}

**Validator:** {report.validator_name}
**Status:** {status}
**Results:** {report.passed_count}/{report.total_tests} passed ({report.pass_rate:.1f}%)
**Timestamp:** {report.timestamp}

### Results

| Status | Test ID | Test Name | Details |
|--------|---------|-----------|---------|
"""
        for result in report.results:
            icon = "✅" if result.passed else "❌"
            details = result.message or result.actual
            body += f"| {icon} | {result.test_id} | {result.test_name} | {details} |\n"
        
        if not report.all_passed:
            body += "\n### Fix Suggestions\n\n"
            for result in report.results:
                if result.fix_suggestion:
                    body += f"- **{result.test_id}**: {result.fix_suggestion}\n"
        
        return body
    
    def format_pr_comment(self, report: ValidationReport) -> str:
        """Format validation report as PR comment"""
        status = "✅ PASS" if report.all_passed else "❌ FAIL"
        
        comment = f"""### 🔍 Documentation Validation {status}

**{report.passed_count}/{report.total_tests}** tests passed

"""
        if not report.all_passed:
            comment += "**Failed tests:**\n"
            for result in report.results:
                if not result.passed:
                    comment += f"- ❌ {result.test_id}: {result.test_name}\n"
        
        return comment
