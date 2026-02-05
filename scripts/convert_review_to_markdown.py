#!/usr/bin/env python3
"""
Golden Dataset JSON to Markdown Converter

Converts review_version_history.json entries to human-readable Markdown reports
following the sample_review format for easy validation and review.

Usage:
    python scripts/convert_review_to_markdown.py [paper_id] [--all] [--output-dir DIR]
    
Examples:
    python scripts/convert_review_to_markdown.py 3604281
    python scripts/convert_review_to_markdown.py --all --output-dir reviews/generated
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


VERSION_HISTORY_FILE = 'review_version_history.json'
DEFAULT_OUTPUT_DIR = 'reviews/generated'


def load_version_history(filepath: str = VERSION_HISTORY_FILE) -> Dict:
    """Load the review version history JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        sys.exit(1)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_list_as_bullets(items: List[str], prefix: str = "-") -> str:
    """Format a list of strings as markdown bullet points."""
    if not items:
        return "_None identified_"
    return "\n".join(f"{prefix} {item}" for item in items)


def format_list_as_numbered(items: List[str]) -> str:
    """Format a list of strings as numbered list."""
    if not items:
        return "_None identified_"
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))


def format_claims_table(claims: List[Dict], pillar_filter: Optional[str] = None) -> str:
    """Format claims as a markdown table, optionally filtered by pillar."""
    filtered = claims
    if pillar_filter:
        filtered = [c for c in claims if c.get('pillar', '').startswith(pillar_filter)]
    
    if not filtered:
        return "_No claims mapped for this pillar_"
    
    lines = [
        "| Sub-Requirement | Evidence | Page | Confidence | Status |",
        "|-----------------|----------|------|------------|--------|"
    ]
    
    for claim in filtered:
        sub_req = claim.get('sub_requirement', 'N/A')
        quote = claim.get('verbatim_quote', claim.get('evidence_chunk', 'N/A'))
        # Truncate long quotes for table display
        if len(quote) > 100:
            quote = quote[:97] + "..."
        quote = quote.replace('|', '\\|').replace('\n', ' ')
        
        location = claim.get('location', {})
        page = location.get('page', 'N/A') if isinstance(location, dict) else 'N/A'
        confidence = claim.get('confidence', 'N/A')
        status = claim.get('status', 'pending_judge_review')
        
        lines.append(f"| {sub_req} | \"{quote}\" | {page} | {confidence} | {status} |")
    
    return "\n".join(lines)


def format_gaps_table(gaps: List[Dict]) -> str:
    """Format gaps as a markdown table."""
    if not gaps:
        return "_No gaps identified_"
    
    lines = [
        "| Gap ID | Type | Description | Page | Status |",
        "|--------|------|-------------|------|--------|"
    ]
    
    for gap in gaps:
        gap_id = gap.get('gap_id', 'N/A')
        gap_type = gap.get('gap_type', 'N/A')
        gap_text = gap.get('gap_text', 'N/A')
        if len(gap_text) > 80:
            gap_text = gap_text[:77] + "..."
        gap_text = gap_text.replace('|', '\\|').replace('\n', ' ')
        
        location = gap.get('location', {})
        page = location.get('page', 'N/A') if isinstance(location, dict) else 'N/A'
        status = gap.get('implied_vs_explicit', 'explicit')
        
        lines.append(f"| {gap_id} | {gap_type} | {gap_text} | {page} | {status} |")
    
    return "\n".join(lines)


def get_unique_pillars(claims: List[Dict]) -> List[str]:
    """Extract unique pillar names from claims, in order of appearance."""
    seen = set()
    pillars = []
    for claim in claims:
        pillar = claim.get('pillar', '')
        if pillar and pillar not in seen:
            seen.add(pillar)
            pillars.append(pillar)
    return pillars


def convert_review_to_markdown(paper_id: str, review_data: Dict) -> str:
    """Convert a single review JSON object to markdown format."""
    
    # Get the latest review if this is a version history entry
    if isinstance(review_data, list) and review_data:
        review = review_data[-1].get('review', review_data[-1])
    elif isinstance(review_data, dict) and 'review' in review_data:
        review = review_data['review']
    else:
        review = review_data
    
    # Extract fields with fallbacks
    title = review.get('TITLE', 'Unknown Title')
    filename = review.get('FILENAME', paper_id)
    timestamp = review.get('REVIEW_TIMESTAMP', review.get('annotation_date', datetime.now().isoformat()))
    
    # Metadata fields
    core_domain = review.get('CORE_DOMAIN', 'N/A')
    sub_domain = review.get('SUB_DOMAIN', 'N/A')
    source = review.get('SOURCE', 'N/A')
    pub_year = review.get('PUBLICATION_YEAR', 'N/A')
    
    # Scores
    domain_relevance = review.get('CORE_DOMAIN_RELEVANCE_SCORE', 'N/A')
    subdomain_relevance = review.get('SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE', 'N/A')
    bio_fidelity = review.get('BIOLOGICAL_FIDELITY', 'N/A')
    reproducibility = review.get('REPRODUCIBILITY_SCORE', 'N/A')
    maturity = review.get('MATURITY_LEVEL', 'N/A')
    
    # Lists
    major_findings = review.get('MAJOR_FINDINGS', [])
    keywords = review.get('KEYWORDS', [])
    core_concepts = review.get('CORE_CONCEPTS', [])
    network_arch = review.get('NETWORK_ARCHITECTURE', [])
    datasets = review.get('DATASET_USED', [])
    
    # Text fields
    applicability = review.get('APPLICABILITY_NOTES', 'N/A')
    gaps_text = review.get('ANALYSIS_GAPS', '')  # Legacy field
    improvement = review.get('IMPROVEMENT_SUGGESTIONS', 'N/A')
    risks = review.get('RISKS', 'N/A')
    energy = review.get('ENERGY_EFFICIENCY', 'N/A')
    implementation = review.get('IMPLEMENTATION_DETAILS', 'N/A')
    validation = review.get('VALIDATION_METHOD', 'N/A')
    bridges = review.get('INTERDISCIPLINARY_BRIDGES', [])
    
    # Golden Dataset structured fields
    claims = review.get('claims', review.get('Requirement(s)', []))
    gaps = review.get('gaps', [])
    methodology = review.get('methodology_summary', {})
    quality_meta = review.get('quality_metadata', {})
    
    # Extraction metadata
    extraction_method = review.get('EXTRACTION_METHOD', 'unknown')
    extraction_quality = review.get('EXTRACTION_QUALITY', 'N/A')
    
    # Build markdown
    md = f"""# Paper Analysis: {title}

**Original Filename:** `{filename}`  
**Analysis Timestamp:** {timestamp}

---

## Metadata

| Field | Value |
|-------|-------|
| **Title** | {title} |
| **Core Domain** | {core_domain} |
| **Sub Domain** | {sub_domain} |
| **Source** | {source} |
| **Publication Year** | {pub_year} |

---

## Scores

| Metric | Score |
|--------|-------|
| **Core Domain Relevance** | {domain_relevance}% |
| **Subdomain Relevance** | {subdomain_relevance}% |
| **Biological Fidelity** | {bio_fidelity} |
| **Reproducibility** | {reproducibility} |
| **Maturity Level** | {maturity} |

---

## Major Findings

{format_list_as_numbered(major_findings)}

---

## Keywords

{format_list_as_bullets(keywords)}

---

## Core Concepts

{format_list_as_bullets(core_concepts)}

---

## Network Architectures

{format_list_as_bullets(network_arch)}

---

## Datasets Used

{format_list_as_bullets(datasets)}

---

## Applicability Notes

{applicability}

---

## Analysis Gaps

{gaps_text if gaps_text else '_See structured gaps below_'}

---

## Improvement Suggestions

{improvement}

---

## Risks

{risks}

---

## Energy Efficiency

{energy}

---

## Implementation Details

{implementation}

---

## Validation Method

{validation}

---

## Interdisciplinary Bridges

{format_list_as_bullets(bridges)}

---

## Claims Mapped (Golden Dataset Format)

"""
    
    # Add claims grouped by pillar
    pillar_names = get_unique_pillars(claims)
    
    if pillar_names:
        for pillar in pillar_names:
            md += f"\n### {pillar}\n\n"
            md += format_claims_table(claims, pillar) + "\n"
    else:
        md += "_No pillar claims identified_\n"
    
    md += f"""
---

## Research Gaps (Structured)

{format_gaps_table(gaps)}

---

## Methodology Summary

| Aspect | Details |
|--------|---------|
| **Approach** | {methodology.get('approach', 'N/A')} |
| **Datasets** | {', '.join(methodology.get('datasets_used', [])) or 'N/A'} |
| **Key Techniques** | {', '.join(methodology.get('key_techniques', [])) or 'N/A'} |
| **Evaluation Metrics** | {', '.join(methodology.get('evaluation_metrics', [])) or 'N/A'} |

---

## Quality Metadata

| Metric | Value |
|--------|-------|
| **Total Claims** | {quality_meta.get('total_claims', len(claims))} |
| **Quantitative Claims** | {quality_meta.get('quantitative_claims', 'N/A')} |
| **Qualitative Claims** | {quality_meta.get('qualitative_claims', 'N/A')} |
| **Total Gaps** | {quality_meta.get('total_gaps', len(gaps))} |
| **Annotation Confidence** | {quality_meta.get('annotation_confidence', 'N/A')} |

---

*Extraction Method: {extraction_method} | Quality: {extraction_quality}*
"""
    
    return md


def save_markdown(content: str, paper_id: str, output_dir: str) -> str:
    """Save markdown content to file and return filepath."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean paper_id for filename
    safe_id = paper_id.replace('.pdf', '').replace('.html', '').replace('.txt', '')
    safe_id = "".join(c for c in safe_id if c.isalnum() or c in '._-')
    
    filepath = os.path.join(output_dir, f"review_{safe_id}.md")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description='Convert Golden Dataset JSON reviews to Markdown reports'
    )
    parser.add_argument(
        'paper_id', 
        nargs='?',
        help='Paper ID (filename) to convert'
    )
    parser.add_argument(
        '--all', 
        action='store_true',
        help='Convert all reviews in version history'
    )
    parser.add_argument(
        '--output-dir', 
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for markdown files (default: {DEFAULT_OUTPUT_DIR})'
    )
    parser.add_argument(
        '--input', 
        default=VERSION_HISTORY_FILE,
        help=f'Input JSON file (default: {VERSION_HISTORY_FILE})'
    )
    
    args = parser.parse_args()
    
    if not args.paper_id and not args.all:
        parser.print_help()
        print("\nError: Specify either a paper_id or --all")
        sys.exit(1)
    
    # Load version history
    history = load_version_history(args.input)
    
    if args.all:
        # Convert all reviews
        converted = 0
        for paper_id, review_data in history.items():
            try:
                md = convert_review_to_markdown(paper_id, review_data)
                filepath = save_markdown(md, paper_id, args.output_dir)
                print(f"✓ Converted: {paper_id} -> {filepath}")
                converted += 1
            except Exception as e:
                print(f"✗ Failed: {paper_id} - {e}")
        
        print(f"\nConverted {converted}/{len(history)} reviews to {args.output_dir}/")
    else:
        # Convert single review
        paper_id = args.paper_id
        
        # Try exact match first, then fuzzy match
        if paper_id not in history:
            # Try adding common extensions
            matches = [k for k in history.keys() if paper_id in k]
            if len(matches) == 1:
                paper_id = matches[0]
            elif len(matches) > 1:
                print(f"Multiple matches found: {matches}")
                print("Please specify the full paper ID")
                sys.exit(1)
            else:
                print(f"Paper ID '{args.paper_id}' not found in version history")
                print(f"Available: {list(history.keys())[:10]}...")
                sys.exit(1)
        
        md = convert_review_to_markdown(paper_id, history[paper_id])
        filepath = save_markdown(md, paper_id, args.output_dir)
        print(f"✓ Converted: {paper_id} -> {filepath}")


if __name__ == '__main__':
    main()
