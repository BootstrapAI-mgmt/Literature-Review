"""
JSON Reporter
Outputs validation results as JSON file.
"""

from pathlib import Path
import json
from ..core.validator import ValidationReport


class JSONReporter:
    """Formats validation results as JSON output"""
    
    def __init__(self, output_path: Path = None):
        self.output_path = output_path
    
    def report(self, validation_report: ValidationReport) -> str:
        """Generate JSON report and optionally write to file"""
        json_str = validation_report.to_json(indent=2)
        
        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    def report_multiple(self, reports: list) -> str:
        """Generate combined JSON report from multiple validators"""
        combined = {
            "validation_run": {
                "total_reports": len(reports),
                "all_passed": all(r.all_passed for r in reports),
            },
            "reports": [r.to_dict() for r in reports],
        }
        
        json_str = json.dumps(combined, indent=2)
        
        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
