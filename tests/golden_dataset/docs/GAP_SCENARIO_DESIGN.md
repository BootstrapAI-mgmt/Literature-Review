# Controlled Gap Scenario Design

## Purpose

Gap scenarios are controlled database states designed to test:
1. Correct gap detection (finding gaps that exist)
2. Correct non-gap handling (not flagging covered requirements)
3. Iterative gap closing (Pass 2 paper attribution)
4. Decoy paper rejection (irrelevant paper handling)

## Scenario Structure

### Basic Scenario Template

```yaml
scenario_id: "GAP-SCENARIO-001"
scenario_name: "STDP Learning Rule Gap"
scenario_type: "iterative"  # single, iterative

# Pass 1: Initial State
initial_state:
  papers:
    - paper_id: "NEURO-001"
      provides_coverage:
        - requirement: "REQ-B1.1"
          completeness_contribution: 45
    - paper_id: "NEURO-002"
      provides_coverage:
        - requirement: "REQ-B1.2"
          completeness_contribution: 30
  
  expected_coverage:
    REQ-B1.1: 45
    REQ-B1.2: 30
    REQ-B1.4: 0  # This is the gap
  
  expected_gaps:
    - requirement: "REQ-B1.4"
      expected_severity: "CRITICAL"
      expected_completeness: 0
      must_be_detected: true
      if_not_detected: "critical_error"
  
  expected_non_gaps:
    - requirement: "REQ-B1.1"
      current_completeness: 45
      must_not_be_flagged_as_gap: true
      if_flagged_as_gap: "error"
      reason: "45% exceeds gap threshold"

# Pass 2: Gap-Closing Papers
gap_closing_additions:
  papers:
    - paper_id: "NEURO-003"
      designed_to_close: ["REQ-B1.4"]
      known_claims:
        - claim_text: "Our STDP implementation shows..."
          expected_contribution: 60
      expected_impact:
        REQ-B1.4:
          before: 0
          after: 60
          severity_change: "CRITICAL → MEDIUM"
  
  decoy_papers:
    - paper_id: "CLIMATE-001"  # Wrong domain
      should_not_close: ["REQ-B1.4"]
      reason: "Climate paper, not relevant to neuromorphic"
      if_contributes: "critical_error"
    
    - paper_id: "NEURO-004"  # Same domain, different topic
      should_not_close: ["REQ-B1.4"]
      reason: "Addresses inference, not learning"
      if_contributes: "error"

# Expected Final State
expected_final_state:
  coverage:
    REQ-B1.1: 45
    REQ-B1.2: 30
    REQ-B1.4: 60
  
  gaps_remaining:
    - requirement: "REQ-B1.4"
      severity: "MEDIUM"  # Reduced from CRITICAL
  
  recommendation_changes:
    - requirement: "REQ-B1.4"
      priority_should_decrease: true
      if_still_critical: "error"
```

## Scenario Types

### Type 1: Single-Pass Gap Detection

**Purpose:** Test initial gap identification accuracy

**Structure:**
- Fixed database state with known gaps
- Test gap detection only (no iteration)
- Validate severity classification

**Validation Points:**
- All critical gaps detected
- Non-gaps not flagged
- Severity levels correct

### Type 2: Iterative Gap Closing

**Purpose:** Test multi-pass behavior

**Structure:**
- Pass 1: Initial gaps
- Pass 2: Add gap-closing papers
- Validate gap reduction

**Validation Points:**
- Gaps close appropriately
- Decoy papers rejected
- Recommendations update

### Type 3: Edge Case Scenarios

**Purpose:** Test boundary conditions

**Examples:**
- Requirement at exactly gap threshold (50%)
- Multiple papers partially closing a gap
- Paper closing multiple gaps
- Conflicting evidence

## Minimum Scenario Coverage

| Scenario Type | Count | Purpose |
|--------------|-------|---------|
| Single-Pass Detection | 2 | Basic gap detection |
| Iterative Closing | 2 | Gap closing validation |
| Decoy Rejection | 2 | False positive prevention |
| Edge Cases | 2 | Boundary testing |
| **Total** | 8 | Comprehensive coverage |

## Gap Scenario Execution Protocol

### Pre-Execution
1. Create isolated database state (snapshot/restore)
2. Load only Pass 1 papers
3. Clear any cached analysis results

### Pass 1 Execution
1. Run full pipeline on Pass 1 database
2. Capture gap_analysis_report.json
3. Compare detected gaps to expected_gaps
4. Compare non-flagged requirements to expected_non_gaps
5. Record Pass 1 validation results

### Pass 2 Execution (for iterative scenarios)
1. Add gap-closing papers to database
2. Add decoy papers to database
3. Run pipeline in incremental mode
4. Capture updated gap_analysis_report.json
5. Compare severity changes to expected
6. Verify decoy papers have zero contribution

### Validation Criteria
- Pass 1: 100% of must_be_detected gaps found
- Pass 1: 100% of must_not_be_flagged requirements clean
- Pass 2: All expected severity changes occurred
- Pass 2: Zero contribution from decoy papers
