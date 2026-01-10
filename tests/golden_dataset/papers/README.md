# Golden Dataset Paper Sources

This directory contains open access papers organized by domain for golden dataset annotation.

## Purpose: Cross-Domain Validation

By sourcing papers from **widely diverse scientific domains**, we validate that the 
literature review system generalizes beyond any single field. Success across unrelated 
domains (e.g., fusion physics AND microbiology) proves domain-agnostic capability.

## Target: 10+ papers per domain (8 domains = 80+ papers)

Papers should be:
- **Open Access** (arXiv, PubMed Central, IEEE Open, DOE OSTI, etc.)
- **Peer-reviewed** or from reputable preprint servers
- **Contain quantitative claims** with measurable evidence
- **Diverse in evidence quality** (strong, weak, borderline)

---

## Domain Categories

### 1. Neuromorphic Computing (`neuromorphic/`)
Focus: SNNs, neuromorphic chips, event-based sensors, spike-timing plasticity

**Suggested Sources:**
- arXiv cs.NE (Neural and Evolutionary Computing)
- Frontiers in Neuroscience
- IEEE Transactions on Neural Networks

**Paper Count Target:** 10+

---

### 2. Nanoparticle Heat Transfer (`nano_thermal/`)
Focus: Nanofluids, thermal conductivity, heat exchangers, nanoparticle synthesis

**Suggested Sources:**
- arXiv cond-mat.mes-hall (Mesoscale and Nanoscale Physics)
- International Journal of Heat and Mass Transfer (open articles)
- Nanoscale Research Letters (SpringerOpen)

**Paper Count Target:** 10+

---

### 3. Fusion Energy (`fusion/`)
Focus: Tokamak physics, plasma confinement, ITER, inertial confinement, stellarators

**Suggested Sources:**
- arXiv physics.plasm-ph (Plasma Physics)
- Nuclear Fusion (IOP Open)
- DOE OSTI (Office of Scientific and Technical Information)

**Paper Count Target:** 10+

---

### 4. Quantum Computing (`quantum/`)
Focus: Qubit technologies, quantum algorithms, error correction, quantum supremacy

**Suggested Sources:**
- arXiv quant-ph (Quantum Physics)
- Nature Communications (open access)
- PRX Quantum (open access)

**Paper Count Target:** 10+

---

### 5. Microbiology & Genomics (`microbio/`)
Focus: CRISPR, gene expression, microbiome, antibiotic resistance, sequencing

**Suggested Sources:**
- PubMed Central (PMC)
- eLife
- PLOS Genetics / PLOS Biology

**Paper Count Target:** 10+

---

### 6. Climate Science (`climate/`)
Focus: Climate models, carbon cycle, sea level rise, extreme weather, mitigation

**Suggested Sources:**
- arXiv physics.ao-ph (Atmospheric and Oceanic Physics)
- Nature Climate Change (open articles)
- Earth System Science Data (Copernicus)

**Paper Count Target:** 10+

---

### 7. Materials Science (`materials/`)
Focus: Battery materials, superconductors, metamaterials, 2D materials, alloys

**Suggested Sources:**
- arXiv cond-mat.mtrl-sci (Materials Science)
- npj Computational Materials (open access)
- Materials Today (Elsevier open)

**Paper Count Target:** 10+

---

### 8. Biomedical Imaging (`bioimaging/`)
Focus: MRI, CT, PET, ultrasound, image reconstruction, deep learning for imaging

**Suggested Sources:**
- arXiv eess.IV (Image and Video Processing)
- PubMed Central
- Frontiers in Radiology

**Paper Count Target:** 10+

---

## Paper Registry Format

Each paper should be registered in `paper_registry.json` with:

```json
{
  "paper_id": "DOMAIN-001",
  "domain": "neuromorphic",
  "title": "Paper Title",
  "authors": ["Author 1", "Author 2"],
  "year": 2024,
  "source": "arXiv:2401.12345",
  "url": "https://arxiv.org/abs/2401.12345",
  "pdf_filename": "neuromorphic/paper_001.pdf",
  "license": "CC-BY-4.0",
  "annotation_status": "pending",
  "claim_count": 0,
  "notes": "Good source for energy efficiency claims"
}
```

---

## Annotation Workflow

1. **Source Paper**: Find open access paper with relevant claims
2. **Register**: Add to `paper_registry.json`
3. **Download PDF**: Save to appropriate domain folder
4. **Extract Claims**: Identify 3-10 claims per paper
5. **Annotate**: Complete annotation template for each claim
6. **Verify**: Cross-check annotations for consistency

---

## Quality Guidelines

### Strong Evidence Claims (target: 50+)
- Quantitative results with statistics (p-values, confidence intervals)
- Clear methodology description
- Reproducible experiments with sample sizes
- Comparison to baselines

### Weak Evidence Claims (target: 30+)
- Vague or qualitative statements
- Citation-only support ("As shown in [45]...")
- Missing methodology
- Speculative language ("may", "could", "might")

### Borderline Claims (target: 10+)
- Partial quantitative data
- Small sample sizes
- Promising but incomplete results
- Needs replication

---

## Progress Tracking

| Domain | Papers | Claims Extracted | Annotated |
|--------|--------|------------------|-----------|
| Neuromorphic Computing | 0/10 | 0 | 0 |
| Nanoparticle Heat Transfer | 0/10 | 0 | 0 |
| Fusion Energy | 0/10 | 0 | 0 |
| Quantum Computing | 0/10 | 0 | 0 |
| Microbiology & Genomics | 0/10 | 0 | 0 |
| Climate Science | 0/10 | 0 | 0 |
| Materials Science | 0/10 | 0 | 0 |
| Biomedical Imaging | 0/10 | 0 | 0 |
| **Total** | **0/80** | **0** | **0** |
