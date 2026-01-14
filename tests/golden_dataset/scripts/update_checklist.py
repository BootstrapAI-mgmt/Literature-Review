#!/usr/bin/env python3
"""
Update annotation tracking and regenerate checklist based on actual annotation files.

Usage:
    python update_checklist.py              # Scan and update all
    python update_checklist.py --status     # Show current status only
    python update_checklist.py --paper NEURO-002 --mark human  # Mark specific checkbox
"""

import argparse
import json
import os
import time
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
GOLDEN_DATASET_DIR = SCRIPT_DIR.parent
ANNOTATIONS_DIR = GOLDEN_DATASET_DIR / "annotations"
TRACKING_FILE = GOLDEN_DATASET_DIR / "annotation_tracking.json"
REGISTRY_FILE = GOLDEN_DATASET_DIR / "papers" / "paper_registry.json"
CHECKLIST_FILE = GOLDEN_DATASET_DIR / "ANNOTATION_CHECKLIST.md"
DASHBOARD_FILE = GOLDEN_DATASET_DIR / "ANNOTATION_DASHBOARD.md"


def load_tracking():
    """Load annotation tracking JSON."""
    with open(TRACKING_FILE, 'r') as f:
        return json.load(f)


def save_tracking(tracking):
    """Save annotation tracking JSON."""
    tracking['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking, f, indent=2)


def load_registry():
    """Load paper registry JSON."""
    with open(REGISTRY_FILE, 'r') as f:
        return json.load(f)


def scan_annotations():
    """Scan annotation directories to find completed annotations."""
    completed = {
        'human': set(),
        'agent': set(),
        'golden': set(),
        'parity': set()
    }
    
    for ann_type in ['human', 'agent', 'golden', 'parity']:
        ann_dir = ANNOTATIONS_DIR / ann_type
        if ann_dir.exists():
            for f in ann_dir.glob('*.json'):
                # Extract paper_id from filename (e.g., NEURO-002.json or NEURO-002_parity.json)
                paper_id = f.stem.replace('_parity', '')
                completed[ann_type].add(paper_id)
    
    return completed


def update_tracking_from_scan(tracking, completed):
    """Update tracking based on scanned annotation files."""
    updated = 0
    
    for paper_id, data in tracking['papers'].items():
        cb = data['checkboxes']
        
        # Update checkboxes based on file existence
        if paper_id in completed['human'] and not cb['human_annotation']:
            cb['human_annotation'] = True
            updated += 1
        
        if paper_id in completed['agent'] and not cb['agent_annotation']:
            cb['agent_annotation'] = True
            updated += 1
        
        if paper_id in completed['parity'] and not cb['parity_check']:
            cb['parity_check'] = True
            updated += 1
        
        if paper_id in completed['golden'] and not cb['golden_finalized']:
            cb['golden_finalized'] = True
            updated += 1
    
    return updated


def mark_checkbox(tracking, paper_id, checkbox_type):
    """Manually mark a checkbox for a paper."""
    if paper_id not in tracking['papers']:
        print(f"Error: Paper {paper_id} not found in tracking")
        return False
    
    checkbox_map = {
        'human': 'human_annotation',
        'agent': 'agent_annotation',
        'parity': 'parity_check',
        'golden': 'golden_finalized'
    }
    
    if checkbox_type not in checkbox_map:
        print(f"Error: Invalid checkbox type '{checkbox_type}'. Use: human, agent, parity, golden")
        return False
    
    tracking['papers'][paper_id]['checkboxes'][checkbox_map[checkbox_type]] = True
    print(f"✓ Marked {checkbox_type} for {paper_id}")
    return True


def generate_checklist(tracking, registry):
    """Generate the ANNOTATION_CHECKLIST.md file."""
    
    # Group papers by domain
    domains = {}
    for paper in registry['papers']:
        paper_id = paper['paper_id']
        domain = paper['domain']
        if paper.get('pdf_acquired', False):
            if domain not in domains:
                domains[domain] = []
            
            track = tracking['papers'].get(paper_id, {})
            cb = track.get('checkboxes', {})
            
            domains[domain].append({
                'paper_id': paper_id,
                'title': paper.get('title', 'Unknown')[:60],
                'human': cb.get('human_annotation', False),
                'agent': cb.get('agent_annotation', False),
                'parity': cb.get('parity_check', False),
                'golden': cb.get('golden_finalized', False)
            })
    
    # Count totals
    total = sum(len(papers) for papers in domains.values())
    human_done = sum(1 for papers in domains.values() for p in papers if p['human'])
    agent_done = sum(1 for papers in domains.values() for p in papers if p['agent'])
    parity_done = sum(1 for papers in domains.values() for p in papers if p['parity'])
    golden_done = sum(1 for papers in domains.values() for p in papers if p['golden'])
    
    # Progress bars
    def progress_bar(done, total, width=20):
        filled = int(width * done / total) if total > 0 else 0
        return '█' * filled + '░' * (width - filled)
    
    checklist = f"""# Golden Dataset Annotation Checklist

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Total Papers:** {total} ready for annotation

---

## Progress Summary

| Stage | Complete | Remaining | Progress |
|-------|----------|-----------|----------|
| PDF Acquired | {total} | 0 | {progress_bar(total, total)} 100% |
| Human Annotation | {human_done} | {total - human_done} | {progress_bar(human_done, total)} {100*human_done//total if total else 0}% |
| Agent Annotation | {agent_done} | {total - agent_done} | {progress_bar(agent_done, total)} {100*agent_done//total if total else 0}% |
| Parity Check | {parity_done} | {total - parity_done} | {progress_bar(parity_done, total)} {100*parity_done//total if total else 0}% |
| Golden Finalized | {golden_done} | {total - golden_done} | {progress_bar(golden_done, total)} {100*golden_done//total if total else 0}% |

---

## How to Use This Checklist

1. **Human Annotation**: Read PDF, extract claims, identify gaps, save to `annotations/human/{{paper_id}}.json`
2. **Agent Annotation**: Run agent prompt on PDF, save to `annotations/agent/{{paper_id}}.json`
3. **Parity Check**: Compare human vs agent, save report to `annotations/parity/{{paper_id}}_parity.json`
4. **Golden Finalized**: After reconciliation, save final to `annotations/golden/{{paper_id}}.json`

Run `python scripts/update_checklist.py` to auto-detect completions and regenerate this file.

---

"""

    # Generate per-domain sections
    for domain in sorted(domains.keys()):
        papers = sorted(domains[domain], key=lambda x: x['paper_id'])
        
        h_done = sum(1 for p in papers if p['human'])
        a_done = sum(1 for p in papers if p['agent'])
        pa_done = sum(1 for p in papers if p['parity'])
        g_done = sum(1 for p in papers if p['golden'])
        
        checklist += f"""## {domain.replace('_', ' ').title()} ({len(papers)} papers)

| Status | Human | Agent | Parity | Golden |
|--------|-------|-------|--------|--------|
| Done | {h_done} | {a_done} | {pa_done} | {g_done} |
| Remaining | {len(papers)-h_done} | {len(papers)-a_done} | {len(papers)-pa_done} | {len(papers)-g_done} |

| Paper ID | Title | Human | Agent | Parity | Golden |
|----------|-------|:-----:|:-----:|:------:|:------:|
"""
        
        for p in papers:
            h = '✅' if p['human'] else '⬜'
            a = '✅' if p['agent'] else '⬜'
            pa = '✅' if p['parity'] else '⬜'
            g = '✅' if p['golden'] else '⬜'
            title = p['title'][:45] + '...' if len(p['title']) > 45 else p['title']
            checklist += f"| {p['paper_id']} | {title} | {h} | {a} | {pa} | {g} |\n"
        
        checklist += "\n---\n\n"

    # Quick reference
    checklist += """## Quick Reference

### Annotation Output Schema

```json
{
  "paper_id": "NEURO-002",
  "annotator": "human|agent",
  "timestamp": "2026-01-14T12:00:00Z",
  "claims": [
    {
      "claim_id": "C1",
      "text": "The system achieves 95% accuracy on MNIST",
      "type": "quantitative",
      "evidence_location": {"page": 5, "section": "Results"},
      "confidence": 0.9,
      "pillar_mapping": ["accuracy", "performance"]
    }
  ],
  "gaps": [
    {
      "gap_id": "G1",
      "description": "No comparison with baseline methods",
      "severity": "medium",
      "location": {"section": "Related Work"}
    }
  ],
  "non_extractable_items": [
    {
      "item_id": "NE1", 
      "reason": "Methodology described but not quantified"
    }
  ]
}
```

### Commands

```bash
# Scan annotations and update checklist
python scripts/update_checklist.py

# Show current status
python scripts/update_checklist.py --status

# Manually mark a paper
python scripts/update_checklist.py --paper NEURO-002 --mark human
python scripts/update_checklist.py --paper NEURO-002 --mark agent
python scripts/update_checklist.py --paper NEURO-002 --mark parity
python scripts/update_checklist.py --paper NEURO-002 --mark golden
```

### File Locations

| Type | Path |
|------|------|
| PDFs | `tests/golden_dataset/papers/{domain}/{paper_id}.pdf` |
| Human Annotations | `tests/golden_dataset/annotations/human/{paper_id}.json` |
| Agent Annotations | `tests/golden_dataset/annotations/agent/{paper_id}.json` |
| Golden Labels | `tests/golden_dataset/annotations/golden/{paper_id}.json` |
| Parity Reports | `tests/golden_dataset/annotations/parity/{paper_id}_parity.json` |
"""
    
    with open(CHECKLIST_FILE, 'w') as f:
        f.write(checklist)
    
    return {
        'total': total,
        'human': human_done,
        'agent': agent_done,
        'parity': parity_done,
        'golden': golden_done
    }


def show_status(tracking, registry):
    """Display current annotation status."""
    stats = generate_checklist(tracking, registry)
    
    print("\n" + "=" * 60)
    print("ANNOTATION STATUS")
    print("=" * 60)
    print(f"\n  Total papers:      {stats['total']}")
    print(f"  Human annotations: {stats['human']}/{stats['total']}")
    print(f"  Agent annotations: {stats['agent']}/{stats['total']}")
    print(f"  Parity checks:     {stats['parity']}/{stats['total']}")
    print(f"  Golden finalized:  {stats['golden']}/{stats['total']}")
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Update annotation tracking and checklist')
    parser.add_argument('--status', action='store_true', help='Show current status only')
    parser.add_argument('--paper', type=str, help='Paper ID to mark')
    parser.add_argument('--mark', type=str, choices=['human', 'agent', 'parity', 'golden'],
                       help='Checkbox type to mark')
    args = parser.parse_args()
    
    tracking = load_tracking()
    registry = load_registry()
    
    if args.paper and args.mark:
        # Manual mark mode
        if mark_checkbox(tracking, args.paper, args.mark):
            save_tracking(tracking)
            generate_checklist(tracking, registry)
            print("✓ Updated tracking and regenerated checklist")
    elif args.status:
        # Status only mode
        show_status(tracking, registry)
    else:
        # Full scan and update mode
        print("Scanning annotation directories...")
        completed = scan_annotations()
        
        print(f"  Found {len(completed['human'])} human annotations")
        print(f"  Found {len(completed['agent'])} agent annotations")
        print(f"  Found {len(completed['parity'])} parity reports")
        print(f"  Found {len(completed['golden'])} golden annotations")
        
        updated = update_tracking_from_scan(tracking, completed)
        
        if updated > 0:
            save_tracking(tracking)
            print(f"\n✓ Updated {updated} checkbox(es) in tracking")
        else:
            print("\n  No new annotations detected")
        
        stats = generate_checklist(tracking, registry)
        print(f"\n✓ Regenerated ANNOTATION_CHECKLIST.md")
        print(f"  Progress: {stats['golden']}/{stats['total']} papers finalized")


if __name__ == '__main__':
    main()
