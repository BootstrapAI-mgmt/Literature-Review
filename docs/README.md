# Documentation

This folder contains all project documentation organized by type and purpose.

## 📁 Folder Structure

### `/architecture/`
**Purpose:** Architectural decisions, analysis, and refactoring documentation

**Files:**
- `ARCHITECTURE_ANALYSIS.md` - Comprehensive analysis of codebase architecture
- `ARCHITECTURE_REFACTOR.md` - Repository restructuring plan and implementation guide

**Status:** 🟢 Current (Updated post-PR #11 refactoring)

---

### `/guides/`
**Purpose:** Step-by-step guides and workflow documentation

**Files:**
- `WORKFLOW_EXECUTION_GUIDE.md` - How to run the literature review pipeline
- `PARALLEL_DEVELOPMENT_STRATEGY.md` - Strategy for parallel feature development

**Status:** 🟢 Current

---

### `/status-reports/`
**Purpose:** Progress tracking, completion summaries, and status updates

**Files:**
- `EXECUTION_INFRASTRUCTURE_STATUS.md` - Infrastructure component status
- `TESTING_STATUS_SUMMARY.md` - Test coverage and testing progress
- `TASK_CARD_13.2_COMPLETION_SUMMARY.md` - Retry logic completion
- `TASK_CARD_4_COMPLETION_SUMMARY.md` - Deep coverage decision completion
- `TASK_CARD_UPDATE_COMPLETION_SUMMARY.md` - Task card refactoring completion

**Status:** 🟡 Mixed (some files reflect latest status, others may need updates)

---

### `/assessments/`
**Purpose:** Technical assessments, impact analysis, and evaluation reports

**Files:**
- `INTEGRATION_E2E_TESTING_ASSESSMENT.md` - Integration and E2E testing strategy assessment
- `TEST_ASSESSMENT.md` - Test suite evaluation
- `TASK_CARD_REFACTOR_IMPACT_ASSESSMENT.md` - Impact of refactoring on task cards

**Status:** 🟢 Current

---

## 📄 Root Documentation Files

### Core Documentation
- **`CONSOLIDATED_ROADMAP.md`** - 🟢 **MASTER REFERENCE** - Complete project roadmap with all 23 task cards, wave deployment, and progress tracking (Updated: Nov 13, 2025)
- **`EVIDENCE_ENHANCEMENT_OVERVIEW.md`** - Overview of evidence quality enhancement features
- **`EVIDENCE_EXTRACTION_ENHANCEMENTS.md`** - Detailed evidence extraction improvements
- **`TEST_MODIFICATIONS.md`** - Test modifications for evidence quality features

**Status:** 🟢 Current

---

## 🎯 Most Up-to-Date Documentation

### For Project Planning & Progress:
1. **`CONSOLIDATED_ROADMAP.md`** ⭐ - Primary reference for all task cards and progress
2. **`WORKFLOW_EXECUTION_GUIDE.md`** - How to run the system

### For Architecture:
1. **`architecture/ARCHITECTURE_REFACTOR.md`** ⭐ - Current repository structure
2. **`architecture/ARCHITECTURE_ANALYSIS.md`** - Design decisions

### For Testing:
1. **`TEST_MODIFICATIONS.md`** ⭐ - Enhanced test specifications
2. **`assessments/INTEGRATION_E2E_TESTING_ASSESSMENT.md`** - Testing strategy

### For Evidence Quality:
1. **`EVIDENCE_ENHANCEMENT_OVERVIEW.md`** ⭐ - Feature overview
2. **`EVIDENCE_EXTRACTION_ENHANCEMENTS.md`** - Implementation details

---

## 🔄 Update Frequency

| Category | Update Frequency | Last Updated |
|----------|------------------|--------------|
| Architecture | As needed (major changes) | Nov 13, 2025 (PR #11) |
| Guides | Quarterly or on workflow changes | Nov 13, 2025 |
| Status Reports | Weekly or on milestone completion | Nov 13, 2025 |
| Assessments | On-demand for major decisions | Nov 13, 2025 |
| Evidence Docs | On feature implementation | Nov 13, 2025 |

---

## 📝 Documentation Standards

### Naming Convention
- Use UPPERCASE with underscores: `DOCUMENT_NAME.md`
- Be descriptive and specific
- Include version/date in content (not filename)

### Content Requirements
- Include "Last Updated" date
- Add status indicators (🟢 Current, 🟡 Partial, 🔴 Outdated)
- Cross-reference related documents
- Maintain table of contents for long documents

### Versioning
- Major updates: Create dated snapshot if needed
- Minor updates: Edit in place with "Last Updated" timestamp
- Deprecated docs: Move to `/docs/archive/` (create as needed)

---

**Last Updated:** November 14, 2025  
**Maintained By:** Literature Review Team
