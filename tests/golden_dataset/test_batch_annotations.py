"""
Tests for batch paper annotations under ``tests/golden_dataset/annotations/agent/``.

Locks in the TC-LR13 acceptance criteria:

1. At least 20 annotation files exist.
2. Each file is well-formed JSON with required top-level keys.
3. Annotations span at least two distinct research domains.
4. Every claim includes ``claim_text``, ``page_number``, and ``pillar_mapping``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ANNOTATIONS_DIR = Path(__file__).parent / "annotations" / "agent"
REGISTRY_PATH = Path(__file__).parent / "papers" / "paper_registry.json"

REQUIRED_TOP_LEVEL = ("paper_id", "annotator", "claims")
REQUIRED_CLAIM_FIELDS = ("claim_text", "page_number", "pillar_mapping")


def _load_annotation(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _domain_for(paper_id: str, registry: dict) -> str | None:
    for entry in registry.get("papers", []):
        if entry.get("paper_id") == paper_id:
            return entry.get("domain")
    return None


@pytest.fixture(scope="module")
def annotation_paths() -> list[Path]:
    return sorted(ANNOTATIONS_DIR.glob("*.json"))


@pytest.fixture(scope="module")
def registry() -> dict:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.unit
def test_minimum_annotation_count(annotation_paths: list[Path]) -> None:
    """TC-LR13 AC#1: at least 20 annotation JSON files exist."""
    assert len(annotation_paths) >= 20, (
        f"Expected >= 20 annotation files in {ANNOTATIONS_DIR}, got {len(annotation_paths)}"
    )


@pytest.mark.unit
def test_annotations_are_valid_json(annotation_paths: list[Path]) -> None:
    """TC-LR13 AC#2: every file parses and has the required top-level keys."""
    for path in annotation_paths:
        data = _load_annotation(path)
        assert isinstance(data, dict), f"{path.name}: top-level is not a JSON object"
        for key in REQUIRED_TOP_LEVEL:
            assert key in data, f"{path.name}: missing required top-level key '{key}'"
        claims = data["claims"]
        assert isinstance(claims, list) and claims, (
            f"{path.name}: 'claims' must be a non-empty list"
        )


@pytest.mark.unit
def test_annotations_span_multiple_domains(annotation_paths: list[Path], registry: dict) -> None:
    """TC-LR13 AC#3: annotations span at least two distinct research domains."""
    domains: Counter[str] = Counter()
    for path in annotation_paths:
        data = _load_annotation(path)
        # Prefer the domain recorded inside the annotation; fall back to the registry.
        domain = (
            (data.get("source") or {}).get("domain")
            or _domain_for(data["paper_id"], registry)
        )
        if domain:
            domains[domain] += 1
    distinct = [d for d, n in domains.items() if n > 0]
    assert len(distinct) >= 2, (
        f"Expected >= 2 distinct domains, got {len(distinct)}: {dict(domains)}"
    )


@pytest.mark.unit
def test_every_claim_has_required_fields(annotation_paths: list[Path]) -> None:
    """TC-LR13 AC#4: each claim has claim_text, page_number, pillar_mapping."""
    failures: list[str] = []
    for path in annotation_paths:
        data = _load_annotation(path)
        for i, claim in enumerate(data.get("claims", [])):
            for field in REQUIRED_CLAIM_FIELDS:
                if field not in claim:
                    failures.append(f"{path.name} claim #{i}: missing '{field}'")
            if not isinstance(claim.get("page_number"), int):
                failures.append(
                    f"{path.name} claim #{i}: 'page_number' must be int, got "
                    f"{type(claim.get('page_number')).__name__}"
                )
            pillars = claim.get("pillar_mapping")
            if not isinstance(pillars, list) or not pillars:
                failures.append(
                    f"{path.name} claim #{i}: 'pillar_mapping' must be a non-empty list"
                )
            text = claim.get("claim_text")
            if not isinstance(text, str) or len(text.strip()) < 10:
                failures.append(
                    f"{path.name} claim #{i}: 'claim_text' must be a meaningful string"
                )
    assert not failures, "Claim-field validation failures:\n  " + "\n  ".join(failures)
