# Task Card: Paper Population for Golden Dataset

**Task ID:** VM-W1.5-1B  
**Wave:** 1.5 (Golden Dataset Enhancement)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W1.5-1  
**Blocks:** VM-W1.5-2  
**Validation IDs:** QB-01, QB-02 (data population)

---

## Objective

Populate the paper registry with 80+ open access papers from 8 scientific domains using the infrastructure created in VM-W1.5-1. This bridges the gap between infrastructure (CLI tooling) and annotation (VM-W1.5-2) by providing the actual papers to annotate.

## Background

VM-W1.5-1 delivered:
- ✅ Enhanced `source_papers.py` CLI with `add`, `validate`, `report`, `download` commands
- ✅ Paper registry schema with new fields (`source_type`, `source_id`, `claim_count_estimate`, etc.)
- ✅ SOURCING.md guides for all 8 domains
- ✅ Test suite for registry validation

VM-W1.5-2 expects:
- 80+ papers already present in registry
- PDFs downloaded to domain directories
- Papers ready for claim annotation

**This task card fills that gap.**

---

## Success Criteria

- [ ] 10+ papers sourced per domain (80+ total)
- [ ] All papers registered via `source_papers.py add` command
- [ ] All papers have open access license (verifiable)
- [ ] Each paper has ≥5 estimated quantitative claims
- [ ] `source_papers.py validate` passes with no errors
- [ ] PDFs downloaded for all papers (optional: can be deferred)
- [ ] Sourcing report generated showing 80/80 target met

---

## Domain Targets

| Domain | Prefix | Target | Primary Sources |
|--------|--------|--------|-----------------|
| Neuromorphic Computing | NEURO | 10 | arXiv cs.NE |
| Nanoparticle Heat Transfer | NANO | 10 | arXiv cond-mat.mes-hall |
| Fusion Energy | FUSION | 10 | arXiv physics.plasm-ph |
| Quantum Computing | QUANT | 10 | arXiv quant-ph |
| Microbiology & Genomics | MICRO | 10 | PubMed Central, PLOS |
| Climate Science | CLIM | 10 | arXiv physics.ao-ph |
| Materials Science | MATL | 10 | arXiv cond-mat.mtrl-sci |
| Biomedical Imaging | BIIMG | 10 | arXiv eess.IV, PMC |

---

## Implementation

### Paper Selection Criteria

Each paper must meet:
1. **Open Access** - CC-BY, CC0, arXiv, PMC-OA, or similar
2. **Quantitative Claims** - ≥5 measurable assertions (performance, accuracy, efficiency)
3. **Methods Present** - Reproducible methodology section
4. **Recency** - Prefer 2020-2025 publications
5. **Domain Match** - Clearly fits target domain

### CLI Commands

```bash
# Check current progress
python tests/golden_dataset/scripts/source_papers.py status

# Add a paper (arXiv)
python tests/golden_dataset/scripts/source_papers.py add \
    --domain neuromorphic \
    --arxiv-id 2301.12345 \
    --title "Spiking Neural Networks for Edge Computing" \
    --authors "Smith, J.; Zhang, L." \
    --year 2023 \
    --claims 8 \
    --download

# Add a paper (DOI)
python tests/golden_dataset/scripts/source_papers.py add \
    --domain microbio \
    --doi "10.1371/journal.pgen.1009876" \
    --title "CRISPR-Cas9 Efficiency in Human Cell Lines" \
    --year 2024 \
    --claims 6

# Validate registry
python tests/golden_dataset/scripts/source_papers.py validate

# Generate report
python tests/golden_dataset/scripts/source_papers.py report > paper_sourcing_report.md
```

### Recommended Papers by Domain

Use the SOURCING.md guides in each domain directory for search terms and source recommendations:
- `tests/golden_dataset/papers/neuromorphic/SOURCING.md`
- `tests/golden_dataset/papers/quantum/SOURCING.md`
- etc.

Additionally, consult the `RECOMMENDED_PAPERS` dictionary in `source_papers.py` for curated suggestions.

---

## Execution Plan

### Phase 1: High-Priority Domains (3 hours)
Source 10 papers each for domains with clearest arXiv coverage:
1. **Neuromorphic Computing** (arXiv cs.NE) - Benchmark domain
2. **Quantum Computing** (arXiv quant-ph) - Well-established open access
3. **Materials Science** (arXiv cond-mat.mtrl-sci) - High volume

### Phase 2: Physics Domains (2.5 hours)
Source 10 papers each:
4. **Fusion Energy** (arXiv physics.plasm-ph)
5. **Nanoparticle Heat Transfer** (arXiv cond-mat.mes-hall)
6. **Climate Science** (arXiv physics.ao-ph)

### Phase 3: Life Sciences & Imaging (2.5 hours)
Source 10 papers each:
7. **Microbiology & Genomics** (PMC, PLOS, eLife)
8. **Biomedical Imaging** (arXiv eess.IV, PMC)

---

## Paper Discovery Strategy

### arXiv Search (Most Domains)

```
https://arxiv.org/search/?searchtype=all&query={domain_terms}&start=0
```

Filter by:
- License: Shows arXiv license (perpetual, open access)
- Date: 2020-2025
- Sort: Relevance or Recent

### PubMed Central (Life Sciences)

```
https://www.ncbi.nlm.nih.gov/pmc/?term={search_terms}+open+access
```

Filter by:
- Open Access subset
- Full text available
- Recent 5 years

### Google Scholar (Fallback)

Search with `filetype:pdf` and check license on paper.

---

## Validation Checkpoints

### After Each Domain (10 papers)
```bash
python tests/golden_dataset/scripts/source_papers.py status
# Should show domain at 10/10
```

### After All Domains (80 papers)
```bash
python tests/golden_dataset/scripts/source_papers.py validate
# Should pass with no errors

python tests/golden_dataset/scripts/source_papers.py report
# Should show 80/80 papers, all domains ✓
```

### Final Test Suite
```bash
python -m pytest tests/golden_dataset/test_paper_sourcing.py -v
# All 21 tests should pass (no skips for content tests)
```

---

## Acceptance Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Total Papers | 80+ | `source_papers.py status` |
| Per-Domain Minimum | 10 each | All domains show ✓ |
| Open Access Rate | 100% | License field populated |
| Claim Estimates | ≥5 per paper | `claim_count_estimate` field |
| Registry Valid | Yes | `validate` command passes |
| Tests Pass | 21/21 | pytest with no skips |

---

## Output Artifacts

1. **Updated `paper_registry.json`** - 80+ paper entries
2. **PDFs in domain directories** - Optional, can be downloaded later
3. **Sourcing report** - Markdown summary of all papers
4. **Passing test suite** - All paper sourcing tests green

---

## Integration with VM-W1.5-2

Once this task is complete, VM-W1.5-2 (Paper Annotation) can proceed:
- Papers are registered and discoverable
- PDFs are available for reading
- Claim estimates guide annotation effort
- Registry tracks annotation status (`not_started` → `in_progress` → `complete`)

---

## Notes

- **Bulk sourcing**: For efficiency, consider scripting arXiv API queries for initial paper discovery
- **Quality over quantity**: Better to have 80 good papers than 100 mediocre ones
- **License verification**: Always confirm open access before adding
- **PDF download**: Can be deferred if registry population is priority
- **Copilot agent**: This task is suitable for automated sourcing with human review

---

## Example Session

```bash
# Start with neuromorphic domain
$ python source_papers.py add --domain neuromorphic \
    --arxiv-id 2301.05785 \
    --title "Neuromorphic Computing: From Devices to Systems" \
    --year 2023 --claims 7 --download
Added paper: NEURO-001 - Neuromorphic Computing: From Devices to Systems...

$ python source_papers.py add --domain neuromorphic \
    --arxiv-id 2304.08042 \
    --title "Event-Driven Spiking Neural Network Training" \
    --year 2023 --claims 6
Added paper: NEURO-002 - Event-Driven Spiking Neural Network Training...

# ... continue until 10 papers per domain

$ python source_papers.py status
=== Paper Sourcing Status ===
Total Papers: 80/80

By Domain:
  ✓ neuromorphic: 10/10
  ✓ nano_thermal: 10/10
  ✓ fusion: 10/10
  ✓ quantum: 10/10
  ✓ microbio: 10/10
  ✓ climate: 10/10
  ✓ materials: 10/10
  ✓ bioimaging: 10/10
```
