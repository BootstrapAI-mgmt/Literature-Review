# Architecture Proposal: Insight Engine

**Date:** 2025-11-16
**Status:** Proposed

---

## 1. Executive Summary

This document proposes the development of an "Insight Engine," a new component for advanced post-processing and analysis of the literature review data. The current system excels at quantifying research coverage, but the Insight Engine will provide a deeper, more qualitative understanding of the research landscape.

The goal is to move beyond simple completeness metrics and provide actionable insights into the strength of evidence, the nature of research gaps, and strategic recommendations for closing those gaps. This will enable a more effective and targeted research strategy.

## 2. Problem Statement

The current analysis pipeline effectively identifies *what* research gaps exist by calculating completeness percentages. However, it provides limited insight into:

*   **The quality and strength of existing evidence:** A requirement might be "covered" by a single, low-confidence claim, which is different from being supported by multiple, high-quality studies.
*   **The nature of the gaps:** *Why* do certain gaps exist? Are they unexplored, controversial, or do they require novel methodologies?
*   **Actionable next steps:** The current recommendations are high-level. The system could provide more specific guidance on how to address the identified gaps.

## 3. Proposed Solution: The Insight Engine

The Insight Engine will be a new post-processing module that runs after the main data extraction and analysis pipeline. It will take the `review_version_history.json` and the `gap_analysis_report.json` as inputs and produce a new set of analytical outputs.

### 3.1. Key Features

#### 3.1.1. Evidence Strength and Consensus Analysis

*   **Evidence Heatmap:** A matrix visualizing sub-requirements against a new "Evidence Strength Score." This score will be a composite metric based on:
    *   Number of supporting papers.
    *   Reviewer confidence scores.
    *   `Judge`'s verdict (`approved`, `rejected`).
    *   Source of the claim (`journal_reviewer` vs. `deep_reviewer`).
*   **Concordance Analysis:** This analysis will identify and report on:
    *   **High-Consensus Topics:** Requirements supported by multiple independent sources with consistent findings.
    *   **Controversial Topics:** Requirements with conflicting claims or a mix of `approved` and `rejected` evidence.

#### 3.1.2. Thematic Gap Analysis

*   **Gap Archetype Classification:** This feature will classify each identified gap into one of the following archetypes:
    *   **Unexplored:** No significant research found.
    *   **Nascent:** A few early-stage papers exist, but the area is not well-developed.
    *   **Contradictory:** Conflicting evidence exists, preventing a clear conclusion.
    *   **Method-Limited:** Progress is stalled due to limitations in current experimental or analytical methods.
*   **Inter-dependency Analysis:** A graph-based model will be created to map dependencies between sub-requirements. This will allow the engine to identify foundational gaps that may be prerequisites for other research areas.

#### 3.1.3. Actionable Strategic Recommendations

*   **Targeted Research Directives:** For high-priority gaps, the engine will generate specific, actionable research questions. For example, for a "Contradictory" gap, it might suggest an experiment to resolve the conflict.
*   **Automated Search Query Generation:** For "Unexplored" gaps, the engine will generate sophisticated search queries for use in academic search engines.
*   **Expert Identification:** By analyzing the authors of relevant papers, the engine will suggest key researchers or labs to follow or collaborate with.

### 3.2. Architecture and Data Flow

The Insight Engine will be implemented as a new Python script (`insight_engine.py`) that is triggered by the main orchestrator after the gap analysis is complete.

```
+------------------------------+
| review_version_history.json  |
+------------------------------+
              |
              v
+------------------------------+
|   gap_analysis_report.json   |
+------------------------------+
              |
              v
+------------------------------+
|      insight_engine.py       |
+------------------------------+
              |
              v
+------------------------------+
|   /insight_analysis_output/  |
|  - insight_report.md         |
|  - evidence_heatmap.html     |
|  - gap_archetypes.json       |
|  - recommendations.json      |
+------------------------------+
```

## 4. Implementation Plan

A new directory, `insight_analysis_output`, will be created to store the outputs of the Insight Engine.

This proposal will be implemented by creating a new file, `literature_review/analysis/insight_engine.py`, which will contain the logic for the Insight Engine. This script will be integrated into the main pipeline orchestrator.
