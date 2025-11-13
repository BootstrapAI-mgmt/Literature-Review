# TASK CARD #19: Temporal Coherence Validation

**Priority:** 🟡 MEDIUM  
**Estimated Effort:** 8-10 hours  
**Risk Level:** LOW  
**Wave:** Wave 3 (Weeks 5-6)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #16 (Evidence Scoring), Task Card #9 (Orchestrator tests)  
**Blocks:** None

## Problem Statement

Current system treats all evidence as equally timely regardless of publication date. This prevents:
- Identifying mature vs. nascent research areas
- Detecting emerging trends or declining interest
- Prioritizing gaps in active research areas
- Understanding evidence evolution over time

Temporal coherence analysis tracks how evidence quality and quantity change over time, enabling strategic research prioritization and maturity assessment.

## Acceptance Criteria

**Functional Requirements:**
- [ ] Extract publication years from all papers
- [ ] Track evidence count by year for each sub-requirement
- [ ] Detect quality trends (improving/stable/declining)
- [ ] Classify maturity level (emerging/growing/established/mature)
- [ ] Assess consensus strength over time
- [ ] Generate temporal heatmaps showing evidence evolution

**Maturity Classifications:**
- [ ] **Emerging**: <2 years of evidence, <5 papers
- [ ] **Growing**: 2-5 years span, 5-10 papers
- [ ] **Established**: 5+ years span, 10+ papers
- [ ] **Mature**: 10+ years span, 20+ papers, active recent publications

**Technical Requirements:**
- [ ] Publication year extraction >90% accurate
- [ ] Quality trend detection uses linear regression (p<0.05)
- [ ] Temporal heatmap generated for all pillars
- [ ] Analysis cached (rebuild only when DB changes)

## Implementation Guide

**Files to Modify:**

### 1. literature_review/orchestrator.py (~150 lines new)

```python
def analyze_evidence_evolution(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """
    Analyze how evidence for each sub-requirement has evolved over time.
    
    Returns:
        {
            "Sub-2.1.1": {
                "earliest_evidence": 2018,
                "latest_evidence": 2024,
                "evidence_span_years": 6,
                "total_papers": 15,
                "evidence_count_by_year": {2018: 2, 2020: 5, 2024: 8},
                "quality_trend": "improving",  # improving|stable|declining
                "maturity_level": "established",  # emerging|growing|established|mature
                "consensus_strength": "strong",  # strong|moderate|weak|none
                "recent_activity": True  # 3+ papers in last 3 years
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
                    quality_trend = "unknown"
                    if "EVIDENCE_COMPOSITE_SCORE" in claims.columns:
                        scores_by_year = claims.groupby("PUBLICATION_YEAR")["EVIDENCE_COMPOSITE_SCORE"].mean()
                        
                        if len(scores_by_year) >= 3:  # Need 3+ years for trend
                            # Linear regression to detect trend
                            from scipy.stats import linregress
                            slope, intercept, r_value, p_value, std_err = linregress(
                                scores_by_year.index, scores_by_year.values
                            )
                            
                            if p_value < 0.05:  # Statistically significant
                                if slope > 0.1:
                                    quality_trend = "improving"
                                elif slope < -0.1:
                                    quality_trend = "declining"
                                else:
                                    quality_trend = "stable"
                            else:
                                quality_trend = "stable"
                    
                    # Determine maturity level
                    evidence_span = int(years.max() - years.min())
                    total_papers = len(claims)
                    current_year = 2024  # TODO: Use datetime.now().year
                    recent_papers = len(claims[claims["PUBLICATION_YEAR"] >= current_year - 3])
                    
                    if evidence_span < 2 and total_papers < 5:
                        maturity = "emerging"
                    elif evidence_span < 5 and total_papers < 10:
                        maturity = "growing"
                    elif evidence_span >= 5 and total_papers >= 10:
                        maturity = "established"
                        if total_papers >= 20 and recent_papers >= 5:
                            maturity = "mature"
                    else:
                        maturity = "growing"
                    
                    # Check for consensus (low score variance = consensus)
                    consensus = "unknown"
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
                    
                    temporal_analysis[sub_req] = {
                        "earliest_evidence": int(years.min()),
                        "latest_evidence": int(years.max()),
                        "evidence_span_years": evidence_span,
                        "total_papers": total_papers,
                        "recent_papers": recent_papers,
                        "evidence_count_by_year": year_counts,
                        "quality_trend": quality_trend,
                        "maturity_level": maturity,
                        "consensus_strength": consensus,
                        "recent_activity": recent_papers >= 3  # Active if 3+ papers in last 3 years
                    }
    
    return temporal_analysis
```

### 2. Visualization Module (~80 lines new)

```python
def plot_evidence_evolution(temporal_analysis: Dict, output_file: str):
    """
    Create heatmap showing evidence emergence over time.
    
    Rows: Sub-requirements
    Columns: Years
    Cell values: Number of papers
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

def plot_maturity_distribution(temporal_analysis: Dict, output_file: str):
    """Plot distribution of maturity levels across sub-requirements."""
    import matplotlib.pyplot as plt
    
    maturity_counts = {}
    for data in temporal_analysis.values():
        level = data["maturity_level"]
        maturity_counts[level] = maturity_counts.get(level, 0) + 1
    
    levels = ["emerging", "growing", "established", "mature"]
    counts = [maturity_counts.get(level, 0) for level in levels]
    
    plt.figure(figsize=(10, 6))
    plt.bar(levels, counts, color=['#ff9999', '#ffcc99', '#99cc99', '#66b2ff'])
    plt.xlabel("Maturity Level")
    plt.ylabel("Number of Sub-Requirements")
    plt.title("Evidence Maturity Distribution")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
```

## Testing Strategy

### Unit Tests

```python
@pytest.mark.unit
def test_maturity_classification():
    """Test maturity level classification."""
    # Emerging: <2 years, <5 papers
    assert classify_maturity(evidence_span=1, total_papers=3, recent_papers=3) == "emerging"
    
    # Growing: 2-5 years, 5-10 papers
    assert classify_maturity(evidence_span=3, total_papers=7, recent_papers=2) == "growing"
    
    # Established: 5+ years, 10+ papers
    assert classify_maturity(evidence_span=6, total_papers=12, recent_papers=3) == "established"
    
    # Mature: 10+ years, 20+ papers, active
    assert classify_maturity(evidence_span=10, total_papers=25, recent_papers=6) == "mature"

@pytest.mark.unit
def test_quality_trend_detection():
    """Test linear regression trend detection."""
    # Improving trend
    years = [2020, 2021, 2022, 2023, 2024]
    scores = [2.5, 2.8, 3.1, 3.4, 3.7]
    
    from scipy.stats import linregress
    slope, _, _, p_value, _ = linregress(years, scores)
    
    assert slope > 0.1
    assert p_value < 0.05
    # Should classify as "improving"
```

### Integration Tests (Modify Task Card #9)

```python
from literature_review.orchestrator import analyze_evidence_evolution, classify_maturity

@pytest.mark.integration
def test_temporal_analysis_generation(temp_workspace, test_database):
    """Test temporal analysis generation."""
    
    # Create test database with temporal data
    db = create_test_db_with_years([
        {"sub_req": "Sub-1.1.1", "year": 2020, "score": 3.0},
        {"sub_req": "Sub-1.1.1", "year": 2022, "score": 3.5},
        {"sub_req": "Sub-1.1.1", "year": 2024, "score": 4.0},
    ])
    
    pillar_defs = load_pillar_definitions()
    
    # Run temporal analysis
    temporal = analyze_evidence_evolution(db, pillar_defs)
    
    assert "Sub-1.1.1" in temporal
    assert temporal["Sub-1.1.1"]["earliest_evidence"] == 2020
    assert temporal["Sub-1.1.1"]["latest_evidence"] == 2024
    assert temporal["Sub-1.1.1"]["quality_trend"] == "improving"
    assert temporal["Sub-1.1.1"]["maturity_level"] in ["growing", "established"]
```

## Success Criteria

- [ ] Publication years extracted from all papers
- [ ] Temporal analysis computed for all sub-requirements
- [ ] Quality trends detected with statistical significance
- [ ] Maturity levels assigned correctly
- [ ] Temporal heatmap generated successfully
- [ ] Maturity distribution plot created
- [ ] Analysis caching implemented (rebuild only on DB changes)
- [ ] Unit tests pass (90% coverage)
- [ ] Integration tests validate full workflow

## Benefits

1. **Strategic planning** - Identify where research is active vs. stagnant
2. **Gap prioritization** - Focus on mature areas with weak evidence
3. **Trend detection** - Spot improving or declining evidence quality
4. **Funding decisions** - Target emerging areas for investigation
5. **Research maturity** - Understand field development stage

---

**Status:** Ready for implementation  
**Wave:** Wave 3 (Weeks 5-6)  
**Next Steps:** Implement temporal analysis in literature_review/orchestrator.py, create visualization functions, add to gap analysis report
