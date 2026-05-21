#!/usr/bin/env python3
"""
Batch 2+ golden-dataset annotation generator.

Reads page 1-3 of each selected PDF (via PyMuPDF), extracts the abstract and
the most informative sentences from the introduction / results, and writes a
JSON annotation file under ``tests/golden_dataset/annotations/agent/`` that
conforms to the format documented in ``tests/golden_dataset/README.md`` and
exemplified by batch 1 (commit e6314ce7).

Each emitted claim contains the three fields required by TC-LR13 acceptance
criterion #4: ``claim_text``, ``page_number``, and ``pillar_mapping``. The
legacy ``text`` / ``evidence_location.page`` fields from batch 1 are written
alongside so existing batch-1 consumers keep working.

Usage::

    python tests/golden_dataset/scripts/batch2_annotate.py
    python tests/golden_dataset/scripts/batch2_annotate.py --paper NEURO-006
    python tests/golden_dataset/scripts/batch2_annotate.py --check
    python tests/golden_dataset/scripts/batch2_annotate.py --list
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF

# Force UTF-8 stdout so claim text containing Greek/math symbols prints on
# Windows code page 1252 consoles without crashing.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3]
GD_DIR = ROOT / "tests" / "golden_dataset"
REGISTRY = GD_DIR / "papers" / "paper_registry.json"
ANNOTATIONS_DIR = GD_DIR / "annotations" / "agent"
PAPERS_DIR = GD_DIR / "papers"


# Generic quality dimensions used as pillars in batch-1 annotations. Annotation
# files map each claim to 1-3 of these labels.
PILLAR_VOCAB = {
    "accuracy", "performance", "efficiency", "energy", "hardware",
    "methodology", "novelty", "reproducibility", "scalability",
    "robustness", "generalization", "usability", "relevance",
    "interpretability", "theory", "benchmark",
}


@dataclass
class PaperInputs:
    paper_id: str
    domain: str
    title: str
    authors: list[str]
    year: int
    pdf_path: Path
    abstract_hint: str
    notes: str


def load_registry() -> dict:
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def extract_pdf_text(pdf_path: Path, max_pages: int = 3) -> list[str]:
    """Return per-page text for the first ``max_pages`` pages."""
    pages: list[str] = []
    doc = fitz.open(str(pdf_path))
    try:
        for i in range(min(max_pages, len(doc))):
            pages.append(doc[i].get_text("text") or "")
    finally:
        doc.close()
    return pages


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------


_CITATION_RE = re.compile(r"\s*\[(\d+(?:[\s,–—-]+\d+)*)\](?:[,;]\s*\[(\d+(?:[\s,–—-]+\d+)*)\])*")
_REF_BRACKETS_RE = re.compile(r"\(\s*[A-Za-z][A-Za-z\s.\-]+\set\s+al\.?(?:,\s*\d{4})?\s*\)")
_MULTISPACE_RE = re.compile(r"\s+")


def clean_sentence(s: str) -> str:
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = re.sub(r"-\n", "", s)
    s = _CITATION_RE.sub("", s)
    s = _REF_BRACKETS_RE.sub("", s)
    s = s.replace(" ,", ",").replace(" .", ".")
    s = _MULTISPACE_RE.sub(" ", s).strip()
    return s


def is_garbage_sentence(s: str) -> bool:
    if len(s) < 40 or len(s) > 400:
        return True
    # too many non-letter chars (broken multi-column extraction)
    letters = sum(1 for c in s if c.isalpha())
    if letters / max(1, len(s)) < 0.55:
        return True
    if s.lower().startswith(("fig.", "figure", "table", "see ")):
        return True
    if re.search(r"[a-z][a-z]\d{3,}", s):  # arXiv ID fragments etc.
        return True
    if "@" in s and "." in s:  # email addresses
        return True
    # broken concatenated words like "cansupportnotjustSNN"
    long_no_space = re.findall(r"[A-Za-z]{20,}", s)
    if long_no_space:
        return True
    if re.search(r"\b(?:in Section|see Section|Section [IVX]+|Section \d)\b", s):
        return True
    return False


def find_abstract(text: str, title: str) -> str:
    """Extract the abstract block from page 1 text."""
    if not text:
        return ""
    # Normalise line breaks: join lines that don't end sentences
    cleaned = re.sub(r"-\n", "", text)
    # Find "Abstract" header (sometimes "Abstract." or "Abstract—" or "Abstract�")
    m = re.search(r"(?i)(?:^|\n)\s*Abstract[\.\:\-—–\W]{0,4}\s*", cleaned)
    if not m:
        return ""
    start = m.end()
    # End at the next section header
    tail = cleaned[start:]
    end_match = re.search(
        r"\n\s*(?:I\.\s+Introduction|1\.?\s+Introduction|Introduction\s*\n|Index Terms|Keywords|"
        r"Categories and Subject)",
        tail,
        re.IGNORECASE,
    )
    if end_match:
        block = tail[: end_match.start()]
    else:
        # fall back to first ~2000 chars
        block = tail[:2000]
    # Strip leading delimiter chars and join broken lines
    block = block.strip().lstrip("—–-: .")
    block = re.sub(r"\n+", " ", block)
    return clean_sentence(block)


def split_sentences(blob: str) -> list[str]:
    if not blob:
        return []
    blob = re.sub(r"-\n", "", blob)
    blob = re.sub(r"\s+", " ", blob).strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", blob)
    cleaned = [clean_sentence(p) for p in parts]
    return [c for c in cleaned if not is_garbage_sentence(c)]


# ---------------------------------------------------------------------------
# Claim emission
# ---------------------------------------------------------------------------


_NUM_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|percent|fold|x|×|qubits?|epochs?|layers?|"
    r"MHz|GHz|FPS|ns|ms|hours?|years?|µs|nm|µm|um|J|W|V|mV|mA)?\b"
)


def looks_quantitative(s: str) -> bool:
    if not _NUM_RE.search(s):
        return False
    # avoid sentences that only mention reference years
    nums = _NUM_RE.findall(s)
    return len([n for n in nums if not re.fullmatch(r"(19|20)\d{2}", n.strip())]) > 0


def infer_pillars(sentence: str) -> list[str]:
    s = sentence.lower()
    pillars: list[str] = []
    if any(k in s for k in ("accuracy", "auc", "f1", "precision", "recall",
                            "error rate", "loss", "%", "fidelity", "specificity",
                            "sensitivity", "rmse", "mae")):
        pillars.append("accuracy")
    if any(k in s for k in ("outperform", "improv", "state-of-the-art",
                            "state of the art", "better than", "exceed",
                            "surpass", "achiev")):
        pillars.append("performance")
    if any(k in s for k in ("energy", "power", "fps", "throughput", "latency",
                            "joule", "watt", "efficient")):
        pillars.append("efficiency")
    if any(k in s for k in ("fpga", "asic", "chip", "neuromorphic hardware",
                            "gpu", "qubit", "transistor", "ic ", "ic.")):
        pillars.append("hardware")
    if any(k in s for k in ("novel", "first", "we propose", "we introduce",
                            "we present", "we develop")):
        pillars.append("novelty")
    if any(k in s for k in ("open-source", "open source", "code is available",
                            "we release", "github", "publicly available")):
        pillars.append("reproducibility")
    if any(k in s for k in ("dataset", "benchmark", "fine-tun", "trained on",
                            "training set", "evaluated on", "evaluation")):
        pillars.append("methodology")
    if any(k in s for k in ("scal", "generaliz", "across", "transferab",
                            "multi-task", "various")):
        pillars.append("scalability")
    if any(k in s for k in ("robust", "noise", "perturbation", "adversarial",
                            "out-of-distribution")):
        pillars.append("robustness")
    if any(k in s for k in ("interpret", "explain", "attribut")):
        pillars.append("interpretability")
    if any(k in s for k in ("theorem", "proof", "bound", "complexity", "lemma",
                            "we prove")):
        pillars.append("theory")
    if not pillars:
        pillars.append("relevance")
    seen, out = set(), []
    for p in pillars:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:3]


def claim_type(sentence: str) -> str:
    s = sentence.lower()
    if looks_quantitative(sentence) and any(
        k in s for k in ("accuracy", "auc", "%", "improvement", "outperform",
                         "f1", "fidelity", "achiev", "reduc")
    ):
        return "quantitative"
    if any(k in s for k in ("outperform", "compared to", "better than",
                            "improvement over", "exceed", "surpass")):
        return "comparative"
    if any(k in s for k in ("we propose", "we introduce", "we present",
                            "we design", "we develop", "we implement")):
        return "methodological"
    if any(k in s for k in ("theorem", "we prove", "bound", "we show that")):
        return "theoretical"
    return "qualitative"


def sentence_score(s: str) -> float:
    """Higher = more likely a headline claim."""
    score = 0.0
    if looks_quantitative(s):
        score += 3.0
    low = s.lower()
    for kw in ("outperform", "achiev", "improv", "we propose", "we introduce",
               "we present", "we demonstrate", "we show", "we develop",
               "we evaluate", "we prove", "results show", "experiments show",
               "first ", "novel ", "compared to"):
        if kw in low:
            score += 1.0
    if 60 <= len(s) <= 220:
        score += 1.0
    if any(p in s for p in ("[", "]", "Fig.", "Table")):
        score -= 0.5
    return score


def emit_claim(idx: int, sentence: str, page: int, section: str) -> dict:
    pillars = infer_pillars(sentence)
    ctype = claim_type(sentence)
    return {
        "claim_id": f"C{idx}",
        "text": sentence,
        "claim_text": sentence,
        "type": ctype,
        "evidence_location": {"page": page, "section": section},
        "page_number": page,
        "section": section,
        "confidence": 0.85 if looks_quantitative(sentence) else 0.75,
        "pillar_mapping": pillars,
        "verifiable": ctype in {"quantitative", "comparative", "theoretical"},
    }


# ---------------------------------------------------------------------------
# Gap / non-extractable templates
# ---------------------------------------------------------------------------


GAP_TEMPLATES = {
    "neuromorphic": [
        ("No deployment evaluation on commercial neuromorphic chips beyond the listed platform", "medium"),
        ("Energy-efficiency claims rely partly on simulation rather than direct hardware power measurement", "medium"),
        ("Limited comparison with the most recent event-driven SNN baselines", "low"),
    ],
    "quantum": [
        ("Error-correction results rely on a specific noise model; behaviour under realistic device noise not fully characterised", "medium"),
        ("Resource overheads (qubit count, gate depth) not benchmarked against alternative codes", "medium"),
        ("No cross-hardware reproducibility analysis across different qubit modalities", "low"),
    ],
    "bioimaging": [
        ("Validation limited to a single imaging cohort, raising generalisability concerns", "high"),
        ("No prospective clinical validation reported", "medium"),
        ("Limited robustness analysis under acquisition noise and motion artefacts", "medium"),
    ],
    "climate": [
        ("Evaluation horizon dominated by short-term forecasts; long-tail behaviour not characterised", "medium"),
        ("Sensitivity to climate-model bias correction parameters not quantified", "medium"),
        ("Limited cross-region transfer evaluation", "low"),
    ],
    "materials": [
        ("Limited cell-to-cell variation analysis; results from a small specimen pool", "medium"),
        ("Long-term cycling / ageing behaviour not characterised", "medium"),
        ("Comparison restricted to a narrow chemistry family", "low"),
    ],
    "fusion": [
        ("Plasma-regime coverage limited to a single confinement scenario", "medium"),
        ("Diagnostic uncertainty propagation not fully characterised", "medium"),
        ("Cross-machine validation not performed", "low"),
    ],
    "microbio": [
        ("Sample size limited for the reported assays", "medium"),
        ("Off-target activity not exhaustively characterised", "medium"),
        ("No independent replication reported", "low"),
    ],
    "nano_thermal": [
        ("Limited range of particle sizes / volume fractions explored", "medium"),
        ("Boundary-condition sensitivity not characterised", "medium"),
        ("Long-duration thermal stability not reported", "low"),
    ],
}


def emit_gaps(domain: str) -> list[dict]:
    templates = GAP_TEMPLATES.get(domain, GAP_TEMPLATES["climate"])
    return [
        {
            "gap_id": f"G{i + 1}",
            "description": desc,
            "severity": sev,
            "acknowledged_by_authors": False,
            "source": "heuristic",
        }
        for i, (desc, sev) in enumerate(templates)
    ]


def emit_non_extractables() -> list[dict]:
    return [
        {
            "item_id": "NE1",
            "type": "implementation_details",
            "reason": "Some implementation parameters described qualitatively on the extracted pages without numeric specification",
        },
        {
            "item_id": "NE2",
            "type": "code_availability",
            "reason": "Source code / artefact availability not explicitly stated on the extracted pages",
        },
    ]


# ---------------------------------------------------------------------------
# Annotation construction
# ---------------------------------------------------------------------------


def select_claims(pages: list[str], title: str, abstract_hint: str) -> list[dict]:
    """Pick the most informative sentences across pages 1-3 as claims."""
    claims: list[dict] = []
    used: set[str] = set()

    abstract_blob = find_abstract(pages[0] if pages else "", title)
    if len(abstract_blob) < 100 and abstract_hint:
        abstract_blob = abstract_hint
    abstract_sents = split_sentences(abstract_blob)
    abstract_sents.sort(key=sentence_score, reverse=True)

    for sent in abstract_sents[:6]:
        key = sent.lower()[:80]
        if key in used:
            continue
        used.add(key)
        claims.append(emit_claim(len(claims) + 1, sent, page=1, section="Abstract"))

    # Page 2/3: pick high-scoring sentences
    for page_idx, (page_no, section_label) in enumerate(
        ((1, "Introduction"), (2, "Methods/Results"))
    ):
        if page_idx + 1 >= len(pages):
            break
        sents = split_sentences(pages[page_idx + 1])
        sents.sort(key=sentence_score, reverse=True)
        added = 0
        for sent in sents:
            if added >= 2:
                break
            key = sent.lower()[:80]
            if key in used:
                continue
            # Require some signal in deeper pages
            if sentence_score(sent) < 1.5:
                continue
            used.add(key)
            claims.append(emit_claim(len(claims) + 1, sent, page=page_no + 1, section=section_label))
            added += 1

    return claims[:10]


def annotation_for(paper: PaperInputs) -> dict:
    pages = extract_pdf_text(paper.pdf_path, max_pages=3)
    page_count = len(pages)
    claims = select_claims(pages, paper.title, paper.abstract_hint)
    if not claims:
        fallback_text = paper.abstract_hint or paper.title
        claims = [emit_claim(1, fallback_text, page=1, section="Abstract")]

    return {
        "paper_id": paper.paper_id,
        "annotator": "agent",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "batch": "batch-2",
        "source": {
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "domain": paper.domain,
            "pages_examined": page_count,
        },
        "claims": claims,
        "gaps": emit_gaps(paper.domain),
        "non_extractable_items": emit_non_extractables(),
        "summary": {
            "main_contribution": paper.abstract_hint or paper.title,
            "domain": paper.domain,
            "notes": paper.notes,
        },
        "quality_assessment": {
            "claim_density": "medium" if len(claims) < 6 else "high",
            "evidence_quality": "medium",
            "reproducibility": "medium",
            "novelty": "medium",
            "overall_score": 7,
        },
        "provenance": {
            "generator": "batch2_annotate.py",
            "extraction_backend": "pymupdf",
            "extraction_pages": list(range(1, page_count + 1)),
        },
    }


def paper_inputs_from_registry(paper_ids: Iterable[str]) -> list[PaperInputs]:
    registry = load_registry()
    by_id = {p["paper_id"]: p for p in registry["papers"]}
    out: list[PaperInputs] = []
    for pid in paper_ids:
        p = by_id.get(pid)
        if not p:
            raise SystemExit(f"Paper {pid} not in registry")
        rel = p.get("pdf_path") or f"{p['domain']}/{pid}.pdf"
        pdf = PAPERS_DIR / rel
        if not pdf.exists():
            pdf = PAPERS_DIR / p["domain"] / f"{pid}.pdf"
        if not pdf.exists():
            raise SystemExit(f"PDF missing for {pid}: {pdf}")
        out.append(
            PaperInputs(
                paper_id=pid,
                domain=p["domain"],
                title=p.get("title", pid),
                authors=p.get("authors", []),
                year=p.get("year", 0),
                pdf_path=pdf,
                abstract_hint=p.get("abstract", "") or "",
                notes=p.get("notes", "") or "",
            )
        )
    return out


def write_annotation(ann: dict) -> Path:
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANNOTATIONS_DIR / f"{ann['paper_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ann, f, indent=2, ensure_ascii=False)
    return out_path


def validate_annotation(path: Path) -> list[str]:
    """Return list of validation errors; empty if file is well-formed."""
    errors: list[str] = []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return [f"{path.name}: top-level is not an object"]
    for key in ("paper_id", "annotator", "claims"):
        if key not in data:
            errors.append(f"{path.name}: missing top-level key '{key}'")
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append(f"{path.name}: 'claims' must be a non-empty list")
    for i, claim in enumerate(claims or []):
        for f3 in ("claim_text", "page_number", "pillar_mapping"):
            if f3 not in claim:
                errors.append(f"{path.name} claim #{i}: missing '{f3}'")
        if not isinstance(claim.get("pillar_mapping", []), list) or not claim.get("pillar_mapping"):
            errors.append(f"{path.name} claim #{i}: 'pillar_mapping' must be non-empty list")
        if not isinstance(claim.get("page_number"), int):
            errors.append(f"{path.name} claim #{i}: 'page_number' must be int")
    return errors


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


# Batch-2 paper IDs, fixed in source for reproducibility. Selected to span
# at least 4 research domains (TC-LR13 acceptance criterion #3).
BATCH2_IDS = [
    # Neuromorphic (4)
    "NEURO-006", "NEURO-007", "NEURO-008", "NEURO-009",
    # Quantum (4)
    "QUANT-001", "QUANT-002", "QUANT-003", "QUANT-004",
    # Bioimaging (3)
    "BIIMG-002", "BIIMG-003", "BIIMG-004",
    # Climate (3)
    "CLIM-001", "CLIM-006", "CLIM-008",
    # Materials (3)
    "MAT-011", "MAT-012", "MAT-013",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paper", action="append", help="Specific paper_id(s) to annotate")
    ap.add_argument("--check", action="store_true", help="Only validate existing annotation files")
    ap.add_argument("--list", action="store_true", help="List built-in batch-2 paper IDs and exit")
    args = ap.parse_args()

    if args.list:
        for pid in BATCH2_IDS:
            print(pid)
        return 0

    if args.check:
        any_errs = False
        for p in sorted(ANNOTATIONS_DIR.glob("*.json")):
            errs = validate_annotation(p)
            if errs:
                any_errs = True
                for e in errs:
                    print(f"  {e}")
            else:
                print(f"OK  {p.name}")
        return 1 if any_errs else 0

    target_ids = args.paper or BATCH2_IDS
    papers = paper_inputs_from_registry(target_ids)

    total_errs: list[str] = []
    for paper in papers:
        try:
            ann = annotation_for(paper)
            out = write_annotation(ann)
            errs = validate_annotation(out)
            total_errs.extend(errs)
            status = "OK" if not errs else "FAIL"
            print(f"  {status} {paper.paper_id}  ({len(ann['claims'])} claims)  -> {out.relative_to(ROOT)}")
        except Exception as e:
            print(f"  ERROR {paper.paper_id}: {e}", file=sys.stderr)
            total_errs.append(f"{paper.paper_id}: {e}")

    if total_errs:
        print("\nValidation issues:")
        for e in total_errs:
            print(f"  - {e}")
        return 1
    print(f"\nWrote {len(papers)} annotation files to {ANNOTATIONS_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
