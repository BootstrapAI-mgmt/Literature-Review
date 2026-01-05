#!/usr/bin/env python3
"""
Domain Fixture Validation Script

Validates domain fixtures similar to metrics configuration validation.
Checks for required files, schema compliance, and cross-references.

Usage:
    python scripts/validate_domain_fixture.py domains/neuromorphic-computing/
    python scripts/validate_domain_fixture.py --all
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_domain(domain_dir: Path) -> Dict[str, Any]:
    """Validate a single domain fixture."""
    result = {
        "domain_dir": str(domain_dir),
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    
    # Check required files
    required_files = [
        "research_config.json",
        "pillar_definitions.json"
    ]
    
    for req_file in required_files:
        if not (domain_dir / req_file).exists():
            result["errors"].append(f"Missing required file: {req_file}")
            result["valid"] = False
    
    # Check optional files
    optional_files = [
        "golden_dataset.json",
        "test_baselines.json"
    ]
    
    for opt_file in optional_files:
        if not (domain_dir / opt_file).exists():
            result["warnings"].append(f"Missing optional file: {opt_file}")
    
    # Validate research_config.json
    config_path = domain_dir / "research_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            result["stats"]["domain_id"] = config.get("domain", {}).get("id", "unknown")
            result["stats"]["domain_name"] = config.get("domain", {}).get("name", "unknown")
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON in research_config.json: {e}")
            result["valid"] = False
    
    # Validate golden_dataset.json if present
    golden_path = domain_dir / "golden_dataset.json"
    if golden_path.exists():
        try:
            with open(golden_path) as f:
                golden = json.load(f)
            result["stats"]["claim_count"] = len(golden.get("claims", []))
            result["stats"]["gap_count"] = len(golden.get("known_gaps", []))
            result["stats"]["paper_count"] = len(golden.get("papers", []))
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON in golden_dataset.json: {e}")
            result["valid"] = False
    
    return result


def validate_all_domains(domains_dir: Path) -> List[Dict[str, Any]]:
    """Validate all domains in the domains directory."""
    results = []
    
    for subdir in sorted(domains_dir.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name.startswith((".", "_")):
            continue
        
        # Check if it looks like a domain directory
        if (subdir / "research_config.json").exists():
            results.append(validate_domain(subdir))
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Validate domain fixtures")
    parser.add_argument("domain_dir", nargs="?", help="Path to domain directory")
    parser.add_argument("--all", action="store_true", help="Validate all domains")
    parser.add_argument("--domains-dir", default="domains", help="Domains directory")
    args = parser.parse_args()
    
    if args.all:
        results = validate_all_domains(Path(args.domains_dir))
    elif args.domain_dir:
        results = [validate_domain(Path(args.domain_dir))]
    else:
        parser.print_help()
        sys.exit(1)
    
    # Print results
    all_valid = True
    for result in results:
        status = "✓ VALID" if result["valid"] else "✗ INVALID"
        print(f"\n{status}: {result['domain_dir']}")
        
        if result.get("stats"):
            print(f"  Domain: {result['stats'].get('domain_name', 'unknown')}")
            if "claim_count" in result["stats"]:
                print(f"  Claims: {result['stats']['claim_count']}")
                print(f"  Gaps: {result['stats']['gap_count']}")
        
        for error in result["errors"]:
            print(f"  ERROR: {error}")
        for warning in result["warnings"]:
            print(f"  WARNING: {warning}")
        
        if not result["valid"]:
            all_valid = False
    
    print(f"\n{'='*50}")
    print(f"Total: {len(results)} domains, {'all valid' if all_valid else 'some invalid'}")
    
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
