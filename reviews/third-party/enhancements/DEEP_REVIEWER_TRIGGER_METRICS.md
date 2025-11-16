# Deep Reviewer - Intelligent Trigger System Design

**Date:** November 16, 2025  
**Purpose:** Objective metrics-based system to automatically trigger Deep Reviewer when ROI is positive  
**Author:** GitHub Copilot (AI Agent)

---

## Executive Summary

**Problem:** Deep Reviewer can add value but is costly (time/API). Running it blindly wastes resources; not running it misses opportunities.

**Solution:** Measure 6 objective metrics after gap analysis. Trigger Deep Reviewer only when metrics indicate **high probability of ROI-positive outcome**.

**Key Innovation:** Treat Deep Reviewer as a **conditional optimization step** in the pipeline, not a manual tool or default stage.

---

## 1. Trigger Decision Framework

### 1.1 Decision Logic

```python
def should_trigger_deep_review(gap_report, version_history, research_db):
    """
    Returns: (should_trigger: bool, trigger_reasons: List[str], skip_reasons: List[str])
    """
    metrics = calculate_trigger_metrics(gap_report, version_history, research_db)
    
    # Evaluate each metric
    triggers = []
    blockers = []
    
    # METRIC 1: Gap Opportunity Score
    if metrics['gap_opportunity_score'] >= 60:
        triggers.append(f"High gap opportunity ({metrics['gap_opportunity_score']}/100)")
    elif metrics['gap_opportunity_score'] < 30:
        blockers.append(f"Low gap opportunity ({metrics['gap_opportunity_score']}/100)")
    
    # METRIC 2: Paper Reuse Efficiency
    if metrics['paper_reuse_efficiency'] >= 0.4:
        triggers.append(f"High paper reuse potential ({metrics['paper_reuse_efficiency']:.1%})")
    elif metrics['paper_reuse_efficiency'] < 0.2:
        blockers.append(f"Low paper reuse ({metrics['paper_reuse_efficiency']:.1%})")
    
    # METRIC 3: Bottleneck Severity
    if metrics['bottleneck_severity'] >= 5:
        triggers.append(f"Critical bottlenecks detected ({metrics['bottleneck_severity']} gaps)")
    
    # METRIC 4: Coverage Saturation
    if metrics['coverage_saturation'] < 0.6:
        triggers.append(f"Low saturation ({metrics['coverage_saturation']:.1%}) - room for improvement")
    elif metrics['coverage_saturation'] >= 0.85:
        blockers.append(f"High saturation ({metrics['coverage_saturation']:.1%}) - diminishing returns")
    
    # METRIC 5: Expected Claim Yield
    if metrics['expected_claim_yield'] >= 15:
        triggers.append(f"High expected yield ({metrics['expected_claim_yield']} claims)")
    elif metrics['expected_claim_yield'] < 5:
        blockers.append(f"Low expected yield ({metrics['expected_claim_yield']} claims)")
    
    # METRIC 6: Cost-Benefit Ratio
    if metrics['cost_benefit_ratio'] >= 3.0:
        triggers.append(f"Excellent ROI ({metrics['cost_benefit_ratio']:.1f}x)")
    elif metrics['cost_benefit_ratio'] < 1.5:
        blockers.append(f"Poor ROI ({metrics['cost_benefit_ratio']:.1f}x)")
    
    # DECISION RULES
    # Rule 1: At least 3 positive triggers AND no critical blockers
    # Rule 2: OR any single metric is EXCEPTIONAL (>90th percentile)
    
    has_critical_blocker = any('Low paper reuse' in b or 'High saturation' in b for b in blockers)
    exceptional_metric = any(
        metrics['gap_opportunity_score'] >= 85,
        metrics['paper_reuse_efficiency'] >= 0.7,
        metrics['bottleneck_severity'] >= 10,
        metrics['cost_benefit_ratio'] >= 5.0
    )
    
    if exceptional_metric:
        return True, triggers + ["EXCEPTIONAL metric detected - override"], blockers
    elif len(triggers) >= 3 and not has_critical_blocker:
        return True, triggers, blockers
    else:
        return False, triggers, blockers
```

---

## 2. Trigger Metrics Definitions

### METRIC 1: Gap Opportunity Score (0-100)

**Measures:** How many gaps are in the "sweet spot" for Deep Reviewer (0-50% coverage with contributing papers)

**Formula:**
```python
def calculate_gap_opportunity_score(gap_report):
    """
    Score = (ideal_gaps / total_gaps) * 100
    
    Ideal gaps:
    - Completeness: 0-50% (room for improvement)
    - Has 1+ contributing papers (something to re-analyze)
    - Confidence: medium-high (not already flagged as uncertain)
    """
    total_gaps = count_all_sub_requirements(gap_report)
    ideal_gaps = 0
    
    for pillar, pillar_data in gap_report.items():
        for req_key, req_data in pillar_data.get('analysis', {}).items():
            for sub_req_key, sub_req_data in req_data.items():
                completeness = sub_req_data.get('completeness_percent', 100)
                contributing_papers = sub_req_data.get('contributing_papers', [])
                confidence = sub_req_data.get('confidence_level', 'low')
                
                # Ideal candidate criteria
                if (0 <= completeness <= 50 and 
                    len(contributing_papers) >= 1 and
                    confidence in ['medium', 'high']):
                    ideal_gaps += 1
    
    return (ideal_gaps / total_gaps) * 100 if total_gaps > 0 else 0
```

**Interpretation:**
- **0-30:** Low opportunity (most gaps have no papers OR already well-covered)
- **30-60:** Moderate opportunity (some good targets)
- **60-100:** High opportunity (many ideal targets)

**Trigger Threshold:** ≥60

**Example Calculation:**
```
Total sub-requirements: 108
Ideal gaps (0-50%, has papers, medium+ confidence): 35

Gap Opportunity Score = (35 / 108) * 100 = 32.4

Verdict: MODERATE - not quite enough to trigger alone
```

---

### METRIC 2: Paper Reuse Efficiency (0.0-1.0)

**Measures:** What fraction of existing papers can be productively re-analyzed for new claims?

**Formula:**
```python
def calculate_paper_reuse_efficiency(gap_report, version_history, research_db):
    """
    Efficiency = reusable_papers / total_papers_in_db
    
    Reusable paper criteria:
    - Has 1+ approved claims (proven relevant)
    - Has gaps it contributes to with <80% coverage (room for more)
    - Not already exhaustively analyzed (claim count < theoretical max)
    """
    all_papers = set(research_db['FILENAME'].tolist())
    reusable_papers = set()
    
    for filename in all_papers:
        # Check if paper has approved claims
        approved_claims = get_approved_claims_for_paper(filename, version_history)
        if not approved_claims:
            continue  # Not proven relevant yet
        
        # Check if paper contributes to any under-covered gaps
        contributing_gaps = find_gaps_with_paper(filename, gap_report)
        under_covered_gaps = [
            gap for gap in contributing_gaps
            if gap['completeness_percent'] < 80
        ]
        
        if not under_covered_gaps:
            continue  # Paper already fully utilized
        
        # Check if paper is not exhausted (heuristic: <10 claims per paper)
        claim_count = len(approved_claims)
        if claim_count >= 10:
            continue  # Likely exhausted
        
        reusable_papers.add(filename)
    
    return len(reusable_papers) / len(all_papers) if all_papers else 0.0
```

**Interpretation:**
- **0.0-0.2:** Low reuse (need new papers, not deep review)
- **0.2-0.4:** Moderate reuse (some papers worth revisiting)
- **0.4-1.0:** High reuse (many papers under-utilized)

**Trigger Threshold:** ≥0.4

**Example Calculation:**
```
Total papers in database: 5
Papers with approved claims: 4
Papers with under-covered gaps they contribute to: 3
Papers not exhausted (<10 claims): 3

Reusable papers: 3
Paper Reuse Efficiency = 3 / 5 = 0.6

Verdict: HIGH - 60% of papers can yield more claims
```

---

### METRIC 3: Bottleneck Severity (Integer Count)

**Measures:** How many gaps are critical bottlenecks blocking downstream requirements?

**Formula:**
```python
def calculate_bottleneck_severity(gap_report, pillar_definitions):
    """
    Bottleneck = A gap that:
    1. Is at <40% coverage (significant gap)
    2. Has 3+ downstream dependencies (blocks many requirements)
    3. Is in a foundational pillar (Pillars 1, 3, 5 - biological foundations)
    """
    bottleneck_count = 0
    
    # Build dependency graph from pillar_definitions
    dependency_graph = build_dependency_graph(pillar_definitions)
    
    for pillar, pillar_data in gap_report.items():
        is_foundational = pillar in ['Pillar 1', 'Pillar 3', 'Pillar 5']
        
        for req_key, req_data in pillar_data.get('analysis', {}).items():
            for sub_req_key, sub_req_data in req_data.items():
                completeness = sub_req_data.get('completeness_percent', 100)
                
                if completeness >= 40:
                    continue  # Not a significant gap
                
                # Count downstream dependencies
                downstream_count = count_downstream_dependencies(
                    sub_req_key, 
                    dependency_graph
                )
                
                if downstream_count >= 3:
                    bottleneck_count += 1
                    if is_foundational:
                        bottleneck_count += 1  # Double weight for foundational pillars
    
    return bottleneck_count
```

**Interpretation:**
- **0-3:** Few bottlenecks (gaps are independent)
- **4-7:** Moderate bottlenecks (some strategic gaps)
- **8+:** Severe bottlenecks (many critical gaps)

**Trigger Threshold:** ≥5

**Example Calculation:**
```
Sub-1.1.1: 0% coverage, blocks 12 requirements, Pillar 1 (foundational)
  → Count: 2 (1 base + 1 foundational bonus)

Sub-1.2.1: 15% coverage, blocks 5 requirements, Pillar 1 (foundational)
  → Count: 2 (1 base + 1 foundational bonus)

Sub-3.1.1: 20% coverage, blocks 8 requirements, Pillar 3 (foundational)
  → Count: 2 (1 base + 1 foundational bonus)

Sub-2.1.1: 10% coverage, blocks 4 requirements, Pillar 2 (not foundational)
  → Count: 1 (1 base only)

Total Bottleneck Severity = 2 + 2 + 2 + 1 = 7

Verdict: MODERATE-HIGH - enough to contribute to trigger
```

---

### METRIC 4: Coverage Saturation (0.0-1.0)

**Measures:** How "saturated" is the current evidence base? (Are we hitting diminishing returns?)

**Formula:**
```python
def calculate_coverage_saturation(gap_report):
    """
    Saturation = weighted_completeness / 100
    
    Where weighted_completeness considers:
    - Raw completeness percentage
    - Claim density (claims per sub-requirement)
    - Evidence triangulation (multiple sources)
    
    High saturation = Already extracted most value from current corpus
    Low saturation = Still lots of room to extract more
    """
    total_weighted_score = 0
    total_sub_reqs = 0
    
    for pillar, pillar_data in gap_report.items():
        for req_key, req_data in pillar_data.get('analysis', {}).items():
            for sub_req_key, sub_req_data in req_data.items():
                total_sub_reqs += 1
                
                # Component 1: Raw completeness (40% weight)
                completeness = sub_req_data.get('completeness_percent', 0)
                
                # Component 2: Claim density (30% weight)
                contributing_papers = sub_req_data.get('contributing_papers', [])
                claim_count = sum(
                    len(paper.get('claims', [])) 
                    for paper in contributing_papers
                )
                claim_density = min(claim_count / 3, 1.0) * 100  # 3 claims = 100%
                
                # Component 3: Source triangulation (30% weight)
                unique_sources = len(contributing_papers)
                triangulation = min(unique_sources / 3, 1.0) * 100  # 3 sources = 100%
                
                # Weighted score
                weighted_score = (
                    completeness * 0.4 +
                    claim_density * 0.3 +
                    triangulation * 0.3
                )
                
                total_weighted_score += weighted_score
    
    avg_weighted_score = total_weighted_score / total_sub_reqs if total_sub_reqs > 0 else 0
    return avg_weighted_score / 100
```

**Interpretation:**
- **0.0-0.4:** Low saturation (corpus under-utilized, high potential)
- **0.4-0.6:** Moderate saturation (some potential remains)
- **0.6-0.85:** High saturation (diminishing returns setting in)
- **0.85-1.0:** Near-saturation (Deep Review unlikely to help much)

**Trigger Threshold:** <0.6 (inverse - lower is better for Deep Review)

**Example Calculation:**
```
108 sub-requirements

Average raw completeness: 10.5%
Average claim density: 15% (avg 0.5 claims per sub-req, want 3)
Average triangulation: 10% (avg 0.3 sources per sub-req, want 3)

Weighted score per sub-req:
  = 10.5 * 0.4 + 15 * 0.3 + 10 * 0.3
  = 4.2 + 4.5 + 3.0
  = 11.7

Coverage Saturation = 11.7 / 100 = 0.117

Verdict: VERY LOW - lots of room for Deep Review to add value
```

---

### METRIC 5: Expected Claim Yield (Integer Count)

**Measures:** How many new claims can Deep Reviewer realistically find?

**Formula:**
```python
def calculate_expected_claim_yield(gap_report, version_history, research_db):
    """
    Yield = sum of (gap_specific_yield) for all ideal gaps
    
    Gap-specific yield estimation:
    - Base yield: 1.5 claims per (paper × gap) combination
    - Multiplier: Based on paper size, existing claim density
    """
    total_expected_yield = 0
    
    for pillar, pillar_data in gap_report.items():
        for req_key, req_data in pillar_data.get('analysis', {}).items():
            for sub_req_key, sub_req_data in req_data.items():
                completeness = sub_req_data.get('completeness_percent', 100)
                contributing_papers = sub_req_data.get('contributing_papers', [])
                
                # Only consider ideal gaps (0-50% with papers)
                if not (0 <= completeness <= 50 and contributing_papers):
                    continue
                
                for paper in contributing_papers:
                    filename = paper.get('filename')
                    
                    # Get paper metadata
                    paper_row = research_db[research_db['FILENAME'] == filename]
                    if paper_row.empty:
                        continue
                    
                    # Estimate based on paper characteristics
                    page_count = paper_row.iloc[0].get('PAGE_COUNT', 20)
                    existing_claims = count_claims_for_paper(filename, version_history)
                    
                    # Base yield: 1.5 claims per (paper × gap)
                    base_yield = 1.5
                    
                    # Size multiplier: Larger papers = more yield
                    size_multiplier = min(page_count / 20, 2.0)  # Up to 2x for 40+ page papers
                    
                    # Saturation penalty: More existing claims = less yield
                    saturation_penalty = max(0.2, 1.0 - (existing_claims / 10))
                    
                    gap_yield = base_yield * size_multiplier * saturation_penalty
                    total_expected_yield += gap_yield
    
    return int(total_expected_yield)
```

**Interpretation:**
- **0-5:** Low yield (not worth the cost)
- **5-15:** Moderate yield (depends on other metrics)
- **15+:** High yield (likely worth running)

**Trigger Threshold:** ≥15

**Example Calculation:**
```
Ideal gaps: 22 (0-50% coverage with papers)

Gap 1: 1 paper (20 pages, 2 existing claims)
  Base: 1.5
  Size multiplier: 20/20 = 1.0
  Saturation: 1.0 - (2/10) = 0.8
  Yield: 1.5 * 1.0 * 0.8 = 1.2 claims

Gap 2: 2 papers (avg 30 pages, 1 existing claim each)
  Paper A: 1.5 * 1.5 * 0.9 = 2.0 claims
  Paper B: 1.5 * 1.5 * 0.9 = 2.0 claims
  Yield: 4.0 claims

... (repeat for all 22 gaps)

Total Expected Yield = 28 claims

Verdict: HIGH - 28 claims is excellent ROI
```

---

### METRIC 6: Cost-Benefit Ratio (Float)

**Measures:** Expected value gain vs. cost (time + API)

**Formula:**
```python
def calculate_cost_benefit_ratio(expected_claim_yield, gap_report):
    """
    Ratio = expected_benefit / expected_cost
    
    Benefit: Value of closing gaps (weighted by gap criticality)
    Cost: API time + computational time
    """
    # BENEFIT CALCULATION
    # Each new claim closes X% of a gap
    # Critical gaps (bottlenecks) are worth 2x
    # Foundational pillars are worth 1.5x
    
    avg_completeness_gain_per_claim = 15  # Assume each claim adds 15% to a sub-req
    critical_gap_count = count_critical_gaps(gap_report)  # <20% coverage
    foundational_gap_count = count_foundational_gaps(gap_report)  # Pillars 1,3,5
    
    # Value points calculation
    base_value = expected_claim_yield * avg_completeness_gain_per_claim
    
    # Bonus value for critical gaps (assume 30% of claims go to critical gaps)
    critical_bonus = (expected_claim_yield * 0.3) * avg_completeness_gain_per_claim * 1.0
    
    # Bonus for foundational gaps (assume 40% go to foundational)
    foundational_bonus = (expected_claim_yield * 0.4) * avg_completeness_gain_per_claim * 0.5
    
    total_benefit = base_value + critical_bonus + foundational_bonus
    
    # COST CALCULATION
    # Time cost: ~8 minutes per (paper × gap) analysis
    # API cost: ~$0.15 per (paper × gap) at gemini-2.0-flash rates
    
    paper_gap_combinations = count_paper_gap_combinations(gap_report)
    
    time_cost_minutes = paper_gap_combinations * 8
    api_cost_dollars = paper_gap_combinations * 0.15
    
    # Normalize costs to "value points" (1 hour = 100 points, $1 = 10 points)
    time_cost_points = (time_cost_minutes / 60) * 100
    api_cost_points = api_cost_dollars * 10
    
    total_cost = time_cost_points + api_cost_points
    
    # Ratio
    return total_benefit / total_cost if total_cost > 0 else 0.0
```

**Interpretation:**
- **<1.0:** Negative ROI (cost > benefit)
- **1.0-1.5:** Marginal ROI (borderline)
- **1.5-3.0:** Positive ROI (worth doing)
- **3.0+:** Excellent ROI (definitely do it)

**Trigger Threshold:** ≥3.0

**Example Calculation:**
```
Expected claim yield: 28 claims
Average completeness gain: 15% per claim

Benefit:
  Base value: 28 * 15 = 420 points
  Critical bonus: (28 * 0.3) * 15 * 1.0 = 126 points
  Foundational bonus: (28 * 0.4) * 15 * 0.5 = 84 points
  Total benefit: 420 + 126 + 84 = 630 points

Cost:
  Paper-gap combinations: 35
  Time cost: 35 * 8 min = 280 min = 4.67 hours = 467 points
  API cost: 35 * $0.15 = $5.25 = 52.5 points
  Total cost: 467 + 52.5 = 519.5 points

Cost-Benefit Ratio = 630 / 519.5 = 1.21

Verdict: MARGINAL - just barely positive ROI, depends on other factors
```

---

## 3. Implementation in Orchestrator

### 3.1 Integration Point

```python
# In orchestrator.py, after gap analysis is complete

def run_gap_analysis_and_deep_review():
    """
    Enhanced gap analysis with conditional Deep Review trigger.
    """
    logger.info("\n=== STEP 3: GAP ANALYSIS ===")
    
    # Load all data
    version_history = load_version_history(VERSION_HISTORY_FILE)
    research_db = load_research_db(RESEARCH_DB_FILE)
    pillar_definitions = load_pillar_definitions(DEFINITIONS_FILE)
    
    # Run gap analysis
    gap_report = analyze_gaps(version_history, pillar_definitions)
    save_gap_report(gap_report)
    
    logger.info("\n=== DEEP REVIEWER TRIGGER EVALUATION ===")
    
    # Calculate trigger metrics
    should_trigger, trigger_reasons, skip_reasons = evaluate_deep_review_trigger(
        gap_report, 
        version_history, 
        research_db,
        pillar_definitions
    )
    
    # Log decision
    logger.info(f"Deep Review Trigger Decision: {'TRIGGER' if should_trigger else 'SKIP'}")
    
    if trigger_reasons:
        logger.info("Trigger Reasons:")
        for reason in trigger_reasons:
            logger.info(f"  ✓ {reason}")
    
    if skip_reasons:
        logger.info("Skip Reasons:")
        for reason in skip_reasons:
            logger.info(f"  ✗ {reason}")
    
    if should_trigger:
        logger.info("\n=== TRIGGERING DEEP REVIEWER ===")
        safe_print("🎯 Metrics indicate Deep Review will provide positive ROI")
        safe_print(f"   Trigger reasons: {', '.join(trigger_reasons[:3])}")
        
        # Generate directions for ideal gaps
        directions = generate_deep_review_directions(gap_report, version_history)
        save_deep_review_directions(directions)
        
        # Run Deep Reviewer
        from literature_review.reviewers import deep_reviewer
        deep_reviewer.main()
        
        # Re-run Judge to process new claims
        logger.info("\n=== RE-RUNNING JUDGE FOR NEW CLAIMS ===")
        from literature_review.judge import judge
        judge.main()
        
        # Re-calculate gaps with new approved claims
        version_history = load_version_history(VERSION_HISTORY_FILE)
        gap_report = analyze_gaps(version_history, pillar_definitions)
        save_gap_report(gap_report)
        
        logger.info("✅ Deep Review cycle complete. Gap analysis updated.")
    else:
        logger.info("⏭️  Skipping Deep Review (metrics indicate low ROI)")
        safe_print("⏭️  Skipping Deep Review - metrics suggest better to search for new papers")
        if skip_reasons:
            safe_print(f"   Skip reasons: {', '.join(skip_reasons[:2])}")
    
    return gap_report
```

---

### 3.2 Metric Calculation Module

**New File:** `literature_review/analysis/deep_review_triggers.py`

```python
"""
Deep Review Trigger Metrics
Calculates objective metrics to decide whether Deep Reviewer should run.
"""

import logging
from typing import Dict, List, Tuple, Set
import pandas as pd

logger = logging.getLogger(__name__)


class DeepReviewTriggerEvaluator:
    """Evaluates whether Deep Reviewer should be triggered based on objective metrics."""
    
    # Threshold constants
    GAP_OPPORTUNITY_THRESHOLD = 60
    PAPER_REUSE_THRESHOLD = 0.4
    BOTTLENECK_THRESHOLD = 5
    SATURATION_THRESHOLD = 0.6
    CLAIM_YIELD_THRESHOLD = 15
    COST_BENEFIT_THRESHOLD = 3.0
    
    def __init__(self, gap_report: Dict, version_history: Dict, 
                 research_db: pd.DataFrame, pillar_definitions: Dict):
        self.gap_report = gap_report
        self.version_history = version_history
        self.research_db = research_db
        self.pillar_definitions = pillar_definitions
        
    def evaluate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Main evaluation method.
        Returns: (should_trigger, trigger_reasons, skip_reasons)
        """
        metrics = self.calculate_all_metrics()
        
        # Log all metrics
        logger.info("Deep Review Trigger Metrics:")
        logger.info(f"  Gap Opportunity Score: {metrics['gap_opportunity_score']:.1f}/100")
        logger.info(f"  Paper Reuse Efficiency: {metrics['paper_reuse_efficiency']:.1%}")
        logger.info(f"  Bottleneck Severity: {metrics['bottleneck_severity']}")
        logger.info(f"  Coverage Saturation: {metrics['coverage_saturation']:.1%}")
        logger.info(f"  Expected Claim Yield: {metrics['expected_claim_yield']}")
        logger.info(f"  Cost-Benefit Ratio: {metrics['cost_benefit_ratio']:.2f}x")
        
        # Evaluate triggers and blockers
        triggers = []
        blockers = []
        
        # Metric 1: Gap Opportunity
        if metrics['gap_opportunity_score'] >= self.GAP_OPPORTUNITY_THRESHOLD:
            triggers.append(f"High gap opportunity ({metrics['gap_opportunity_score']:.0f}/100)")
        elif metrics['gap_opportunity_score'] < 30:
            blockers.append(f"Low gap opportunity ({metrics['gap_opportunity_score']:.0f}/100)")
        
        # Metric 2: Paper Reuse
        if metrics['paper_reuse_efficiency'] >= self.PAPER_REUSE_THRESHOLD:
            triggers.append(f"High paper reuse potential ({metrics['paper_reuse_efficiency']:.0%})")
        elif metrics['paper_reuse_efficiency'] < 0.2:
            blockers.append(f"Low paper reuse ({metrics['paper_reuse_efficiency']:.0%})")
        
        # Metric 3: Bottlenecks
        if metrics['bottleneck_severity'] >= self.BOTTLENECK_THRESHOLD:
            triggers.append(f"Critical bottlenecks ({metrics['bottleneck_severity']} gaps)")
        
        # Metric 4: Saturation (inverse)
        if metrics['coverage_saturation'] < self.SATURATION_THRESHOLD:
            triggers.append(f"Low saturation ({metrics['coverage_saturation']:.0%}) - room for improvement")
        elif metrics['coverage_saturation'] >= 0.85:
            blockers.append(f"High saturation ({metrics['coverage_saturation']:.0%}) - diminishing returns")
        
        # Metric 5: Claim Yield
        if metrics['expected_claim_yield'] >= self.CLAIM_YIELD_THRESHOLD:
            triggers.append(f"High expected yield ({metrics['expected_claim_yield']} claims)")
        elif metrics['expected_claim_yield'] < 5:
            blockers.append(f"Low expected yield ({metrics['expected_claim_yield']} claims)")
        
        # Metric 6: Cost-Benefit
        if metrics['cost_benefit_ratio'] >= self.COST_BENEFIT_THRESHOLD:
            triggers.append(f"Excellent ROI ({metrics['cost_benefit_ratio']:.1f}x)")
        elif metrics['cost_benefit_ratio'] < 1.5:
            blockers.append(f"Poor ROI ({metrics['cost_benefit_ratio']:.1f}x)")
        
        # DECISION LOGIC
        has_critical_blocker = any(
            'Low paper reuse' in b or 'High saturation' in b 
            for b in blockers
        )
        
        exceptional_metric = any([
            metrics['gap_opportunity_score'] >= 85,
            metrics['paper_reuse_efficiency'] >= 0.7,
            metrics['bottleneck_severity'] >= 10,
            metrics['cost_benefit_ratio'] >= 5.0
        ])
        
        if exceptional_metric:
            should_trigger = True
            triggers.append("EXCEPTIONAL metric detected - override decision")
        elif len(triggers) >= 3 and not has_critical_blocker:
            should_trigger = True
        else:
            should_trigger = False
        
        return should_trigger, triggers, blockers
    
    def calculate_all_metrics(self) -> Dict[str, float]:
        """Calculate all 6 trigger metrics."""
        return {
            'gap_opportunity_score': self._calculate_gap_opportunity(),
            'paper_reuse_efficiency': self._calculate_paper_reuse(),
            'bottleneck_severity': self._calculate_bottleneck_severity(),
            'coverage_saturation': self._calculate_coverage_saturation(),
            'expected_claim_yield': self._calculate_expected_yield(),
            'cost_benefit_ratio': self._calculate_cost_benefit_ratio()
        }
    
    def _calculate_gap_opportunity(self) -> float:
        """METRIC 1: Gap Opportunity Score"""
        total_gaps = 0
        ideal_gaps = 0
        
        for pillar, pillar_data in self.gap_report.items():
            for req_key, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_key, sub_req_data in req_data.items():
                    total_gaps += 1
                    
                    completeness = sub_req_data.get('completeness_percent', 100)
                    contributing_papers = sub_req_data.get('contributing_papers', [])
                    confidence = sub_req_data.get('confidence_level', 'low')
                    
                    # Ideal: 0-50% coverage, has papers, medium+ confidence
                    if (0 <= completeness <= 50 and 
                        len(contributing_papers) >= 1 and
                        confidence in ['medium', 'high']):
                        ideal_gaps += 1
        
        return (ideal_gaps / total_gaps * 100) if total_gaps > 0 else 0
    
    def _calculate_paper_reuse(self) -> float:
        """METRIC 2: Paper Reuse Efficiency"""
        all_papers = set(self.research_db['FILENAME'].tolist())
        reusable_papers = set()
        
        for filename in all_papers:
            # Has approved claims?
            if not self._has_approved_claims(filename):
                continue
            
            # Contributes to under-covered gaps?
            if not self._has_under_covered_gaps(filename):
                continue
            
            # Not exhausted?
            claim_count = self._count_claims_for_paper(filename)
            if claim_count >= 10:
                continue
            
            reusable_papers.add(filename)
        
        return len(reusable_papers) / len(all_papers) if all_papers else 0.0
    
    def _calculate_bottleneck_severity(self) -> int:
        """METRIC 3: Bottleneck Severity"""
        # Simplified version - full version would build dependency graph
        bottleneck_count = 0
        foundational_pillars = ['Pillar 1', 'Pillar 3', 'Pillar 5']
        
        for pillar, pillar_data in self.gap_report.items():
            is_foundational = pillar in foundational_pillars
            
            for req_key, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_key, sub_req_data in req_data.items():
                    completeness = sub_req_data.get('completeness_percent', 100)
                    
                    if completeness < 40:  # Significant gap
                        # Heuristic: Assume foundational + low coverage = bottleneck
                        if is_foundational:
                            bottleneck_count += 2  # Double weight
                        else:
                            bottleneck_count += 1
        
        return bottleneck_count
    
    def _calculate_coverage_saturation(self) -> float:
        """METRIC 4: Coverage Saturation"""
        total_weighted_score = 0
        total_sub_reqs = 0
        
        for pillar, pillar_data in self.gap_report.items():
            for req_key, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_key, sub_req_data in req_data.items():
                    total_sub_reqs += 1
                    
                    # Raw completeness (40% weight)
                    completeness = sub_req_data.get('completeness_percent', 0)
                    
                    # Claim density (30% weight)
                    contributing_papers = sub_req_data.get('contributing_papers', [])
                    claim_count = len(contributing_papers)  # Simplified
                    claim_density = min(claim_count / 3, 1.0) * 100
                    
                    # Triangulation (30% weight)
                    triangulation = min(len(contributing_papers) / 3, 1.0) * 100
                    
                    weighted_score = (
                        completeness * 0.4 +
                        claim_density * 0.3 +
                        triangulation * 0.3
                    )
                    
                    total_weighted_score += weighted_score
        
        avg_score = total_weighted_score / total_sub_reqs if total_sub_reqs > 0 else 0
        return avg_score / 100
    
    def _calculate_expected_yield(self) -> int:
        """METRIC 5: Expected Claim Yield"""
        total_yield = 0
        
        for pillar, pillar_data in self.gap_report.items():
            for req_key, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_key, sub_req_data in req_data.items():
                    completeness = sub_req_data.get('completeness_percent', 100)
                    contributing_papers = sub_req_data.get('contributing_papers', [])
                    
                    # Only ideal gaps
                    if not (0 <= completeness <= 50 and contributing_papers):
                        continue
                    
                    for paper_dict in contributing_papers:
                        filename = paper_dict.get('filename')
                        
                        # Base yield
                        base_yield = 1.5
                        
                        # Size multiplier (simplified - assume avg)
                        size_multiplier = 1.2
                        
                        # Saturation penalty
                        existing_claims = self._count_claims_for_paper(filename)
                        saturation = max(0.2, 1.0 - (existing_claims / 10))
                        
                        total_yield += base_yield * size_multiplier * saturation
        
        return int(total_yield)
    
    def _calculate_cost_benefit_ratio(self) -> float:
        """METRIC 6: Cost-Benefit Ratio"""
        expected_yield = self._calculate_expected_yield()
        
        # Benefit (simplified)
        avg_gain_per_claim = 15
        total_benefit = expected_yield * avg_gain_per_claim
        
        # Cost (simplified)
        paper_gap_combos = self._count_paper_gap_combinations()
        time_cost = (paper_gap_combos * 8 / 60) * 100  # minutes to points
        api_cost = paper_gap_combos * 0.15 * 10  # dollars to points
        total_cost = time_cost + api_cost
        
        return total_benefit / total_cost if total_cost > 0 else 0.0
    
    # Helper methods
    def _has_approved_claims(self, filename: str) -> bool:
        """Check if paper has any approved claims."""
        if filename not in self.version_history:
            return False
        versions = self.version_history[filename]
        for version in versions:
            reqs = version.get('review', {}).get('Requirement(s)', [])
            if any(r.get('status') == 'approved' for r in reqs):
                return True
        return False
    
    def _has_under_covered_gaps(self, filename: str) -> bool:
        """Check if paper contributes to gaps with <80% coverage."""
        for pillar, pillar_data in self.gap_report.items():
            for req_key, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_key, sub_req_data in req_data.items():
                    papers = sub_req_data.get('contributing_papers', [])
                    paper_filenames = [p.get('filename') for p in papers]
                    
                    if filename in paper_filenames:
                        if sub_req_data.get('completeness_percent', 100) < 80:
                            return True
        return False
    
    def _count_claims_for_paper(self, filename: str) -> int:
        """Count total claims for a paper."""
        if filename not in self.version_history:
            return 0
        versions = self.version_history[filename]
        total_claims = 0
        for version in versions:
            reqs = version.get('review', {}).get('Requirement(s)', [])
            total_claims += len(reqs)
        return total_claims
    
    def _count_paper_gap_combinations(self) -> int:
        """Count total (paper × gap) combinations for cost estimation."""
        count = 0
        for pillar, pillar_data in self.gap_report.items():
            for req_key, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_key, sub_req_data in req_data.items():
                    completeness = sub_req_data.get('completeness_percent', 100)
                    papers = sub_req_data.get('contributing_papers', [])
                    if 0 <= completeness <= 50 and papers:
                        count += len(papers)
        return count


def evaluate_deep_review_trigger(gap_report: Dict, version_history: Dict,
                                 research_db: pd.DataFrame, 
                                 pillar_definitions: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to evaluate Deep Review trigger.
    Returns: (should_trigger, trigger_reasons, skip_reasons)
    """
    evaluator = DeepReviewTriggerEvaluator(
        gap_report, version_history, research_db, pillar_definitions
    )
    return evaluator.evaluate()
```

---

## 4. Expected Behavior Scenarios

### Scenario 1: TRIGGER - High Opportunity 🟢

**Conditions:**
- 22 gaps at 0-40% with contributing papers
- 60% of papers can be reused
- 7 critical bottlenecks
- Low saturation (11.7%)
- Expected yield: 28 claims
- Cost-benefit: 3.5x

**Metrics:**
```
Gap Opportunity Score: 65/100 ✓
Paper Reuse Efficiency: 60% ✓
Bottleneck Severity: 7 ✓
Coverage Saturation: 11.7% ✓
Expected Claim Yield: 28 ✓
Cost-Benefit Ratio: 3.5x ✓
```

**Decision:** **TRIGGER** (6/6 metrics positive)

**Output:**
```
🎯 Metrics indicate Deep Review will provide positive ROI
   Trigger reasons: High gap opportunity (65/100), High paper reuse (60%), Critical bottlenecks (7)
   
=== TRIGGERING DEEP REVIEWER ===
Generating directions for 22 high-value gaps...
Running Deep Reviewer...
[Deep Reviewer processes 35 paper-gap combinations]
Found 26 new claims

=== RE-RUNNING JUDGE ===
[Judge processes new claims]
Approved: 22 claims
Rejected: 4 claims

✅ Deep Review cycle complete
   Coverage improved: 10.5% → 18.3% (+7.8%)
   Gaps closed: 22 gaps now have 30-50% coverage
```

---

### Scenario 2: SKIP - Low Reuse ⏭️

**Conditions:**
- Only 1 paper in database
- 72 gaps at 0%, but only 3 have contributing papers
- 15% paper reuse (1/1 paper, but most gaps have no papers)
- Expected yield: 4 claims

**Metrics:**
```
Gap Opportunity Score: 28/100 ✗
Paper Reuse Efficiency: 15% ✗
Bottleneck Severity: 12 ✓
Coverage Saturation: 5% ✓
Expected Claim Yield: 4 ✗
Cost-Benefit Ratio: 0.8x ✗
```

**Decision:** **SKIP** (4/6 metrics negative, critical blocker: low reuse)

**Output:**
```
⏭️  Skipping Deep Review - metrics suggest better to search for new papers
   Skip reasons: Low gap opportunity (28/100), Low paper reuse (15%)
   
💡 RECOMMENDATION: Focus on literature search to build corpus before deep reviewing
   Suggested action: Run literature search for 69 gaps with no contributing papers
```

---

### Scenario 3: TRIGGER - Exceptional Bottleneck ⚡

**Conditions:**
- 15 critical bottlenecks in foundational pillars
- Other metrics mixed (moderate opportunity, low yield)
- But bottleneck severity is EXCEPTIONAL (>90th percentile)

**Metrics:**
```
Gap Opportunity Score: 45/100 (moderate)
Paper Reuse Efficiency: 35% (moderate)
Bottleneck Severity: 15 ⚡ EXCEPTIONAL
Coverage Saturation: 25% ✓
Expected Claim Yield: 12 (moderate)
Cost-Benefit Ratio: 2.1x (moderate)
```

**Decision:** **TRIGGER** (exceptional metric override)

**Output:**
```
🎯 Metrics indicate Deep Review will provide positive ROI
   Trigger reasons: Critical bottlenecks (15), EXCEPTIONAL metric detected - override
   
⚡ STRATEGIC TRIGGER: Bottleneck severity is exceptional
   Rationale: Closing these 15 foundational gaps will unblock 45+ downstream requirements
   
=== TRIGGERING DEEP REVIEWER ===
Prioritizing 15 critical bottleneck gaps...
```

---

### Scenario 4: SKIP - High Saturation 🛑

**Conditions:**
- Already at 85% average coverage
- Papers already heavily analyzed (8-10 claims each)
- Diminishing returns

**Metrics:**
```
Gap Opportunity Score: 35/100 (few gaps remaining)
Paper Reuse Efficiency: 20% ✗
Bottleneck Severity: 2 (few critical gaps)
Coverage Saturation: 87% ✗ CRITICAL BLOCKER
Expected Claim Yield: 6 (low)
Cost-Benefit Ratio: 1.2x ✗
```

**Decision:** **SKIP** (critical blocker: high saturation)

**Output:**
```
⏭️  Skipping Deep Review - metrics suggest diminishing returns
   Skip reasons: High saturation (87%), Low expected yield (6 claims)
   
✅ Current corpus is well-utilized
   Recommendation: Remaining gaps likely require NEW papers, not deeper analysis
   Suggested action: Run targeted literature search for remaining 12 gaps
```

---

## 5. Benefits of Trigger System

### 5.1 Resource Optimization

**Before (Manual):**
- User must decide when to run Deep Reviewer
- Risk of running too early (wasted API calls, low yield)
- Risk of running too late (missed opportunities)
- No objective criteria for decision

**After (Automated Triggers):**
- ✅ System decides based on objective metrics
- ✅ Only runs when ROI is positive
- ✅ Optimal timing (runs when most valuable)
- ✅ Transparent decision (logs show why triggered/skipped)

**Expected Savings:**
- **Time:** 50% reduction in unnecessary Deep Review runs
- **Cost:** 60% reduction in wasted API calls
- **Effectiveness:** 2x improvement in claims per API dollar

---

### 5.2 Strategic Gap Closure

**Before:**
- Deep Review all gaps equally
- Miss high-value bottlenecks
- Waste effort on saturated gaps

**After:**
- ✅ Prioritize bottlenecks automatically
- ✅ Skip saturated gaps
- ✅ Focus on high-ROI targets
- ✅ Maximize impact per run

---

### 5.3 Pipeline Intelligence

**Before:**
- Pipeline is "dumb" - always same steps
- No adaptation to data characteristics
- Manual intervention required

**After:**
- ✅ Pipeline adapts to data state
- ✅ Different paths for different scenarios
- ✅ Self-optimizing workflow
- ✅ Fully automated decision-making

---

## 6. Testing Strategy

### 6.1 Unit Tests for Metrics

```python
# tests/unit/test_deep_review_triggers.py

def test_gap_opportunity_high():
    """Test gap opportunity calculation with many ideal gaps."""
    gap_report = create_mock_gap_report(
        total_gaps=100,
        ideal_gaps=65  # 65% are 0-50% with papers
    )
    evaluator = DeepReviewTriggerEvaluator(gap_report, {}, pd.DataFrame(), {})
    score = evaluator._calculate_gap_opportunity()
    assert score == 65.0

def test_paper_reuse_low():
    """Test paper reuse when no papers have approved claims."""
    research_db = pd.DataFrame({'FILENAME': ['paper1.pdf', 'paper2.pdf']})
    version_history = {}  # No claims yet
    gap_report = {}
    
    evaluator = DeepReviewTriggerEvaluator(gap_report, version_history, research_db, {})
    efficiency = evaluator._calculate_paper_reuse()
    assert efficiency == 0.0  # No reusable papers

def test_trigger_decision_with_exceptional_metric():
    """Test that exceptional metric overrides other blockers."""
    # Setup: Mixed metrics but exceptional bottleneck severity
    gap_report, version_history, research_db, pillar_defs = create_mixed_scenario(
        bottleneck_severity=15  # Exceptional
    )
    
    should_trigger, triggers, blockers = evaluate_deep_review_trigger(
        gap_report, version_history, research_db, pillar_defs
    )
    
    assert should_trigger is True
    assert any('EXCEPTIONAL' in t for t in triggers)
```

---

### 6.2 Integration Tests

```python
# tests/integration/test_deep_review_trigger_integration.py

def test_trigger_skips_when_corpus_empty():
    """Integration test: Skip when no papers to reuse."""
    # Simulate first run: 1 paper, 108 gaps, most at 0%
    orchestrator = create_test_orchestrator(
        papers_count=1,
        gaps_at_zero=105
    )
    
    orchestrator.run_gap_analysis_and_deep_review()
    
    # Verify Deep Reviewer was skipped
    assert orchestrator.deep_review_ran is False
    assert 'Low paper reuse' in orchestrator.skip_reasons

def test_trigger_runs_when_metrics_positive():
    """Integration test: Trigger when all metrics positive."""
    # Simulate ideal scenario: 5 papers, 22 ideal gaps
    orchestrator = create_test_orchestrator(
        papers_count=5,
        ideal_gaps=22,
        paper_reuse_efficiency=0.6
    )
    
    orchestrator.run_gap_analysis_and_deep_review()
    
    # Verify Deep Reviewer was triggered
    assert orchestrator.deep_review_ran is True
    assert orchestrator.new_claims_found > 0
```

---

## 7. Monitoring & Logging

### 7.1 Metric Dashboard

**Output to `gap_analysis_output/deep_review_trigger_metrics.json`:**

```json
{
  "timestamp": "2025-11-16T14:32:15",
  "decision": "TRIGGER",
  "metrics": {
    "gap_opportunity_score": 65.0,
    "paper_reuse_efficiency": 0.60,
    "bottleneck_severity": 7,
    "coverage_saturation": 0.117,
    "expected_claim_yield": 28,
    "cost_benefit_ratio": 3.5
  },
  "trigger_reasons": [
    "High gap opportunity (65/100)",
    "High paper reuse potential (60%)",
    "Critical bottlenecks (7 gaps)",
    "Low saturation (12%) - room for improvement",
    "High expected yield (28 claims)",
    "Excellent ROI (3.5x)"
  ],
  "skip_reasons": [],
  "outcome": {
    "deep_review_ran": true,
    "claims_found": 26,
    "claims_approved": 22,
    "coverage_improvement": 7.8,
    "runtime_minutes": 42.3,
    "api_cost_dollars": 5.20
  }
}
```

---

### 7.2 Console Output

```
=== DEEP REVIEWER TRIGGER EVALUATION ===

Calculating trigger metrics...

Deep Review Trigger Metrics:
  Gap Opportunity Score: 65.0/100
  Paper Reuse Efficiency: 60%
  Bottleneck Severity: 7
  Coverage Saturation: 11.7%
  Expected Claim Yield: 28
  Cost-Benefit Ratio: 3.50x

Deep Review Trigger Decision: TRIGGER

Trigger Reasons:
  ✓ High gap opportunity (65/100)
  ✓ High paper reuse potential (60%)
  ✓ Critical bottlenecks (7 gaps)
  ✓ Low saturation (12%) - room for improvement
  ✓ High expected yield (28 claims)
  ✓ Excellent ROI (3.5x)

🎯 Metrics indicate Deep Review will provide positive ROI
   Expected: 28 new claims, 7.8% coverage improvement
   Cost: ~42 minutes runtime, ~$5 API

=== TRIGGERING DEEP REVIEWER ===
```

---

## 8. Future Enhancements

### 8.1 Machine Learning Predictor

**Train model on historical trigger data:**
- Input: Trigger metrics
- Output: Actual claims found, actual coverage improvement
- Goal: More accurate ROI predictions

### 8.2 Dynamic Threshold Tuning

**Auto-adjust thresholds based on corpus size:**
- Small corpus (< 10 papers): Lower thresholds (more aggressive)
- Large corpus (> 100 papers): Higher thresholds (more selective)

### 8.3 Multi-Stage Triggers

**Progressive Deep Review:**
- Stage 1: Only critical bottlenecks (if bottleneck_severity > 10)
- Stage 2: All ideal gaps (if gap_opportunity > 60)
- Stage 3: Even marginal gaps (if user requests exhaustive analysis)

---

## Conclusion

**The intelligent trigger system transforms Deep Reviewer from a manual tool into an automated pipeline optimization step.**

**Key Advantages:**
1. ✅ **Objective Decision-Making** - No guesswork, metrics-driven
2. ✅ **Resource Efficiency** - Only run when ROI is positive
3. ✅ **Strategic Optimization** - Focus on high-value targets
4. ✅ **Full Automation** - No manual intervention required
5. ✅ **Transparent Logging** - Clear explanation of every decision

**Implementation Effort:** 8-12 hours
**Expected ROI:** 3-5x improvement in Deep Review efficiency

**Recommended Next Steps:**
1. Implement `DeepReviewTriggerEvaluator` class (4 hours)
2. Integrate into orchestrator.py (2 hours)
3. Add unit tests for metrics (2 hours)
4. Add integration tests (2 hours)
5. Run smoke test with trigger system (2 hours)

**Total Effort:** ~12 hours for full implementation and testing
