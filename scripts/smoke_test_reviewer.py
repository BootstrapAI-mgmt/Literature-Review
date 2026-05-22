"""Smoke-test the journal-reviewer pipeline on a small batch of PDFs.

Validates the upgraded reviewer end-to-end:
  - pymupdf-primary PDF text extraction
  - PDF_METADATA injection (filename/title/authors/DOI/year/page_count)
  - Provider-aware APIManager (Gemini direct path vs. llm_client)
  - review_version_history.json receives new entries

Usage:
    PYTHONIOENCODING=utf-8 python scripts/smoke_test_reviewer.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import tempfile
from pathlib import Path

# Make repo root importable when run from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Load env from main clone if worktree has none
worktree_env = Path(".env")
if not worktree_env.exists():
    load_dotenv("C:/Users/jpcol/Documents/Literature-Review/Literature-Review/.env")
else:
    load_dotenv(worktree_env)

# Use an isolated version history to avoid stomping on real data
sandbox_dir = Path(tempfile.mkdtemp(prefix="reviewer_smoke_"))
sandbox_history = sandbox_dir / "review_version_history.json"
print(f"Sandbox version history: {sandbox_history}")

# Patch journal_reviewer's VERSION_HISTORY_FILE before import
import literature_review.reviewers.journal_reviewer as jr  # noqa: E402

jr.VERSION_HISTORY_FILE = str(sandbox_history)

from literature_review.reviewers.journal_reviewer import (  # noqa: E402
    APIManager,
    NetworkAnalyzer,
    ReviewVersionControl,
    process_batch,
)

pdfs = glob.glob("data/raw/**/*.pdf", recursive=True)
print(f"Worktree PDFs: {len(pdfs)}")
batch_files = [(p, os.path.basename(p)) for p in pdfs[:3]]
print(f"Smoke batch (3 PDFs):")
for _, name in batch_files:
    print(f"  - {name}")

# Minimal pillar definitions
pillar_definitions_str = json.dumps(
    {"Pillar1": {"sub_requirements": ["test"], "description": "smoke-test pillar"}}
)

api_manager = APIManager()
print(f"APIManager provider: {api_manager.provider.value}")
print(f"APIManager model: {api_manager.active_model_name}")

network_analyzer = NetworkAnalyzer(api_manager.embedder)
version_control = ReviewVersionControl()

journal_results, non_journal_results = process_batch(
    batch_files=batch_files,
    api_manager=api_manager,
    network_analyzer=network_analyzer,
    version_control=version_control,
    existing_reviews=[],
    pillar_definitions_str=pillar_definitions_str,
)

print(f"\nJournal results: {len(journal_results)}")
print(f"Non-journal results: {len(non_journal_results)}")

# Validate version history
if sandbox_history.exists():
    history = json.loads(sandbox_history.read_text(encoding="utf-8"))
    print(f"\nVersion history entries: {len(history)}")
    for filename, versions in history.items():
        latest = versions[-1]["review"]
        pdf_md = latest.get("PDF_METADATA", {})
        print(f"\n  {filename}")
        print(f"    PDF_METADATA present: {bool(pdf_md)}")
        if pdf_md:
            print(f"      title:      {(pdf_md.get('title') or '')[:80]}")
            print(f"      authors:    {pdf_md.get('authors')[:2] if pdf_md.get('authors') else None}")
            print(f"      doi:        {pdf_md.get('doi')}")
            print(f"      year:       {pdf_md.get('year')}")
            print(f"      page_count: {pdf_md.get('page_count')}")
            print(f"      backend:    {pdf_md.get('extraction_backend')}")
else:
    print(f"\nWARNING: version history not created at {sandbox_history}")
    sys.exit(2)

print("\nSMOKE_TEST_DONE")
