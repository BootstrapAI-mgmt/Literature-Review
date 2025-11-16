# Integrated Pipeline Flow: Insight-Driven Research

**Date:** 2025-11-16
**Status:** Proposed

---

## 1. Executive Summary

This document outlines the proposed integration of the `Insight Engine` and the `Deep-Reviewer` into the main literature review pipeline. The goal is to evolve the pipeline from a purely quantitative gap analysis tool into a strategic, insight-driven research platform.

The new flow introduces a multi-phase process managed by the `Orchestrator`:
1.  **Phase 1: Baseline Analysis:** Establish the current state of research coverage.
2.  **Phase 2: Strategic Insight:** Analyze the "why" behind the gaps and generate a plan.
3.  **Phase 3: Targeted Execution:** Execute the plan by directing the `Deep-Reviewer` to fill the most critical gaps.

This creates a virtuous cycle where the system learns, strategizes, and executes with increasing precision.

## 2. Proposed Integrated Pipeline Flow

The pipeline will be structured into three distinct phases, orchestrated sequentially.

### Phase 1: Baseline Analysis

This phase focuses on establishing a clear, quantitative understanding of the current research landscape.

*   **Step 1: Initial Judge Review**
    *   **Module:** `Judge`
    *   **Action:** The `Judge` processes all claims currently marked as `pending_judge_review` in `review_version_history.json`.
    *   **Outcome:** A clean set of `approved` and `rejected` claims, providing a solid foundation for analysis.

*   **Step 2: Quantitative Gap Analysis**
    *   **Module:** `Orchestrator` (Gap Analysis function)
    *   **Action:** The orchestrator calculates the research completeness for each sub-requirement based on the `approved` claims.
    *   **Outcome:** The `gap_analysis_report.json` and associated visualizations are generated, showing *what* gaps exist.

### Phase 2: Strategic Insight Generation

This new phase focuses on adding a qualitative layer of understanding on top of the quantitative baseline.

*   **Step 3: Insight Engine Analysis**
    *   **Module:** `Insight Engine` (new module)
    *   **Action:** The `Insight Engine` ingests the `gap_analysis_report.json` and the full `review_version_history.json`. It performs its analysis to determine the strength of evidence, identify consensus or contradiction, and classify gap archetypes.
    *   **Outcome:** A new `insight_analysis_output/` directory containing:
        *   `insight_report.md`: A qualitative summary.
        *   `gap_archetypes.json`: Classification of each gap.
        *   `strategic_recommendations.json`: Actionable next steps, including targeted search queries and focus areas for the `Deep-Reviewer`.

### Phase 3: Targeted Execution

This phase uses the strategic insights to actively and intelligently fill the identified gaps.

*   **Step 4: Directed Deep Review**
    *   **Module:** `Deep-Reviewer`
    *   **Action:** The `Orchestrator` triggers the `Deep-Reviewer`. Crucially, instead of a broad search, the `Deep-Reviewer` is now directed by the `strategic_recommendations.json` from the `Insight Engine`. It focuses its search on the highest-priority gaps identified in Phase 2.
    *   **Outcome:** New, highly relevant claims are found and added to `review_version_history.json` with the status `pending_judge_review`.

### The Virtuous Cycle

The pipeline is now ready to loop. The new claims generated in Step 4 can be reviewed by the `Judge` in the next run (Step 1), leading to an updated gap analysis, which in turn leads to more refined insights and even more targeted execution.

## 3. Data Flow Diagram

```
+-----------------------------+
| review_version_history.json |
+-----------------------------+
      |         ^
      |         | (Adds new claims)
      v         |
+-----------------------------+     +--------------------------------+
|           Judge             |---->|      Orchestrator (Gap          |
|   (Reviews pending claims)  |     |        Analysis)               |
+-----------------------------+     +--------------------------------+
      |                                     |
      | (Updates claim statuses)            | (Creates report)
      v                                     v
+-----------------------------+     +-----------------------------+
| review_version_history.json |<--->|    gap_analysis_report.json   |
+-----------------------------+     +-----------------------------+
      |                                     |
      +-------------------------------------+
      |
      v
+-----------------------------+
|       Insight Engine        |
| (Analyzes gaps & evidence)  |
+-----------------------------+
      |
      | (Creates recommendations)
      v
+-----------------------------+
| strategic_recommendations.json |
+-----------------------------+
      |
      | (Directs search)
      v
+-----------------------------+
|        Deep-Reviewer        |
| (Finds new, targeted claims)|
+-----------------------------+
```

## 4. Orchestrator Modifications

The `pipeline_orchestrator.py` will be modified to manage this new flow. The main execution loop will be updated to reflect these phases:

```python
# Pseudocode for the new orchestrator logic

def run_integrated_pipeline():
    
    # Phase 1: Baseline Analysis
    print("--- Phase 1: Baseline Analysis ---")
    run_judge()
    run_gap_analysis()

    # Phase 2: Strategic Insight
    print("--- Phase 2: Strategic Insight ---")
    run_insight_engine()

    # Phase 3: Targeted Execution
    print("--- Phase 3: Targeted Execution ---")
    if has_strategic_recommendations():
        run_deep_reviewer_in_targeted_mode()
    else:
        print("No strategic recommendations to execute.")

    print("--- Pipeline Cycle Complete ---")

```

This phased approach ensures that each component is used to its maximum potential, creating a smarter, more efficient, and more effective literature review process.
