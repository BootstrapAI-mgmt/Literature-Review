# Evidence Extraction Enhancement Recommendations

**Date:** November 12, 2025  
**Purpose:** Actionable improvements to increase accuracy and rigor of systematic literature review  
**Priority:** HIGH (Wave 2-3 implementation candidates)  
**Status:** 🎯 Ready for Implementation

---

## Executive Summary

Beyond the third-party's "evidence scoring" suggestion, this document identifies **12 high-value enhancements** to improve evidence extraction accuracy and research goal assessment. These recommendations are grounded in systematic review best practices and address specific gaps in the current implementation.

**Quick Wins (Wave 2):**
1. Multi-dimensional evidence scoring
2. Claim provenance tracking
3. Inter-rater reliability checks
4. Temporal coherence validation

**High-Impact (Wave 3):**
5. Evidence triangulation
6. Methodological quality assessment
7. Publication bias detection
8. Conflict-of-interest analysis

**Advanced (Wave 4):**
9. Meta-analytic aggregation
10. Evidence-to-requirement traceability matrix
11. Uncertainty quantification
12. Living review infrastructure

---

## Current System Analysis

### What Works Well ✅

1. **Multi-stage validation** (Journal-Reviewer → Judge → DRA)
2. **Version history** for audit trail
3. **Chunking** for large documents (50-75k chars)
4. **Deduplication** to prevent claim repetition
5. **Gap analysis** via Orchestrator convergence loop
6. **Binary approval** (clear accept/reject decisions)

### Current Limitations ⚠️

1. **No evidence strength gradation** - All approved claims treated equally
2. **No provenance metadata** - Can't trace claim to specific page/section
3. **No cross-paper validation** - Each paper judged in isolation
4. **No methodological quality scores** - Experimental vs. theoretical not distinguished
5. **No temporal analysis** - Can't identify evidence evolution over time
6. **No statistical meta-analysis** - Can't aggregate quantitative findings
7. **No uncertainty quantification** - Confidence levels not tracked
8. **No bias detection** - Publication bias, funding bias not assessed

---

## Recommendation #1: Multi-Dimensional Evidence Scoring

**Current State:** Binary (approved/rejected)  
**Proposed State:** Multi-dimensional quality scores  
**Effort:** 6-8 hours  
**Priority:** 🔴 HIGH (Wave 2)  
**Impact:** Enables prioritization and weighted gap analysis

### Implementation

**Extend claim structure in `Judge.py`:**

```python
# Current structure
claim = {
    "claim_id": "c1a2b3",
    "status": "approved",  # or "rejected"
    "judge_notes": "Evidence clearly supports requirement.",
    "sub_requirement": "Sub-2.1.1",
    # ... other metadata
}

# ENHANCED structure
claim = {
    "claim_id": "c1a2b3",
    "status": "approved",
    "evidence_quality": {
        # DIMENSION 1: Strength of Evidence (1-5 scale)
        "strength_score": 4,  # 5=Strong, 4=Moderate, 3=Weak, 2=Very Weak, 1=Insufficient
        "strength_rationale": "Direct experimental validation with quantitative metrics",
        
        # DIMENSION 2: Methodological Rigor (1-5 scale)
        "rigor_score": 5,  # 5=Gold standard, 4=Controlled study, 3=Observational, 2=Case study, 1=Opinion
        "study_type": "experimental",  # experimental|observational|theoretical|review|opinion
        
        # DIMENSION 3: Relevance to Requirement (1-5 scale)
        "relevance_score": 4,  # 5=Perfect match, 4=Strong, 3=Moderate, 2=Tangential, 1=Weak
        "relevance_notes": "Directly addresses SNN feature extraction on DVS data",
        
        # DIMENSION 4: Evidence Directness (1-3 scale)
        "directness": 3,  # 3=Direct, 2=Indirect, 1=Inferred
        
        # DIMENSION 5: Recency Bonus (boolean)
        "is_recent": True,  # Published within last 3 years
        
        # DIMENSION 6: Reproducibility (1-5 scale)
        "reproducibility_score": 4,  # 5=Code+data, 4=Detailed methods, 3=Basic methods, 2=Vague, 1=None
        
        # COMPOSITE SCORE (weighted average)
        "composite_score": 4.2,  # Weighted: strength(0.3) + rigor(0.25) + relevance(0.25) + directness(0.1) + recency(0.05) + reproducibility(0.05)
        
        # CONFIDENCE INTERVAL
        "confidence_level": "high"  # high|medium|low (based on evidence clarity)
    },
    "judge_notes": "Strong experimental evidence with public code repository.",
    "sub_requirement": "Sub-2.1.1",
    # ... other metadata
}
```

### Updated Judge Prompt

```python
def build_judge_prompt_enhanced(claim: Dict, sub_requirement_definition: str) -> str:
    return f"""
You are an impartial "Judge" AI evaluating scientific evidence quality.

**Claim to Evaluate:**
{json.dumps(claim, indent=2)}

**Target Requirement:**
{sub_requirement_definition}

**Your Task:**
Assess this claim using PRISMA systematic review standards across 6 dimensions:

1. **Strength of Evidence** (1-5):
   - 5: Strong (Multiple RCTs, meta-analysis, direct experimental proof)
   - 4: Moderate (Single well-designed study, clear experimental validation)
   - 3: Weak (Observational study, indirect evidence)
   - 2: Very Weak (Case reports, anecdotal evidence)
   - 1: Insufficient (Opinion, speculation, no empirical support)

2. **Methodological Rigor** (1-5):
   - 5: Gold standard (Randomized controlled trial, peer-reviewed, replicated)
   - 4: Controlled study (Experimental with controls, proper statistics)
   - 3: Observational (Real-world data, no controls)
   - 2: Case study (Single instance, n=1)
   - 1: Opinion (Expert opinion without empirical basis)

3. **Relevance to Requirement** (1-5):
   - 5: Perfect match (Directly addresses this exact requirement)
   - 4: Strong (Clearly related, minor gap)
   - 3: Moderate (Related but requires inference)
   - 2: Tangential (Peripherally related)
   - 1: Weak (Very indirect connection)

4. **Evidence Directness** (1-3):
   - 3: Direct (Paper explicitly states this finding)
   - 2: Indirect (Finding can be inferred from results)
   - 1: Inferred (Requires significant interpretation)

5. **Recency Bonus**:
   - true if published within last 3 years, false otherwise

6. **Reproducibility** (1-5):
   - 5: Code + data publicly available
   - 4: Detailed methods, replicable
   - 3: Basic methods described
   - 2: Vague methods
   - 1: No methodological detail

**Decision Criteria:**
- APPROVE if composite_score ≥ 3.0 AND strength_score ≥ 3 AND relevance_score ≥ 3
- REJECT otherwise

**Return Format (JSON only):**
{{
  "verdict": "approved|rejected",
  "evidence_quality": {{
    "strength_score": <1-5>,
    "strength_rationale": "<brief justification>",
    "rigor_score": <1-5>,
    "study_type": "experimental|observational|theoretical|review|opinion",
    "relevance_score": <1-5>,
    "relevance_notes": "<brief explanation>",
    "directness": <1-3>,
    "is_recent": <true|false>,
    "reproducibility_score": <1-5>,
    "composite_score": <calculated weighted average>,
    "confidence_level": "high|medium|low"
  }},
  "judge_notes": "<1-2 sentence summary>"
}}

**Composite Score Formula:**
composite_score = (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
"""
```

### Benefits

1. **Weighted gap analysis** - Prioritize gaps with low-quality evidence
2. **Evidence tiers** - Distinguish strong experimental proof from weak observational data
3. **Meta-analysis ready** - Composite scores enable statistical aggregation
4. **Transparency** - Explainable scoring (not black-box approval)
5. **Quality control** - Identify low-rigor papers needing re-review

### Implementation Steps

1. **Update Judge.py** (4 hours)
   - Modify `build_judge_prompt()` with enhanced prompt
   - Update `validate_judge_response()` to check score structure
   - Add score calculation validation

2. **Update version history schema** (1 hour)
   - Migrate existing claims (set default scores for backward compatibility)

3. **Update Orchestrator.py** (2 hours)
   - Use `composite_score` for weighted gap analysis
   - Prioritize filling gaps with low-quality evidence first

4. **Add visualization** (1 hour)
   - Plot evidence quality distribution per pillar
   - Heatmap of sub-requirement coverage by quality tier

---

## Recommendation #2: Claim Provenance Tracking

**Current State:** Claims have filename but not page/section location  
**Proposed State:** Full citation with page numbers, sections, quotes  
**Effort:** 4-6 hours  
**Priority:** 🟡 HIGH (Wave 2)  
**Impact:** Enables verification, auditing, and targeted re-review

### Implementation

**Extend Journal-Reviewer.py text extraction:**

```python
# Current extraction
def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

# ENHANCED extraction with provenance
def extract_text_with_provenance(file_path: str) -> List[Dict]:
    """
    Extract text with page-level tracking.
    
    Returns:
        List of dicts: [
            {"page_num": 1, "text": "...", "section": "Introduction"},
            {"page_num": 2, "text": "...", "section": "Methods"},
            ...
        ]
    """
    pages_with_metadata = []
    
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            
            # Detect section headings (simple heuristic)
            section = detect_section_heading(text)
            
            pages_with_metadata.append({
                "page_num": page_num,
                "text": text,
                "section": section or "Unknown",
                "char_start": sum(len(p["text"]) for p in pages_with_metadata),
                "char_end": sum(len(p["text"]) for p in pages_with_metadata) + len(text)
            })
    
    return pages_with_metadata

def detect_section_heading(text: str) -> Optional[str]:
    """Detect common section headings in academic papers."""
    headings = [
        "abstract", "introduction", "background", "related work",
        "methods", "methodology", "approach", "design",
        "results", "findings", "experiments", "evaluation",
        "discussion", "analysis", "interpretation",
        "conclusion", "future work", "limitations",
        "references", "bibliography"
    ]
    
    # Look for heading patterns in first 200 chars
    first_lines = text[:200].lower()
    for heading in headings:
        if heading in first_lines:
            return heading.title()
    
    return None
```

**Enhanced claim structure:**

```python
claim = {
    "claim_id": "c1a2b3",
    "status": "approved",
    
    # NEW: Provenance metadata
    "provenance": {
        "filename": "neuromorphic_snn_2024.pdf",
        "page_numbers": [5, 6],  # Claim spans pages 5-6
        "section": "Results",
        "char_start": 12450,  # Character offset in full text
        "char_end": 12890,
        
        # Direct quote from paper
        "supporting_quote": "We achieved 94.3% accuracy on DVS128-Gesture using a 3-layer SNN with 1.2mJ energy per inference...",
        "quote_page": 5,
        
        # Context (surrounding text)
        "context_before": "...previous methods required 15mJ per inference.",
        "context_after": "This represents a 12x improvement over baseline...",
        
        # DOI/URL if available
        "doi": "10.1109/TNNLS.2024.12345",
        "url": "https://arxiv.org/abs/2401.12345"
    },
    
    "sub_requirement": "Sub-2.1.1",
    "extracted_claim_text": "Achieved 94.3% accuracy on event-based gesture recognition with 1.2mJ energy efficiency",
    # ... rest of claim
}
```

### Benefits

1. **Verifiable claims** - Human reviewers can check exact source
2. **Citation generation** - Auto-generate "According to Smith et al. (2024, p. 5)..."
3. **Conflict resolution** - Trace contradictory claims to different papers/sections
4. **Targeted re-review** - Re-analyze specific sections if needed
5. **Audit trail** - Full transparency for systematic review standards

---

## Recommendation #3: Inter-Rater Reliability (Multi-Judge Consensus)

**Current State:** Single Judge evaluation  
**Proposed State:** Multiple independent judgments with agreement scoring  
**Effort:** 6-8 hours  
**Priority:** 🟡 MEDIUM (Wave 2-3)  
**Impact:** Increases confidence in borderline decisions

### Implementation

```python
# Judge.py enhancement
API_CONFIG = {
    "CONSENSUS_JUDGES": 3,  # Number of independent judgments
    "AGREEMENT_THRESHOLD": 0.67,  # 67% must agree (2 out of 3)
    "TIE_BREAKER_ENABLED": True
}

def judge_with_consensus(claim: Dict, sub_req_def: str, api_manager) -> Dict:
    """
    Get multiple independent judgments and compute consensus.
    """
    judgments = []
    
    for judge_num in range(API_CONFIG["CONSENSUS_JUDGES"]):
        # Each judge gets identical prompt but different temperature for diversity
        prompt = build_judge_prompt_enhanced(claim, sub_req_def)
        
        judgment = api_manager.call_api(
            prompt,
            temperature=0.3 + (judge_num * 0.1),  # 0.3, 0.4, 0.5
            cache_key=f"{claim['claim_id']}_judge_{judge_num}"
        )
        
        validated = validate_judge_response(judgment)
        if validated:
            judgments.append(validated)
    
    # Analyze agreement
    verdicts = [j["verdict"] for j in judgments]
    verdict_counts = {
        "approved": verdicts.count("approved"),
        "rejected": verdicts.count("rejected")
    }
    
    # Compute agreement
    majority_verdict = max(verdict_counts, key=verdict_counts.get)
    agreement_rate = verdict_counts[majority_verdict] / len(verdicts)
    
    # Check if agreement meets threshold
    if agreement_rate >= API_CONFIG["AGREEMENT_THRESHOLD"]:
        consensus_status = "strong_consensus"
    elif agreement_rate >= 0.5:
        consensus_status = "weak_consensus"
    else:
        consensus_status = "no_consensus"
    
    # Aggregate scores (average across judges)
    avg_composite_score = np.mean([
        j["evidence_quality"]["composite_score"] 
        for j in judgments
    ])
    
    # Build consensus judgment
    consensus_judgment = {
        "verdict": majority_verdict,
        "consensus_metadata": {
            "total_judges": len(judgments),
            "agreement_rate": agreement_rate,
            "consensus_status": consensus_status,
            "vote_breakdown": verdict_counts,
            "individual_judgments": judgments,
            "average_composite_score": avg_composite_score,
            "score_std_dev": np.std([
                j["evidence_quality"]["composite_score"] 
                for j in judgments
            ])
        },
        "evidence_quality": judgments[0]["evidence_quality"],  # Use first judge's detailed scores
        "judge_notes": f"{consensus_status.replace('_', ' ').title()}: {verdict_counts}"
    }
    
    return consensus_judgment
```

### Benefits

1. **Higher confidence** - Borderline claims get multiple reviews
2. **Identify ambiguity** - Low agreement signals need for human review
3. **Reduce bias** - No single judge's quirks dominate
4. **Quality metric** - Agreement rate indicates claim clarity

### Cost-Benefit Tradeoff

- **Pro:** More reliable decisions (especially critical for borderline cases)
- **Con:** 3x API costs and latency
- **Mitigation:** Use consensus only for **borderline claims** (composite_score 2.5-3.5 range)

---

## Recommendation #4: Temporal Coherence Validation

**Current State:** No temporal analysis of evidence evolution  
**Proposed State:** Track how evidence changes over time, detect emerging consensus  
**Effort:** 8-10 hours  
**Priority:** 🟡 MEDIUM (Wave 3)  
**Impact:** Identify mature vs. nascent research areas

### Implementation

**Add temporal analysis to Orchestrator.py:**

```python
def analyze_evidence_evolution(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """
    Analyze how evidence for each sub-requirement has evolved over time.
    
    Returns:
        {
            "Sub-2.1.1": {
                "earliest_evidence": 2018,
                "latest_evidence": 2024,
                "evidence_count_by_year": {2018: 2, 2020: 5, 2024: 8},
                "quality_trend": "improving",  # improving|stable|declining
                "maturity_level": "established",  # emerging|growing|established|mature
                "consensus_strength": "strong",  # strong|moderate|weak|none
                "contradictory_findings": False
            },
            ...
        }
    """
    temporal_analysis = {}
    
    for pillar_name, pillar_data in pillar_definitions.items():
        for req_key, req_data in pillar_data.get("requirements", {}).items():
            for sub_req_list in req_data:
                for sub_req in sub_req_list.split(','):
                    sub_req = sub_req.strip()
                    
                    # Get all claims for this sub-requirement
                    claims = db[db["Requirement(s)"].str.contains(sub_req, na=False)]
                    
                    if claims.empty:
                        continue
                    
                    # Extract publication years
                    years = claims["PUBLICATION_YEAR"].dropna().astype(int)
                    
                    if len(years) == 0:
                        continue
                    
                    # Count by year
                    year_counts = years.value_counts().sort_index().to_dict()
                    
                    # Analyze quality trend (if composite scores available)
                    if "EVIDENCE_COMPOSITE_SCORE" in claims.columns:
                        scores_by_year = claims.groupby("PUBLICATION_YEAR")["EVIDENCE_COMPOSITE_SCORE"].mean()
                        
                        # Linear regression to detect trend
                        from scipy.stats import linregress
                        slope, intercept, r_value, p_value, std_err = linregress(
                            scores_by_year.index, scores_by_year.values
                        )
                        
                        if slope > 0.1 and p_value < 0.05:
                            quality_trend = "improving"
                        elif slope < -0.1 and p_value < 0.05:
                            quality_trend = "declining"
                        else:
                            quality_trend = "stable"
                    else:
                        quality_trend = "unknown"
                    
                    # Determine maturity level
                    evidence_span = years.max() - years.min()
                    total_papers = len(claims)
                    recent_papers = len(claims[claims["PUBLICATION_YEAR"] >= 2022])
                    
                    if evidence_span < 2:
                        maturity = "emerging"
                    elif evidence_span < 5 and total_papers < 10:
                        maturity = "growing"
                    elif evidence_span >= 5 and total_papers >= 10:
                        maturity = "established"
                    elif total_papers >= 20 and recent_papers >= 5:
                        maturity = "mature"
                    else:
                        maturity = "unknown"
                    
                    # Check for consensus (low score variance = consensus)
                    if "EVIDENCE_COMPOSITE_SCORE" in claims.columns:
                        score_std = claims["EVIDENCE_COMPOSITE_SCORE"].std()
                        if score_std < 0.5:
                            consensus = "strong"
                        elif score_std < 1.0:
                            consensus = "moderate"
                        elif score_std < 1.5:
                            consensus = "weak"
                        else:
                            consensus = "none"
                    else:
                        consensus = "unknown"
                    
                    temporal_analysis[sub_req] = {
                        "earliest_evidence": int(years.min()),
                        "latest_evidence": int(years.max()),
                        "evidence_span_years": int(evidence_span),
                        "total_papers": total_papers,
                        "evidence_count_by_year": year_counts,
                        "quality_trend": quality_trend,
                        "maturity_level": maturity,
                        "consensus_strength": consensus,
                        "recent_activity": recent_papers >= 3  # Active if 3+ papers in last 3 years
                    }
    
    return temporal_analysis
```

### Visualization

**Generate temporal heatmaps:**

```python
def plot_evidence_evolution(temporal_analysis: Dict, output_file: str):
    """
    Create heatmap showing evidence emergence over time.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # Build matrix: rows = sub-requirements, cols = years
    sub_reqs = list(temporal_analysis.keys())
    all_years = sorted(set(
        year 
        for data in temporal_analysis.values() 
        for year in data["evidence_count_by_year"].keys()
    ))
    
    matrix = np.zeros((len(sub_reqs), len(all_years)))
    
    for i, sub_req in enumerate(sub_reqs):
        for j, year in enumerate(all_years):
            count = temporal_analysis[sub_req]["evidence_count_by_year"].get(year, 0)
            matrix[i, j] = count
    
    # Plot heatmap
    plt.figure(figsize=(16, 12))
    sns.heatmap(
        matrix,
        xticklabels=all_years,
        yticklabels=sub_reqs,
        cmap="YlOrRd",
        annot=True,
        fmt=".0f",
        cbar_kws={"label": "Number of Papers"}
    )
    plt.title("Evidence Evolution: Papers per Sub-Requirement by Year")
    plt.xlabel("Publication Year")
    plt.ylabel("Sub-Requirement")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
```

### Benefits

1. **Identify research gaps** - Areas with no recent papers (stagnant research)
2. **Emerging trends** - Detect rapidly growing evidence areas
3. **Maturity assessment** - Distinguish mature fields from nascent ones
4. **Funding priorities** - Target emerging areas for investigation

---

## Recommendation #5: Evidence Triangulation

**Current State:** Each claim judged independently  
**Proposed State:** Cross-validate claims across multiple papers  
**Effort:** 10-12 hours  
**Priority:** 🟢 MEDIUM (Wave 3)  
**Impact:** Detect consistent vs. contradictory evidence

### Implementation

```python
def triangulate_evidence(claims: List[Dict], similarity_threshold: float = 0.85) -> Dict:
    """
    Group similar claims and analyze cross-paper agreement.
    
    Returns:
        {
            "cluster_1": {
                "representative_claim": "SNNs achieve 90%+ accuracy on DVS datasets",
                "supporting_papers": ["paper1.pdf", "paper2.pdf", "paper3.pdf"],
                "claim_ids": ["c1", "c2", "c3"],
                "agreement_level": "strong",  # strong|moderate|weak
                "score_variance": 0.3,
                "contradictory_claims": []
            },
            ...
        }
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import DBSCAN
    
    # Embed all claim texts
    model = SentenceTransformer('all-MiniLM-L6-v2')
    claim_texts = [c["extracted_claim_text"] for c in claims]
    embeddings = model.encode(claim_texts)
    
    # Cluster similar claims
    clustering = DBSCAN(eps=1-similarity_threshold, min_samples=2, metric='cosine')
    labels = clustering.fit_predict(embeddings)
    
    # Analyze each cluster
    triangulation_results = {}
    
    for cluster_id in set(labels):
        if cluster_id == -1:  # Noise cluster
            continue
        
        cluster_mask = labels == cluster_id
        cluster_claims = [claims[i] for i in np.where(cluster_mask)[0]]
        
        # Extract metadata
        supporting_papers = list(set(c["filename"] for c in cluster_claims))
        claim_ids = [c["claim_id"] for c in cluster_claims]
        
        # Analyze agreement
        scores = [c["evidence_quality"]["composite_score"] for c in cluster_claims if "evidence_quality" in c]
        
        if scores:
            score_variance = np.var(scores)
            avg_score = np.mean(scores)
            
            if score_variance < 0.3:
                agreement = "strong"
            elif score_variance < 0.7:
                agreement = "moderate"
            else:
                agreement = "weak"
        else:
            score_variance = None
            avg_score = None
            agreement = "unknown"
        
        # Find contradictions (claims with opposite verdicts)
        verdicts = [c["status"] for c in cluster_claims]
        has_contradiction = "approved" in verdicts and "rejected" in verdicts
        
        triangulation_results[f"cluster_{cluster_id}"] = {
            "representative_claim": cluster_claims[0]["extracted_claim_text"],
            "supporting_papers": supporting_papers,
            "claim_ids": claim_ids,
            "num_supporting_papers": len(supporting_papers),
            "agreement_level": agreement,
            "average_score": avg_score,
            "score_variance": score_variance,
            "has_contradiction": has_contradiction,
            "all_claims": cluster_claims
        }
    
    return triangulation_results
```

### Benefits

1. **Strengthen evidence** - Multiple papers supporting same claim
2. **Flag contradictions** - Different papers reaching opposite conclusions
3. **Identify consensus** - Low variance = field agreement
4. **Prioritize research** - High-consensus claims are reliable

---

## Recommendation #6: Methodological Quality Assessment

**Current State:** Study type tracked but not validated against standards  
**Proposed State:** Formal quality assessment using established frameworks  
**Effort:** 8-10 hours  
**Priority:** 🟡 MEDIUM (Wave 3)  
**Impact:** Distinguish high-quality studies from weak evidence

### Implementation

**Add GRADE (Grading of Recommendations Assessment) framework:**

```python
def assess_methodological_quality(claim: Dict, paper_metadata: Dict) -> Dict:
    """
    Apply GRADE criteria to assess evidence quality.
    
    GRADE Criteria:
    1. Study Design (RCT=high, Observational=low)
    2. Risk of Bias
    3. Inconsistency
    4. Indirectness
    5. Imprecision
    6. Publication Bias
    
    Returns quality level: "very_low", "low", "moderate", "high"
    """
    
    # Start with study design baseline
    study_type = claim.get("evidence_quality", {}).get("study_type", "unknown")
    
    if study_type == "experimental":
        baseline_quality = 4  # High
    elif study_type == "observational":
        baseline_quality = 2  # Low
    elif study_type == "theoretical":
        baseline_quality = 1  # Very Low (for empirical claims)
    else:
        baseline_quality = 1
    
    # Adjust for risk of bias
    reproducibility = claim.get("evidence_quality", {}).get("reproducibility_score", 3)
    if reproducibility >= 4:
        bias_adjustment = 0  # No downgrade
    elif reproducibility >= 3:
        bias_adjustment = -1  # Serious risk
    else:
        bias_adjustment = -2  # Very serious risk
    
    # Adjust for indirectness
    relevance = claim.get("evidence_quality", {}).get("relevance_score", 3)
    if relevance >= 4:
        indirectness_adjustment = 0
    elif relevance >= 3:
        indirectness_adjustment = -1
    else:
        indirectness_adjustment = -2
    
    # Compute final quality
    final_quality_score = baseline_quality + bias_adjustment + indirectness_adjustment
    final_quality_score = max(1, min(4, final_quality_score))  # Clamp to 1-4
    
    quality_levels = {
        1: "very_low",
        2: "low",
        3: "moderate",
        4: "high"
    }
    
    return {
        "grade_quality_level": quality_levels[final_quality_score],
        "grade_score": final_quality_score,
        "baseline_quality": baseline_quality,
        "bias_adjustment": bias_adjustment,
        "indirectness_adjustment": indirectness_adjustment,
        "interpretation": get_grade_interpretation(quality_levels[final_quality_score])
    }

def get_grade_interpretation(quality_level: str) -> str:
    """Map GRADE quality to interpretation."""
    interpretations = {
        "high": "High confidence that true effect is close to estimated effect",
        "moderate": "Moderate confidence; true effect likely close but may differ substantially",
        "low": "Limited confidence; true effect may differ substantially",
        "very_low": "Very little confidence; true effect likely substantially different"
    }
    return interpretations.get(quality_level, "Unknown quality")
```

### Benefits

1. **Standardized quality** - Uses established GRADE framework
2. **Explainable decisions** - Clear rationale for quality ratings
3. **Publication-ready** - GRADE required for systematic reviews
4. **Risk communication** - Transparent uncertainty

---

## Quick Reference: Priority Matrix

| Recommendation | Effort | Priority | Impact | Wave |
|----------------|--------|----------|--------|------|
| 1. Multi-dimensional scoring | 6-8h | 🔴 HIGH | HIGH | Wave 2 |
| 2. Provenance tracking | 4-6h | 🟡 HIGH | MEDIUM | Wave 2 |
| 3. Inter-rater reliability | 6-8h | 🟡 MEDIUM | MEDIUM | Wave 2-3 |
| 4. Temporal coherence | 8-10h | 🟡 MEDIUM | MEDIUM | Wave 3 |
| 5. Evidence triangulation | 10-12h | 🟢 MEDIUM | HIGH | Wave 3 |
| 6. Methodological quality | 8-10h | 🟡 MEDIUM | MEDIUM | Wave 3 |

---

## Implementation Roadmap

### Wave 2 (Weeks 3-4) - Foundation

**Week 3:**
- ✅ Implement multi-dimensional evidence scoring (Rec #1)
- ✅ Add provenance tracking to extraction (Rec #2)
- ✅ Update version history schema

**Week 4:**
- ✅ Add visualization for evidence quality distribution
- ✅ Test inter-rater reliability on sample dataset (Rec #3)
- ✅ Document new scoring methodology

### Wave 3 (Weeks 5-6) - Advanced Features

**Week 5:**
- ✅ Implement temporal coherence analysis (Rec #4)
- ✅ Build evidence triangulation clustering (Rec #5)
- ✅ Generate temporal heatmaps

**Week 6:**
- ✅ Add GRADE methodological quality assessment (Rec #6)
- ✅ Integrate all quality metrics into Orchestrator gap analysis
- ✅ Create comprehensive quality report

---

## Success Metrics

**Evidence Quality Improvements:**
- [ ] 100% of claims have multi-dimensional scores
- [ ] 90%+ of claims have page-level provenance
- [ ] Borderline claims (score 2.5-3.5) get consensus review
- [ ] Evidence evolution tracked for all sub-requirements
- [ ] Contradictory findings automatically flagged
- [ ] GRADE quality levels assigned to all claims

**Process Improvements:**
- [ ] Gap analysis prioritizes low-quality evidence areas
- [ ] Visual quality dashboards available
- [ ] Temporal trends guide research priorities
- [ ] Publication-ready systematic review output

---

## Conclusion

These 6 recommendations (plus 6 more in extended version) transform the Literature Review system from a good extraction tool into a **rigorous systematic review platform** meeting PRISMA standards.

**Immediate Next Steps:**
1. Implement Recommendation #1 (multi-dimensional scoring) in Wave 2
2. Add provenance tracking (Rec #2) to extraction pipeline
3. Test inter-rater reliability (Rec #3) on challenging claims

These enhancements are **grounded in systematic review best practices**, **implementable within existing architecture**, and **provide measurable quality improvements**.

---

**Document Status:** ✅ Ready for Implementation  
**Next Action:** Review with team, prioritize Rec #1-3 for Wave 2  
**Estimated Total Effort:** 40-50 hours across all 6 recommendations
