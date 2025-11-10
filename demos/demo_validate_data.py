#!/usr/bin/env python3
"""
Data Structure Validation Demo

This demo validates all data files for schema compliance and detects
common issues like circular references, missing fields, and invalid JSON.

Run: python demos/demo_validate_data.py
"""

import json
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Judge import detect_circular_refs


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def validate_version_history():
    """Validate review_version_history_EXAMPLE.json structure."""
    print_section("Validating Version History")
    
    filepath = "review_version_history_EXAMPLE.json"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    try:
        with open(filepath) as f:
            history = json.load(f)
        
        print(f"✅ Valid JSON structure")
        print(f"   Files tracked: {len(history)}")
        
        # Count total versions
        total_versions = sum(len(versions) for versions in history.values())
        print(f"   Total versions: {total_versions}")
        
        # Count total claims
        total_claims = 0
        approved = 0
        rejected = 0
        pending = 0
        
        for filename, versions in history.items():
            latest = versions[-1]["review"]
            claims = latest.get("Requirement(s)", [])
            total_claims += len(claims)
            
            for claim in claims:
                status = claim.get("status", "unknown")
                if status == "approved":
                    approved += 1
                elif status == "rejected":
                    rejected += 1
                elif "pending" in status:
                    pending += 1
        
        print(f"   Total claims: {total_claims}")
        print(f"     Approved: {approved}")
        print(f"     Rejected: {rejected}")
        print(f"     Pending: {pending}")
        
        # Check for circular references
        print("\n   Checking for circular references...")
        try:
            detect_circular_refs(history)
            print("   ✅ No circular references found")
        except ValueError as e:
            print(f"   ❌ Circular reference detected: {e}")
            return False
        
        # Validate required fields
        print("\n   Validating required fields...")
        required_fields = ["TITLE", "FILENAME", "CORE_DOMAIN", "Requirement(s)"]
        missing_fields = []
        
        for filename, versions in history.items():
            latest = versions[-1]["review"]
            for field in required_fields:
                if field not in latest:
                    missing_fields.append((filename, field))
        
        if missing_fields:
            print(f"   ⚠️  Found {len(missing_fields)} missing fields:")
            for fname, field in missing_fields[:5]:  # Show first 5
                print(f"      {fname}: missing {field}")
        else:
            print("   ✅ All required fields present")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def validate_csv_database():
    """Validate neuromorphic-research_database_EXAMPLE.csv structure."""
    print_section("Validating CSV Database")
    
    filepath = "neuromorphic-research_database_EXAMPLE.csv"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    try:
        df = pd.read_csv(filepath)
        
        print(f"✅ Valid CSV structure")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        
        # Check required columns
        required_cols = [
            "FILENAME", "TITLE", "CORE_DOMAIN", "Requirement(s)",
            "PUBLICATION_YEAR", "REVIEW_TIMESTAMP"
        ]
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ Missing columns: {missing_cols}")
            return False
        else:
            print("✅ All required columns present")
        
        # Check for duplicate filenames
        duplicates = df[df.duplicated(subset=['FILENAME'], keep=False)]
        if len(duplicates) > 0:
            print(f"⚠️  Found {len(duplicates)} duplicate filenames")
        else:
            print("✅ No duplicate filenames")
        
        # Validate Requirements JSON
        print("\n   Validating Requirements JSON...")
        invalid_json = []
        
        for idx, row in df.iterrows():
            try:
                reqs = json.loads(row["Requirement(s)"])
                if not isinstance(reqs, list):
                    invalid_json.append((idx, "Not a list"))
            except json.JSONDecodeError:
                invalid_json.append((idx, "Invalid JSON"))
        
        if invalid_json:
            print(f"   ❌ Found {len(invalid_json)} rows with invalid JSON")
            for idx, error in invalid_json[:5]:
                print(f"      Row {idx}: {error}")
        else:
            print("   ✅ All Requirements are valid JSON lists")
        
        # Check publication years
        print("\n   Validating publication years...")
        invalid_years = df[~df["PUBLICATION_YEAR"].between(1900, 2030)]
        
        if len(invalid_years) > 0:
            print(f"   ⚠️  Found {len(invalid_years)} rows with invalid years")
        else:
            print("   ✅ All publication years are valid")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def validate_pillar_definitions():
    """Validate pillar_definitions_enhanced.json structure."""
    print_section("Validating Pillar Definitions")
    
    filepath = "pillar_definitions_enhanced.json"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    try:
        with open(filepath) as f:
            definitions = json.load(f)
        
        print(f"✅ Valid JSON structure")
        
        # Count pillars
        pillar_keys = [k for k in definitions.keys() if k.startswith("Pillar")]
        print(f"   Pillars defined: {len(pillar_keys)}")
        
        # Count total requirements
        total_requirements = 0
        total_sub_requirements = 0
        
        for pillar_key in pillar_keys:
            pillar_data = definitions[pillar_key]
            if "requirements" in pillar_data:
                reqs = pillar_data["requirements"]
                total_requirements += len(reqs)
                
                for req_key, sub_reqs in reqs.items():
                    total_sub_requirements += len(sub_reqs)
        
        print(f"   Total requirements: {total_requirements}")
        print(f"   Total sub-requirements: {total_sub_requirements}")
        
        # Check for circular references
        print("\n   Checking for circular references...")
        try:
            detect_circular_refs(definitions)
            print("   ✅ No circular references found")
        except ValueError as e:
            print(f"   ❌ Circular reference detected: {e}")
            return False
        
        # List all pillars
        print("\n   Pillar overview:")
        for pillar_key in pillar_keys:
            pillar_data = definitions[pillar_key]
            req_count = len(pillar_data.get("requirements", {}))
            print(f"     {pillar_key}: {req_count} requirement categories")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all validation checks."""
    print("\n" + "█" * 70)
    print("  DATA STRUCTURE VALIDATION DEMO")
    print("█" * 70)
    
    results = []
    
    # Validate version history
    results.append(("Version History", validate_version_history()))
    
    # Validate CSV database
    results.append(("CSV Database", validate_csv_database()))
    
    # Validate pillar definitions
    results.append(("Pillar Definitions", validate_pillar_definitions()))
    
    # Summary
    print_section("VALIDATION SUMMARY")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("  🎉 All validations passed!")
    else:
        print("  ⚠️  Some validations failed - see details above")
    print("=" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
