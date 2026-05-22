"""Reconcile dissertation citation keys against PDFs in the data directories.

For each citation key in MISSING_KEYS, scan the configured PDF roots, run
pymupdf metadata extraction, score every PDF against the key, and emit the
best candidates to dissertation_pdf_mapping.json.

Scope constraints (do not violate):
  - This script produces a filename -> paper mapping ONLY.
  - It must NOT bridge review_version_history.json excerpts to the
    dissertation's citation log. The dissertation's own pymupdf ->
    citation_log_gate pipeline is the sole verbatim chain.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Make repo root importable when run from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 8 missing dissertation citation keys (author lastname + year)
MISSING_KEYS: Dict[str, Dict[str, object]] = {
    "debole2025":        {"authors": ["debole", "de bole"],         "year": 2025},
    "khalighrazavi2014": {"authors": ["khaligh-razavi", "khaligh razavi", "khalighrazavi"], "year": 2014},
    "appuswamy2024":     {"authors": ["appuswamy"],                  "year": 2024},
    "friston2005":       {"authors": ["friston"],                    "year": 2005},
    "kar2019":           {"authors": ["kar"],                        "year": 2019},
    "kubilius2019":      {"authors": ["kubilius"],                   "year": 2019},
    "parisi2019":        {"authors": ["parisi"],                     "year": 2019},
    "huys2016":          {"authors": ["huys"],                       "year": 2016},
}


@dataclass
class Candidate:
    path: str
    score: float
    title: str = ""
    authors: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    year: Optional[int] = None
    page_count: int = 0
    reasons: List[str] = field(default_factory=list)


def normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def score_candidate(
    key: str,
    spec: Dict[str, object],
    metadata: Dict,
    filename: str,
) -> Tuple[float, List[str]]:
    """Score how well a PDF's metadata matches a citation key.

    Heuristics (additive):
      - authors substring match: +3.0 each
      - year exact match:        +2.0
      - year within ±1:          +0.75
      - filename substring of key author + year: +1.5
      - title contains "year" string: +0.25
    """
    score = 0.0
    reasons: List[str] = []

    md_authors = [normalise(a) for a in metadata.get("authors", []) if a]
    md_title = normalise(metadata.get("title", "") or "")
    md_year = metadata.get("year")
    fname_norm = normalise(filename)

    for author_variant in spec["authors"]:  # type: ignore[index]
        a_norm = normalise(author_variant)
        if any(a_norm in a for a in md_authors):
            score += 3.0
            reasons.append(f"author '{author_variant}' in metadata")
        elif a_norm in md_title:
            score += 1.5
            reasons.append(f"author '{author_variant}' in title")
        if a_norm in fname_norm:
            score += 1.0
            reasons.append(f"author '{author_variant}' in filename")

    target_year = spec["year"]  # type: ignore[index]
    if md_year is not None and isinstance(target_year, int):
        if md_year == target_year:
            score += 2.0
            reasons.append(f"year {md_year} exact match")
        elif abs(md_year - target_year) == 1:
            score += 0.75
            reasons.append(f"year {md_year} within ±1 of {target_year}")

    # Filename hint: author+year together
    for author_variant in spec["authors"]:  # type: ignore[index]
        token = f"{normalise(author_variant)}{spec['year']}"  # type: ignore[index]
        if token.replace(" ", "") in fname_norm.replace(" ", ""):
            score += 1.5
            reasons.append(f"filename contains '{author_variant}{spec['year']}'")
            break

    return score, reasons


def scan(roots: List[Path], top_n: int = 5, key_filter: Optional[str] = None) -> Dict:
    try:
        from literature_review.metadata_extractor import EnhancedMetadataExtractor
    except ImportError:
        print("ERROR: cannot import literature_review.metadata_extractor", file=sys.stderr)
        raise

    md_extractor = EnhancedMetadataExtractor()

    pdfs: List[Path] = []
    for root in roots:
        if not root.exists():
            print(f"WARNING: scan root does not exist: {root}", file=sys.stderr)
            continue
        pdfs.extend(root.rglob("*.pdf"))
        pdfs.extend(root.rglob("*.PDF"))
    pdfs = sorted(set(pdfs))
    print(f"Scanning {len(pdfs)} PDFs across {len(roots)} roots", file=sys.stderr)

    keys_to_match = {key_filter: MISSING_KEYS[key_filter]} if key_filter else MISSING_KEYS
    matches: Dict[str, List[Candidate]] = {k: [] for k in keys_to_match}

    for i, pdf in enumerate(pdfs, 1):
        if i % 100 == 0:
            print(f"  [{i}/{len(pdfs)}] scanning...", file=sys.stderr)
        try:
            md = md_extractor.extract_metadata(str(pdf))
        except Exception as e:
            print(f"  metadata extract failed for {pdf.name}: {e}", file=sys.stderr)
            continue

        for key, spec in keys_to_match.items():
            score, reasons = score_candidate(key, spec, md, pdf.name)
            if score >= 2.0:  # threshold to consider as candidate
                matches[key].append(
                    Candidate(
                        path=str(pdf),
                        score=score,
                        title=md.get("title", "") or "",
                        authors=md.get("authors", []) or [],
                        doi=md.get("doi"),
                        year=md.get("year"),
                        page_count=md.get("page_count", 0) or 0,
                        reasons=reasons,
                    )
                )

    # Sort and truncate
    out: Dict[str, object] = {
        "_scope_note": (
            "filename -> paper mapping only. NOT a verbatim/citation-chain source. "
            "Dissertation citation log verification is owned by the dissertation's "
            "own pymupdf -> citation_log_gate pipeline."
        ),
        "scan_roots": [str(r) for r in roots],
        "total_pdfs_scanned": len(pdfs),
        "candidates": {},
    }
    for key, cands in matches.items():
        cands.sort(key=lambda c: c.score, reverse=True)
        out["candidates"][key] = [asdict(c) for c in cands[:top_n]]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        action="append",
        default=None,
        help="PDF scan root (can repeat). Defaults to main-clone data/raw and worktree data/raw.",
    )
    parser.add_argument("--top-n", type=int, default=5, help="Top candidates per key")
    parser.add_argument("--key", default=None, help="Limit to a single citation key")
    parser.add_argument(
        "--output",
        default="dissertation_pdf_mapping.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    if args.data_root:
        roots = [Path(r) for r in args.data_root]
    else:
        roots = [
            Path("data/raw"),
            Path("data/processed"),
            Path("C:/Users/jpcol/Documents/Literature-Review/Literature-Review/data/raw"),
            Path("C:/Users/jpcol/Documents/Literature-Review/Literature-Review/data/processed"),
        ]

    mapping = scan(roots, top_n=args.top_n, key_filter=args.key)
    Path(args.output).write_text(json.dumps(mapping, indent=2, default=str), encoding="utf-8")
    print(f"Wrote mapping to {args.output}")

    # Console summary
    for key, cands in mapping["candidates"].items():
        if not cands:
            print(f"  [{key}] NO CANDIDATES (score >= 2.0)")
        else:
            top = cands[0]
            print(
                f"  [{key}] best: score={top['score']:.1f}  "
                f"year={top['year']}  pages={top['page_count']}"
            )
            print(f"    path:   {top['path']}")
            print(f"    title:  {(top['title'] or '')[:80]}")
            print(f"    doi:    {top['doi']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
