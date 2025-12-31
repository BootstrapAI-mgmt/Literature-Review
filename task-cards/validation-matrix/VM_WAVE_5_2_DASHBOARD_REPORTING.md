# Task Card: Dashboard & Reporting

**Task ID:** VM-W5-2  
**Wave:** 5 (Integration & Reporting)  
**Priority:** MEDIUM  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W5-1  
**Blocks:** None (Final wave)  
**Validation IDs:** N/A (Infrastructure)

---

## Objective

Create a validation matrix dashboard and automated reporting system for visualizing test results, benchmark trends, and regression alerts.

## Background

A comprehensive dashboard enables:
- Real-time visibility into validation suite health
- Historical trend analysis for benchmarks
- Quick identification of failing tests
- Automated report generation for stakeholders
- Slack/email notifications for critical failures

## Success Criteria

- [ ] Validation matrix dashboard panel
- [ ] Benchmark trend visualization (30-day window)
- [ ] Automated validation report generation
- [ ] Slack/notification integration
- [ ] Historical trend analysis
- [ ] Regression alert thresholds with notifications

---

## Deliverables

### 1. Dashboard Data Generator

**File:** `scripts/dashboard/generate_validation_data.py`

```python
#!/usr/bin/env python3
"""
Validation Dashboard Data Generator

Aggregates test results and benchmark data into dashboard-ready format.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class TestResult:
    """Single test result."""
    test_id: str
    name: str
    category: str
    status: str  # passed, failed, skipped
    duration_seconds: float
    timestamp: str
    error_message: Optional[str] = None


@dataclass
class BenchmarkDataPoint:
    """Single benchmark data point."""
    benchmark_id: str
    name: str
    value: float
    unit: str
    threshold: float
    passed: bool
    timestamp: str
    commit_sha: str


@dataclass
class ValidationSummary:
    """Summary of validation suite run."""
    timestamp: str
    commit_sha: str
    branch: str
    
    # Test counts
    total_tests: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    
    # Category breakdown
    by_category: Dict[str, Dict[str, int]]
    
    # Duration
    total_duration_seconds: float
    
    # Failed test details
    failures: List[Dict]


@dataclass
class DashboardData:
    """Complete dashboard data structure."""
    generated_at: str
    
    # Current state
    current_summary: ValidationSummary
    
    # Trends (30 days)
    daily_summaries: List[ValidationSummary]
    benchmark_trends: Dict[str, List[BenchmarkDataPoint]]
    
    # Alerts
    active_alerts: List[Dict]
    
    # Health indicators
    overall_health: str  # healthy, warning, critical
    health_score: float  # 0-100


class DashboardGenerator:
    """Generates dashboard data from test results."""
    
    def __init__(self, results_dir: Path, output_dir: Path):
        self.results_dir = results_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_test_results(self, results_file: Path) -> List[TestResult]:
        """Load test results from JUnit XML or JSON."""
        results = []
        
        if results_file.suffix == ".json":
            with open(results_file) as f:
                data = json.load(f)
            
            for test in data.get("tests", []):
                results.append(TestResult(
                    test_id=test.get("id", test.get("name", "")),
                    name=test.get("name", ""),
                    category=test.get("category", "unknown"),
                    status=test.get("outcome", "unknown"),
                    duration_seconds=test.get("duration", 0),
                    timestamp=test.get("timestamp", datetime.now().isoformat()),
                    error_message=test.get("error", None)
                ))
        
        elif results_file.suffix == ".xml":
            # Parse JUnit XML
            import xml.etree.ElementTree as ET
            tree = ET.parse(results_file)
            root = tree.getroot()
            
            for testcase in root.iter("testcase"):
                status = "passed"
                error_msg = None
                
                if testcase.find("failure") is not None:
                    status = "failed"
                    error_msg = testcase.find("failure").text
                elif testcase.find("skipped") is not None:
                    status = "skipped"
                
                results.append(TestResult(
                    test_id=f"{testcase.get('classname', '')}.{testcase.get('name', '')}",
                    name=testcase.get("name", ""),
                    category=self._extract_category(testcase.get("classname", "")),
                    status=status,
                    duration_seconds=float(testcase.get("time", 0)),
                    timestamp=datetime.now().isoformat(),
                    error_message=error_msg
                ))
        
        return results
    
    def _extract_category(self, classname: str) -> str:
        """Extract category from test class name."""
        if "functional" in classname.lower():
            return "functional"
        elif "accuracy" in classname.lower():
            return "accuracy"
        elif "efficiency" in classname.lower():
            return "efficiency"
        elif "benchmark" in classname.lower():
            return "benchmark"
        elif "e2e" in classname.lower():
            return "e2e"
        elif "output" in classname.lower() or "quality" in classname.lower():
            return "output_quality"
        elif "visualization" in classname.lower():
            return "visualization"
        return "other"
    
    def load_benchmark_results(self, benchmark_file: Path) -> List[BenchmarkDataPoint]:
        """Load benchmark results from JSON."""
        if not benchmark_file.exists():
            return []
        
        with open(benchmark_file) as f:
            data = json.load(f)
        
        results = []
        benchmarks = data.get("benchmarks", data.get("results", []))
        
        if isinstance(benchmarks, dict):
            benchmarks = [{"id": k, **v} for k, v in benchmarks.items()]
        
        for bm in benchmarks:
            results.append(BenchmarkDataPoint(
                benchmark_id=bm.get("benchmark_id", bm.get("id", "")),
                name=bm.get("name", ""),
                value=bm.get("value", bm.get("stats", {}).get("mean", 0)),
                unit=bm.get("unit", ""),
                threshold=bm.get("threshold", 0),
                passed=bm.get("passed", True),
                timestamp=data.get("timestamp", datetime.now().isoformat()),
                commit_sha=data.get("commit", os.getenv("GITHUB_SHA", "local"))
            ))
        
        return results
    
    def create_summary(
        self,
        test_results: List[TestResult],
        commit_sha: str = "",
        branch: str = ""
    ) -> ValidationSummary:
        """Create validation summary from test results."""
        passed = len([t for t in test_results if t.status == "passed"])
        failed = len([t for t in test_results if t.status == "failed"])
        skipped = len([t for t in test_results if t.status == "skipped"])
        total = len(test_results)
        
        by_category = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0})
        for t in test_results:
            by_category[t.category][t.status] += 1
        
        failures = [
            {"test_id": t.test_id, "name": t.name, "error": t.error_message}
            for t in test_results if t.status == "failed"
        ]
        
        return ValidationSummary(
            timestamp=datetime.now().isoformat(),
            commit_sha=commit_sha or os.getenv("GITHUB_SHA", "local"),
            branch=branch or os.getenv("GITHUB_REF", "unknown"),
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=passed / total * 100 if total > 0 else 0,
            by_category=dict(by_category),
            total_duration_seconds=sum(t.duration_seconds for t in test_results),
            failures=failures[:10]  # Limit to 10 failures
        )
    
    def calculate_health(
        self,
        summary: ValidationSummary,
        benchmark_results: List[BenchmarkDataPoint]
    ) -> tuple:
        """Calculate overall health status and score."""
        # Base score from pass rate
        score = summary.pass_rate
        
        # Adjust for benchmark failures
        failed_benchmarks = [b for b in benchmark_results if not b.passed]
        if failed_benchmarks:
            score -= len(failed_benchmarks) * 5
        
        # Determine status
        if score >= 95:
            status = "healthy"
        elif score >= 80:
            status = "warning"
        else:
            status = "critical"
        
        return status, max(0, min(100, score))
    
    def generate_alerts(
        self,
        summary: ValidationSummary,
        benchmark_results: List[BenchmarkDataPoint]
    ) -> List[Dict]:
        """Generate alerts for failures and regressions."""
        alerts = []
        
        # Critical: any failed tests
        if summary.failed > 0:
            alerts.append({
                "level": "error",
                "title": f"{summary.failed} tests failed",
                "message": f"Test failures in: {', '.join(set(f['name'][:30] for f in summary.failures[:3]))}",
                "timestamp": summary.timestamp
            })
        
        # Warning: low pass rate
        if summary.pass_rate < 95:
            alerts.append({
                "level": "warning",
                "title": f"Pass rate below 95%",
                "message": f"Current pass rate: {summary.pass_rate:.1f}%",
                "timestamp": summary.timestamp
            })
        
        # Benchmark failures
        failed_bm = [b for b in benchmark_results if not b.passed]
        if failed_bm:
            alerts.append({
                "level": "error",
                "title": f"{len(failed_bm)} benchmarks below threshold",
                "message": f"Failed: {', '.join(b.benchmark_id for b in failed_bm[:3])}",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
    
    def generate(self) -> DashboardData:
        """Generate complete dashboard data."""
        # Load current results
        all_tests = []
        all_benchmarks = []
        
        for results_file in self.results_dir.glob("*.xml"):
            all_tests.extend(self.load_test_results(results_file))
        
        for results_file in self.results_dir.glob("*.json"):
            if "benchmark" in results_file.name:
                all_benchmarks.extend(self.load_benchmark_results(results_file))
            else:
                all_tests.extend(self.load_test_results(results_file))
        
        # Create current summary
        current_summary = self.create_summary(all_tests)
        
        # Calculate health
        health_status, health_score = self.calculate_health(current_summary, all_benchmarks)
        
        # Generate alerts
        alerts = self.generate_alerts(current_summary, all_benchmarks)
        
        # Build benchmark trends (placeholder - would load from history)
        benchmark_trends = defaultdict(list)
        for bm in all_benchmarks:
            benchmark_trends[bm.benchmark_id].append(bm)
        
        return DashboardData(
            generated_at=datetime.now().isoformat(),
            current_summary=current_summary,
            daily_summaries=[current_summary],  # Would load historical
            benchmark_trends=dict(benchmark_trends),
            active_alerts=alerts,
            overall_health=health_status,
            health_score=health_score
        )
    
    def save(self, data: DashboardData):
        """Save dashboard data to output directory."""
        output_file = self.output_dir / "dashboard_data.json"
        
        with open(output_file, "w") as f:
            json.dump(asdict(data), f, indent=2, default=str)
        
        print(f"Dashboard data saved to: {output_file}")
        return output_file


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate validation dashboard data")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Directory containing test results"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("webdashboard/data"),
        help="Output directory for dashboard data"
    )
    
    args = parser.parse_args()
    
    generator = DashboardGenerator(args.results_dir, args.output_dir)
    data = generator.generate()
    generator.save(data)
    
    print(f"\n📊 Dashboard Summary:")
    print(f"   Health: {data.overall_health} ({data.health_score:.0f}/100)")
    print(f"   Tests: {data.current_summary.passed}/{data.current_summary.total_tests} passed")
    print(f"   Alerts: {len(data.active_alerts)}")


if __name__ == "__main__":
    main()
```

### 2. Dashboard HTML Panel

**File:** `webdashboard/validation-matrix.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Matrix Dashboard</title>
    <style>
        :root {
            --color-healthy: #22c55e;
            --color-warning: #f59e0b;
            --color-critical: #ef4444;
            --color-bg: #1e293b;
            --color-card: #334155;
            --color-text: #f1f5f9;
            --color-muted: #94a3b8;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            padding: 2rem;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        
        h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .timestamp {
            color: var(--color-muted);
            font-size: 0.875rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: var(--color-card);
            border-radius: 0.75rem;
            padding: 1.5rem;
        }
        
        .card-title {
            font-size: 0.875rem;
            color: var(--color-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .health-indicator {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .health-circle {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 700;
        }
        
        .health-circle.healthy { background: var(--color-healthy); }
        .health-circle.warning { background: var(--color-warning); }
        .health-circle.critical { background: var(--color-critical); }
        
        .health-label {
            font-size: 1.25rem;
            font-weight: 600;
            text-transform: capitalize;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
        }
        
        .stat-value.passed { color: var(--color-healthy); }
        .stat-value.failed { color: var(--color-critical); }
        .stat-value.skipped { color: var(--color-warning); }
        
        .stat-label {
            font-size: 0.75rem;
            color: var(--color-muted);
            text-transform: uppercase;
        }
        
        .category-bar {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .category-bar:last-child {
            border-bottom: none;
        }
        
        .category-name {
            font-weight: 500;
        }
        
        .category-counts {
            display: flex;
            gap: 1rem;
            font-size: 0.875rem;
        }
        
        .alert-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        
        .alert {
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
        }
        
        .alert.error {
            background: rgba(239, 68, 68, 0.2);
            border-left: 3px solid var(--color-critical);
        }
        
        .alert.warning {
            background: rgba(245, 158, 11, 0.2);
            border-left: 3px solid var(--color-warning);
        }
        
        .alert-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        
        .alert-message {
            color: var(--color-muted);
        }
        
        .benchmark-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .benchmark-table th,
        .benchmark-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .benchmark-table th {
            color: var(--color-muted);
            font-size: 0.75rem;
            text-transform: uppercase;
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .status-badge.pass { background: var(--color-healthy); }
        .status-badge.fail { background: var(--color-critical); }
        
        .chart-container {
            height: 200px;
            position: relative;
        }
        
        .no-data {
            color: var(--color-muted);
            text-align: center;
            padding: 2rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Validation Matrix Dashboard</h1>
        <span class="timestamp" id="timestamp">Loading...</span>
    </div>
    
    <div class="grid">
        <!-- Health Score -->
        <div class="card">
            <div class="card-title">Overall Health</div>
            <div class="health-indicator">
                <div class="health-circle" id="health-circle">--</div>
                <div>
                    <div class="health-label" id="health-status">Loading...</div>
                    <div class="timestamp" id="health-detail">Calculating...</div>
                </div>
            </div>
        </div>
        
        <!-- Test Results -->
        <div class="card">
            <div class="card-title">Test Results</div>
            <div class="stats">
                <div>
                    <div class="stat-value passed" id="passed-count">-</div>
                    <div class="stat-label">Passed</div>
                </div>
                <div>
                    <div class="stat-value failed" id="failed-count">-</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div>
                    <div class="stat-value skipped" id="skipped-count">-</div>
                    <div class="stat-label">Skipped</div>
                </div>
            </div>
        </div>
        
        <!-- Pass Rate -->
        <div class="card">
            <div class="card-title">Pass Rate</div>
            <div style="font-size: 3rem; font-weight: 700; text-align: center; padding: 1rem 0;">
                <span id="pass-rate">-</span>%
            </div>
        </div>
    </div>
    
    <div class="grid">
        <!-- By Category -->
        <div class="card">
            <div class="card-title">Results by Category</div>
            <div id="category-breakdown">
                <div class="no-data">Loading categories...</div>
            </div>
        </div>
        
        <!-- Alerts -->
        <div class="card">
            <div class="card-title">Active Alerts</div>
            <div class="alert-list" id="alerts">
                <div class="no-data">No alerts</div>
            </div>
        </div>
    </div>
    
    <div class="card" style="margin-top: 1.5rem;">
        <div class="card-title">Benchmark Results</div>
        <table class="benchmark-table" id="benchmark-table">
            <thead>
                <tr>
                    <th>Benchmark</th>
                    <th>Value</th>
                    <th>Threshold</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="benchmark-body">
                <tr><td colspan="4" class="no-data">Loading benchmarks...</td></tr>
            </tbody>
        </table>
    </div>
    
    <script>
        async function loadDashboardData() {
            try {
                const response = await fetch('data/dashboard_data.json');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Failed to load dashboard data:', error);
                document.getElementById('health-status').textContent = 'Error loading data';
            }
        }
        
        function updateDashboard(data) {
            // Timestamp
            document.getElementById('timestamp').textContent = 
                `Last updated: ${new Date(data.generated_at).toLocaleString()}`;
            
            // Health
            const healthCircle = document.getElementById('health-circle');
            healthCircle.textContent = Math.round(data.health_score);
            healthCircle.className = `health-circle ${data.overall_health}`;
            document.getElementById('health-status').textContent = data.overall_health;
            document.getElementById('health-detail').textContent = 
                `${data.current_summary.total_tests} tests analyzed`;
            
            // Test counts
            document.getElementById('passed-count').textContent = data.current_summary.passed;
            document.getElementById('failed-count').textContent = data.current_summary.failed;
            document.getElementById('skipped-count').textContent = data.current_summary.skipped;
            document.getElementById('pass-rate').textContent = data.current_summary.pass_rate.toFixed(1);
            
            // Category breakdown
            const categoryDiv = document.getElementById('category-breakdown');
            categoryDiv.innerHTML = '';
            for (const [category, counts] of Object.entries(data.current_summary.by_category)) {
                categoryDiv.innerHTML += `
                    <div class="category-bar">
                        <span class="category-name">${category}</span>
                        <div class="category-counts">
                            <span style="color: var(--color-healthy)">✓ ${counts.passed || 0}</span>
                            <span style="color: var(--color-critical)">✗ ${counts.failed || 0}</span>
                        </div>
                    </div>
                `;
            }
            
            // Alerts
            const alertsDiv = document.getElementById('alerts');
            if (data.active_alerts && data.active_alerts.length > 0) {
                alertsDiv.innerHTML = data.active_alerts.map(alert => `
                    <div class="alert ${alert.level}">
                        <div class="alert-title">${alert.title}</div>
                        <div class="alert-message">${alert.message}</div>
                    </div>
                `).join('');
            } else {
                alertsDiv.innerHTML = '<div class="no-data">✓ No active alerts</div>';
            }
            
            // Benchmarks
            const benchmarkBody = document.getElementById('benchmark-body');
            const benchmarks = Object.values(data.benchmark_trends).flat();
            if (benchmarks.length > 0) {
                benchmarkBody.innerHTML = benchmarks.map(bm => `
                    <tr>
                        <td>${bm.name || bm.benchmark_id}</td>
                        <td>${bm.value.toFixed(3)} ${bm.unit}</td>
                        <td>${bm.threshold.toFixed(3)} ${bm.unit}</td>
                        <td><span class="status-badge ${bm.passed ? 'pass' : 'fail'}">${bm.passed ? 'PASS' : 'FAIL'}</span></td>
                    </tr>
                `).join('');
            } else {
                benchmarkBody.innerHTML = '<tr><td colspan="4" class="no-data">No benchmark data</td></tr>';
            }
        }
        
        // Load on page load
        loadDashboardData();
        
        // Auto-refresh every 5 minutes
        setInterval(loadDashboardData, 5 * 60 * 1000);
    </script>
</body>
</html>
```

### 3. Slack Notification Script

**File:** `scripts/notifications/slack_notify.py`

```python
#!/usr/bin/env python3
"""
Slack Notification for Validation Results

Sends formatted Slack messages for validation failures and benchmark regressions.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import urllib.error


def create_failure_message(
    summary: Dict,
    alerts: List[Dict],
    repo: str = "",
    branch: str = "",
    commit: str = ""
) -> Dict:
    """Create Slack message for validation failures."""
    
    # Determine color based on severity
    if summary.get("failed", 0) > 0:
        color = "#ef4444"  # Red
        status_emoji = "🔴"
    elif summary.get("pass_rate", 100) < 95:
        color = "#f59e0b"  # Orange
        status_emoji = "🟡"
    else:
        color = "#22c55e"  # Green
        status_emoji = "🟢"
    
    # Build message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} Validation Matrix Results",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Repository:*\n{repo or 'Literature-Review'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Branch:*\n{branch or 'unknown'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Pass Rate:*\n{summary.get('pass_rate', 0):.1f}%"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Tests:*\n{summary.get('passed', 0)}/{summary.get('total_tests', 0)} passed"
                }
            ]
        }
    ]
    
    # Add failures if any
    if summary.get("failed", 0) > 0:
        failures = summary.get("failures", [])[:5]
        failure_text = "\n".join([f"• `{f['name']}`" for f in failures])
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Failed Tests:*\n{failure_text}"
            }
        })
    
    # Add alerts
    if alerts:
        alert_text = "\n".join([f"• {a['title']}" for a in alerts[:3]])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Alerts:*\n{alert_text}"
            }
        })
    
    # Add action buttons
    if commit:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Details",
                        "emoji": True
                    },
                    "url": f"https://github.com/{repo}/commit/{commit}"
                }
            ]
        })
    
    return {
        "attachments": [
            {
                "color": color,
                "blocks": blocks
            }
        ]
    }


def create_regression_message(
    regressions: List[Dict],
    repo: str = "",
    branch: str = ""
) -> Dict:
    """Create Slack message for benchmark regressions."""
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚠️ Benchmark Regression Detected",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{len(regressions)} benchmarks regressed* in `{branch or 'unknown'}`"
            }
        }
    ]
    
    # Add regression details
    for reg in regressions[:5]:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{reg['name']}*\n"
                    f"Baseline: {reg['baseline']:.3f} → Current: {reg['current']:.3f} "
                    f"({reg['change']:+.1f}%)"
                )
            }
        })
    
    return {
        "attachments": [
            {
                "color": "#ef4444",
                "blocks": blocks
            }
        ]
    }


def send_slack_message(webhook_url: str, message: Dict) -> bool:
    """Send message to Slack webhook."""
    try:
        data = json.dumps(message).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    
    except urllib.error.URLError as e:
        print(f"Failed to send Slack message: {e}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Send Slack notification for validation results")
    parser.add_argument(
        "--dashboard-data",
        type=Path,
        help="Path to dashboard_data.json"
    )
    parser.add_argument(
        "--regression-report",
        type=Path,
        help="Path to regression report JSON"
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=os.getenv("SLACK_WEBHOOK_URL"),
        help="Slack webhook URL"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=os.getenv("GITHUB_REPOSITORY", ""),
        help="GitHub repository"
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=os.getenv("GITHUB_REF_NAME", ""),
        help="Branch name"
    )
    parser.add_argument(
        "--commit",
        type=str,
        default=os.getenv("GITHUB_SHA", ""),
        help="Commit SHA"
    )
    parser.add_argument(
        "--only-on-failure",
        action="store_true",
        help="Only send notification if there are failures"
    )
    
    args = parser.parse_args()
    
    if not args.webhook_url:
        print("Warning: No Slack webhook URL provided, skipping notification")
        return
    
    # Load dashboard data if provided
    if args.dashboard_data and args.dashboard_data.exists():
        with open(args.dashboard_data) as f:
            data = json.load(f)
        
        summary = data.get("current_summary", {})
        alerts = data.get("active_alerts", [])
        
        # Check if we should send
        if args.only_on_failure:
            if summary.get("failed", 0) == 0 and not alerts:
                print("No failures, skipping notification")
                return
        
        message = create_failure_message(
            summary, alerts,
            repo=args.repo,
            branch=args.branch,
            commit=args.commit
        )
        
        if send_slack_message(args.webhook_url, message):
            print("✓ Slack notification sent")
        else:
            print("✗ Failed to send Slack notification")
            sys.exit(1)
    
    # Load regression report if provided
    if args.regression_report and args.regression_report.exists():
        with open(args.regression_report) as f:
            regressions = json.load(f)
        
        if regressions:
            message = create_regression_message(
                regressions,
                repo=args.repo,
                branch=args.branch
            )
            send_slack_message(args.webhook_url, message)


if __name__ == "__main__":
    main()
```

---

## Implementation Plan

### Hour 1-2: Dashboard Data Generator
1. Implement test result loading (JSON/XML)
2. Implement benchmark result loading
3. Create summary generation

### Hour 3-4: Dashboard HTML
1. Create responsive dashboard layout
2. Implement health indicators
3. Add category breakdown

### Hour 5-6: Trend Analysis
1. Implement benchmark trend storage
2. Create trend visualization
3. Add historical comparison

### Hour 7-8: Notifications & Integration
1. Implement Slack notification script
2. Add CI/CD integration hooks
3. Document usage and configuration

---

## Testing Instructions

```bash
# Generate dashboard data
python scripts/dashboard/generate_validation_data.py \
  --results-dir results/ \
  --output-dir webdashboard/data/

# View dashboard locally
python -m http.server 8000 --directory webdashboard/

# Test Slack notification
python scripts/notifications/slack_notify.py \
  --dashboard-data webdashboard/data/dashboard_data.json \
  --webhook-url "$SLACK_WEBHOOK_URL" \
  --only-on-failure
```

---

## Dependencies

### Python Packages
- Standard library only (json, xml, urllib)

### Optional
- `requests>=2.28.0` - Alternative HTTP client
- `jinja2>=3.1.0` - Template rendering for reports

---

## Acceptance Criteria

- [ ] Dashboard displays health score, pass rate, test counts
- [ ] Category breakdown shows per-category results
- [ ] Alerts displayed for failures and regressions
- [ ] Benchmark table shows all benchmarks with status
- [ ] Dashboard auto-refreshes every 5 minutes
- [ ] Slack notifications sent on failures
- [ ] 30-day trend data preserved
- [ ] CI/CD workflow triggers dashboard update

---

## Notes

- Dashboard uses static JSON data (no backend required)
- Slack webhook URL should be stored as GitHub secret
- Consider adding email notifications as backup
- Historical data stored as artifacts in GitHub Actions
- Dashboard can be hosted on GitHub Pages
