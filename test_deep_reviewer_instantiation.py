#!/usr/bin/env python3
"""
Deep Reviewer Instantiation Test
Tests manual instantiation and configuration of Deep Reviewer components
"""

import sys
import os
import json
from pathlib import Path

def test_deep_reviewer_instantiation():
    """Test that Deep Reviewer can be manually instantiated and configured"""
    
    print("=" * 70)
    print("DEEP REVIEWER INSTANTIATION TEST")
    print("=" * 70)
    
    # Step 1: Import module
    print("\n[1/6] Testing module import...")
    try:
        from literature_review.reviewers import deep_reviewer
        print("✅ Module imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Step 2: Test component instantiation
    print("\n[2/6] Testing component instantiation...")
    try:
        # APIManager
        api_manager = deep_reviewer.APIManager()
        print("✅ APIManager instantiated")
        
        # TextExtractor
        text_extractor = deep_reviewer.TextExtractor()
        print("✅ TextExtractor instantiated")
        print(f"   TextExtractor class: {type(text_extractor).__name__}")
        
    except Exception as e:
        print(f"❌ Component instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Check file paths configuration
    print("\n[3/6] Checking file path configuration...")
    config = {
        "PAPERS_FOLDER": deep_reviewer.PAPERS_FOLDER,
        "RESEARCH_DB_FILE": deep_reviewer.RESEARCH_DB_FILE,
        "GAP_REPORT_FILE": deep_reviewer.GAP_REPORT_FILE,
        "DEEP_REVIEW_DIRECTIONS_FILE": deep_reviewer.DEEP_REVIEW_DIRECTIONS_FILE,
        "VERSION_HISTORY_FILE": deep_reviewer.VERSION_HISTORY_FILE,
    }
    
    for key, value in config.items():
        print(f"   {key}: {value}")
    
    # Step 4: Check required files existence
    print("\n[4/6] Checking required files...")
    files_status = {}
    
    # Gap analysis outputs
    gap_report = config["GAP_REPORT_FILE"]
    files_status["Gap Report"] = os.path.exists(gap_report)
    print(f"   {'✅' if files_status['Gap Report'] else '❌'} Gap Report: {gap_report}")
    
    directions_file = config["DEEP_REVIEW_DIRECTIONS_FILE"]
    files_status["Directions"] = os.path.exists(directions_file)
    print(f"   {'✅' if files_status['Directions'] else '❌'} Directions: {directions_file}")
    
    # Version history - check both locations
    vh_file = config["VERSION_HISTORY_FILE"]
    vh_exists = os.path.exists(vh_file)
    vh_root = "review_version_history.json"
    vh_root_exists = os.path.exists(vh_root)
    
    files_status["Version History"] = vh_exists or vh_root_exists
    
    if vh_exists:
        print(f"   ✅ Version History: {vh_file}")
    elif vh_root_exists:
        print(f"   ⚠️  Version History at root (expected at {vh_file}): {vh_root}")
        print(f"      → You may need to move or create symlink")
    else:
        print(f"   ❌ Version History not found")
    
    # Research database
    research_db = config["RESEARCH_DB_FILE"]
    research_db_full = f"data/{research_db}" if not research_db.startswith("data/") else research_db
    files_status["Research DB"] = os.path.exists(research_db_full)
    print(f"   {'✅' if files_status['Research DB'] else '❌'} Research DB: {research_db_full}")
    
    # Papers folder
    papers_folder = config["PAPERS_FOLDER"]
    files_status["Papers Folder"] = os.path.isdir(papers_folder)
    if files_status["Papers Folder"]:
        num_pdfs = len([f for f in os.listdir(papers_folder) if f.endswith('.pdf')])
        print(f"   ✅ Papers Folder: {papers_folder} ({num_pdfs} PDFs)")
    else:
        print(f"   ❌ Papers Folder: {papers_folder}")
    
    # Step 5: Test helper functions
    print("\n[5/6] Testing helper functions...")
    try:
        # Test load functions with actual files
        if files_status["Gap Report"]:
            gap_data = deep_reviewer.load_gap_report(gap_report)
            if gap_data:
                print(f"   ✅ load_gap_report(): {len(gap_data)} pillars")
            else:
                print(f"   ⚠️  load_gap_report() returned None")
        
        if files_status["Directions"]:
            directions = deep_reviewer.load_directions(directions_file)
            if directions:
                print(f"   ✅ load_directions(): {len(directions)} directions")
            else:
                print(f"   ⚠️  load_directions() returned empty")
        
        # Test version history loading (try both locations)
        vh_to_load = vh_file if vh_exists else (vh_root if vh_root_exists else None)
        if vh_to_load:
            version_hist = deep_reviewer.load_version_history(vh_to_load)
            if version_hist:
                print(f"   ✅ load_version_history(): {len(version_hist)} entries")
            else:
                print(f"   ⚠️  load_version_history() returned empty")
        
    except Exception as e:
        print(f"   ⚠️  Helper function test failed: {e}")
    
    # Step 6: Manual instantiation guide
    print("\n[6/6] Manual instantiation readiness...")
    all_required = all([
        files_status.get("Gap Report", False),
        files_status.get("Version History", False),
        files_status.get("Papers Folder", False)
    ])
    
    if all_required:
        print("   ✅ All required files present")
        print("\n" + "=" * 70)
        print("✅ DEEP REVIEWER CAN BE MANUALLY INSTANTIATED")
        print("=" * 70)
        print("\nTo run Deep Reviewer manually:")
        print("   python -m literature_review.reviewers.deep_reviewer")
        print("\nOr import in Python:")
        print("   from literature_review.reviewers.deep_reviewer import main")
        print("   main()")
        
        if vh_root_exists and not vh_exists:
            print("\n⚠️  RECOMMENDATION:")
            print(f"   Move version history to expected location:")
            print(f"   mv {vh_root} {vh_file}")
            print(f"   or create directory: mkdir -p data")
        
        return True
    else:
        print("   ❌ Missing required files")
        print("\n" + "=" * 70)
        print("❌ CANNOT RUN DEEP REVIEWER - MISSING FILES")
        print("=" * 70)
        
        print("\nMissing components:")
        for name, exists in files_status.items():
            if not exists:
                print(f"   ❌ {name}")
        
        print("\nTo fix:")
        if not files_status.get("Gap Report"):
            print("   • Run orchestrator to generate gap analysis")
        if not files_status.get("Version History"):
            print("   • Run journal reviewer and judge to create version history")
        if not files_status.get("Papers Folder"):
            print(f"   • Create papers folder: mkdir -p {papers_folder}")
            print(f"   • Add PDF files to {papers_folder}")
        
        return False

if __name__ == "__main__":
    success = test_deep_reviewer_instantiation()
    sys.exit(0 if success else 1)
