"""
HTML Reporter
Outputs validation results as HTML file.
"""

from pathlib import Path
from ..core.validator import ValidationReport, ValidationStatus


class HTMLReporter:
    """Formats validation results as HTML output"""
    
    def __init__(self, output_path: Path = None):
        self.output_path = output_path
    
    def report(self, validation_report: ValidationReport) -> str:
        """Generate HTML report and optionally write to file"""
        html = self._generate_html(validation_report)
        
        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(html)
        
        return html
    
    def _generate_html(self, report: ValidationReport) -> str:
        status_class = "pass" if report.all_passed else "fail"
        
        results_html = ""
        for result in report.results:
            icon = self._status_icon(result.status)
            row_class = "pass" if result.passed else "fail"
            results_html += f"""
            <tr class="{row_class}">
                <td>{icon}</td>
                <td>{result.test_id}</td>
                <td>{result.test_name}</td>
                <td>{result.expected}</td>
                <td>{result.actual}</td>
                <td>{result.message}</td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report - Tier {report.tier}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #00d9ff; }}
        .summary {{ background: #16213e; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }}
        .summary.pass {{ border-left: 4px solid #00ff88; }}
        .summary.fail {{ border-left: 4px solid #ff4444; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; }}
        tr.pass {{ background: rgba(0, 255, 136, 0.1); }}
        tr.fail {{ background: rgba(255, 68, 68, 0.1); }}
        .icon {{ font-size: 1.2rem; }}
    </style>
</head>
<body>
    <h1>🔍 Validation Report - Tier {report.tier}</h1>
    <div class="summary {status_class}">
        <h2>{report.validator_name}</h2>
        <p><strong>Status:</strong> {'PASS ✅' if report.all_passed else 'FAIL ❌'}</p>
        <p><strong>Results:</strong> {report.passed_count}/{report.total_tests} passed ({report.pass_rate:.1f}%)</p>
        <p><strong>Timestamp:</strong> {report.timestamp}</p>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Status</th>
                <th>Test ID</th>
                <th>Test Name</th>
                <th>Expected</th>
                <th>Actual</th>
                <th>Message</th>
            </tr>
        </thead>
        <tbody>
            {results_html}
        </tbody>
    </table>
</body>
</html>
"""
        return html
    
    def _status_icon(self, status: ValidationStatus) -> str:
        icons = {
            ValidationStatus.PASS: "✅",
            ValidationStatus.FAIL: "❌",
            ValidationStatus.SKIP: "⏭️",
            ValidationStatus.ERROR: "⚠️",
        }
        return icons.get(status, "❓")
