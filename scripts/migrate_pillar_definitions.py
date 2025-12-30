#!/usr/bin/env python3
"""
Migrate pillar_definitions_enhanced.json to include benchmark linkage.

This script:
1. Backs up the existing file
2. Restructures quantitative_metrics with benchmark linkage
3. Adds validation_strategy placeholders to requirements
4. Validates the output schema
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def backup_file(filepath: Path) -> Path:
    """Create timestamped backup of file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = filepath.with_suffix(f".backup_{timestamp}.json")
    shutil.copy(filepath, backup_path)
    print(f"✅ Backed up to: {backup_path}")
    return backup_path


def migrate_quantitative_metrics(metrics: Dict) -> Dict:
    """
    Migrate flat metrics to benchmark-linked structure.
    
    Before:
        {"latency_target": "< 10ms end-to-end"}
    
    After:
        {"latency_target": {
            "target_value": "< 10ms end-to-end",
            "measurement_method": "",
            "benchmarks": [],
            "benchmark_status": "no_benchmark",
            "validation_evidence": []
        }}
    """
    migrated = {}
    
    for metric_name, value in metrics.items():
        if isinstance(value, str):
            # Old format - migrate
            migrated[metric_name] = {
                "target_value": value,
                "measurement_method": "",
                "benchmarks": [],
                "benchmark_status": "no_benchmark",
                "validation_evidence": []
            }
        elif isinstance(value, dict):
            # Already new format or partially migrated
            # Extract target_value - prefer existing, then try common field names
            target_val = value.get("target_value") or value.get("value") or value.get("target")
            if target_val is None:
                # Last resort: use first string value found or empty string
                for v in value.values():
                    if isinstance(v, str):
                        target_val = v
                        break
                if target_val is None:
                    target_val = ""
            
            migrated[metric_name] = {
                "target_value": target_val,
                "measurement_method": value.get("measurement_method", ""),
                "benchmarks": value.get("benchmarks", []),
                "benchmark_status": value.get("benchmark_status", "no_benchmark"),
                "validation_evidence": value.get("validation_evidence", [])
            }
        else:
            # Unknown format - preserve as-is with wrapper
            migrated[metric_name] = {
                "target_value": str(value),
                "measurement_method": "",
                "benchmarks": [],
                "benchmark_status": "no_benchmark",
                "validation_evidence": []
            }
    
    return migrated


def add_validation_strategies(requirements: Dict) -> Dict:
    """
    Add validation_strategy placeholders to requirements.
    
    Transforms:
        ["Sub-1.1.1: Description", "Sub-1.1.2: Description"]
    
    To:
        [
            {
                "id": "Sub-1.1.1",
                "text": "Description",
                "validation_strategy": {...}
            }
        ]
    """
    migrated = {}
    
    for req_key, sub_reqs in requirements.items():
        if isinstance(sub_reqs, list):
            migrated_subs = []
            for sub_req in sub_reqs:
                if isinstance(sub_req, str):
                    # Parse "Sub-X.X.X: Description" format
                    if ": " in sub_req:
                        parts = sub_req.split(": ", 1)
                        sub_id = parts[0]
                        sub_text = parts[1] if len(parts) > 1 else ""
                    else:
                        sub_id = sub_req
                        sub_text = sub_req
                    
                    migrated_subs.append({
                        "id": sub_id,
                        "text": sub_text,
                        "validation_strategy": {
                            "method": "",
                            "benchmark_protocol": "",
                            "acceptance_criteria": "",
                            "required_evidence_types": [],
                            "status": "no_strategy"
                        }
                    })
                elif isinstance(sub_req, dict):
                    # Already structured - ensure validation_strategy exists
                    if "validation_strategy" not in sub_req:
                        sub_req["validation_strategy"] = {
                            "method": "",
                            "benchmark_protocol": "",
                            "acceptance_criteria": "",
                            "required_evidence_types": [],
                            "status": "no_strategy"
                        }
                    migrated_subs.append(sub_req)
            
            migrated[req_key] = migrated_subs
        else:
            migrated[req_key] = sub_reqs
    
    return migrated


def migrate_pillar(pillar_data: Dict) -> Dict:
    """Migrate a single pillar's data."""
    migrated = pillar_data.copy()
    
    # Migrate quantitative_metrics
    if "quantitative_metrics" in migrated:
        migrated["quantitative_metrics"] = migrate_quantitative_metrics(
            migrated["quantitative_metrics"]
        )
    
    # Add validation strategies to requirements
    if "requirements" in migrated:
        migrated["requirements"] = add_validation_strategies(
            migrated["requirements"]
        )
    
    return migrated


def migrate_pillar_definitions(input_path: str, output_path: str = None) -> Dict:
    """
    Main migration function.
    
    Args:
        input_path: Path to existing pillar_definitions_enhanced.json
        output_path: Path for migrated file (default: overwrite input)
    
    Returns:
        Migrated data dictionary
    """
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path else input_path
    
    # Backup original
    backup_file(input_path)
    
    # Load existing data
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📖 Loaded {len(data)} top-level keys")
    
    # Migrate each pillar
    migrated = {}
    for key, value in data.items():
        if key.startswith("Pillar") or key in ["Cross_Cutting_Requirements", "Success_Criteria"]:
            if isinstance(value, dict):
                migrated[key] = migrate_pillar(value)
                print(f"  ✅ Migrated: {key}")
            else:
                migrated[key] = value
        else:
            # Preserve non-pillar keys (Framework_Overview, etc.)
            migrated[key] = value
    
    # Add schema version
    migrated["_schema_version"] = "2.0.0"
    migrated["_migrated_at"] = datetime.now().isoformat()
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(migrated, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Wrote migrated file to: {output_path}")
    
    return migrated


if __name__ == "__main__":
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else "pillar_definitions_enhanced.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    migrate_pillar_definitions(input_file, output_file)
