# Research-Agnostic Architecture: Refactoring Guide

**Date:** December 10, 2025  
**Version:** 2.0  
**Status:** Active Refactoring Guide  
**Previous Version:** 1.0 (November 14, 2025) - See `RESEARCH_AGNOSTIC_ARCHITECTURE_v1_archived.md`

---

## Executive Summary

This document provides a comprehensive guide for refactoring the Literature Review pipeline from a **neuromorphic-computing-specific** implementation to a **research-agnostic** system. The goal is to decouple all domain-specific knowledge from the core processing logic, enabling the pipeline to analyze any research area by providing a research-specific configuration file.

### Current State (December 2025)

The pipeline remains **tightly coupled** to neuromorphic computing research through:
- Hardcoded research topic strings in prompts
- Domain-specific file names (`neuromorphic-research_database.csv`)
- Neuromorphic-specific pillar definitions
- Domain-specific scoring examples in prompts

### Target State

A fully research-agnostic system where:
- All domain knowledge is externalized into configuration files
- Prompts are templated with configurable research context
- File naming follows configurable patterns
- The same codebase supports any research domain

---

## Table of Contents

1. [Current Hardcoded Components Audit](#1-current-hardcoded-components-audit)
2. [Proposed Architecture](#2-proposed-architecture)
3. [Implementation Plan](#3-implementation-plan)
4. [Migration Strategy](#4-migration-strategy)
5. [Testing Strategy](#5-testing-strategy)
6. [Appendix: Original Proposal Status](#appendix-original-proposal-status)

---

## 1. Current Hardcoded Components Audit

### 1.1 Hardcoded Research Topic Strings

The core research topic is embedded directly in prompt strings across multiple modules:

#### `literature_review/reviewers/journal_reviewer.py`

**Location:** Lines 694-697 (Chunk Summary Prompt)
```python
Your task is to read a chunk of a larger academic paper and extract its most 
critical information relevant to neuromorphic computing and brain-inspired AI.

Our core research interest is: "The mapping of human brain functions to machine 
learning frameworks, specifically in the areas of skill acquisition, memory 
consolidation, and stimulus-response, with emphasis on neuromorphic computing 
architectures."
```

**Location:** Line 768 (Enhanced Analysis Prompt)
```python
"The mapping of human brain functions to machine learning frameworks, 
specifically in the areas of skill acquisition, memory consolidation, 
and stimulus-response, with emphasis on neuromorphic computing architectures."
```

**Location:** Line 839 (Non-Journal Topic Extraction)
```python
Our core research topic is: "The mapping of human brain functions to machine 
learning frameworks..."
```

**Impact:** HIGH - These prompts guide AI understanding of relevance across the entire pipeline.

#### `literature_review/reviewers/deep_reviewer.py`

**Location:** Line 707 (Deep Analysis Prompt)
```python
Our core research topic is: "The mapping of human brain functions to machine 
learning frameworks, specifically in the areas of skill acquisition, memory 
consolidation, and stimulus-response, with emphasis on neuromorphic computing 
architectures."
```

**Impact:** HIGH - Affects deep requirement matching and claim extraction.

#### `literature_review/analysis/recommendation.py`

**Location:** Line 189 (Gap Bridge Query Prompt)
```python
You are a PhD-level research assistant specializing in literature review for 
neuromorphic computing and neuroscience.
```

**Impact:** MEDIUM - Affects search query generation for gap filling.

#### `literature_review/analysis/proof_scorecard.py`

**Location:** Lines 166, 428
```python
'goal': 'Integrated neuromorphic system demonstrates biological fidelity...'
return 'Cannot prove neuromorphic framework with current evidence'
```

**Impact:** MEDIUM - Affects proof chain visualization and messaging.

---

### 1.2 Hardcoded File Names

| File | Location | Hardcoded Value |
|------|----------|-----------------|
| `journal_reviewer.py` | Line 65 | `OUTPUT_CSV_FILE = 'neuromorphic-research_database.csv'` |
| `deep_reviewer.py` | Line 45 | `RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'` |
| `orchestrator.py` | Line 63 | `RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'` |
| `recommendation.py` | Line 36 | `RESEARCH_DB_FILE = 'data/processed/neuromorphic-research_database.csv'` |
| `state_manager.py` | Lines 353, 397 | `'database_path': 'neuromorphic-research_database.csv'` |
| `judge.py` | Line 55 | `# DEPRECATED: RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'` |

**Impact:** MEDIUM - Creates coupling and prevents multi-domain support.

---

### 1.3 Domain-Specific Pillar Definitions

**File:** `pillar_definitions.json` (362 lines)

Contains neuromorphic-specific:
- **Vision:** "Create neuromorphic systems..."
- **Core Principles:** "Biological fidelity", "Multi-timescale adaptation"  
- **Keywords:** "neuromorphic", "spiking neural networks", "event-based", "DVS"
- **Requirements:** 31 detailed requirements with neuromorphic-specific sub-requirements
- **Metrics:** Neuromorphic targets (latency, power, sparsity)
- **Validation Criteria:** Neuromorphic benchmarks (N-MNIST, DVS128)

**Usage:** Loaded and passed to prompts throughout the pipeline.

**Impact:** CRITICAL - This is the single largest source of domain knowledge.

---

### 1.4 Domain-Specific Examples in Prompts

**Location:** `journal_reviewer.py`, Line 781
```python
- "CORE_DOMAIN": (String) Primary field (e.g., "Machine Learning", 
  "Neuroscience", "Neuromorphic Engineering").
```

**Impact:** LOW - These are examples but bias AI understanding.

---

### 1.5 Hardcoded Search Context

**Location:** `orchestrator.py`, Lines 1117-1121
```python
# Add neuromorphic/AI context for AI pillars
'query': f'neuromorphic AND ({req_short})',
'rationale': 'Neuromorphic computing context',
```

**Impact:** MEDIUM - Affects search recommendations.

---

## 2. Proposed Architecture

### 2.1 Core Principle: Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: Research Domain Configuration                             │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ research_config.json                                            ││
│  │ - research_topic (primary question)                             ││
│  │ - domain_name, domain_id                                        ││
│  │ - keywords (primary, secondary, exclusion)                      ││
│  │ - scoring_criteria                                              ││
│  │ - file_naming_template                                          ││
│  │ - prompt_context snippets                                       ││
│  └─────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ pillar_definitions.json (per-domain)                            ││
│  │ - Requirements framework                                        ││
│  │ - Metrics & validation criteria                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2: Research-Agnostic Pipeline Core                           │
│  - Document processing (PDF/HTML extraction)                        │
│  - AI orchestration (API calls, rate limiting)                      │
│  - Requirement matching (generic algorithm)                         │
│  - Consensus building (Judge)                                       │
│  - Gap analysis (generic framework)                                 │
│  - Prompts use {config.research_topic} placeholders                 │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3: Infrastructure & Utilities                                │
│  - API management (api_manager.py)                                  │
│  - Caching (global_rate_limiter.py)                                 │
│  - State management (state_manager.py)                              │
│  - File I/O, logging                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Research Configuration Schema

**New File:** `research_config.json`

```json
{
  "schema_version": "1.0.0",
  
  "domain": {
    "id": "neuromorphic-computing",
    "name": "Neuromorphic Computing & Brain-Inspired AI",
    "version": "1.0.0",
    "created_at": "2025-12-10"
  },
  
  "research_topic": {
    "primary": "The mapping of human brain functions to machine learning frameworks, specifically in the areas of skill acquisition, memory consolidation, and stimulus-response, with emphasis on neuromorphic computing architectures.",
    "short_description": "neuromorphic computing and brain-inspired AI",
    "secondary_questions": [
      "How can biological neural mechanisms inform AI architectures?",
      "What energy efficiency gains are achievable with neuromorphic systems?"
    ]
  },
  
  "prompt_context": {
    "researcher_role": "PhD-level research assistant specializing in literature review for neuromorphic computing and neuroscience",
    "domain_focus": "neuromorphic computing and brain-inspired AI",
    "example_domains": ["Machine Learning", "Neuroscience", "Neuromorphic Engineering"],
    "example_subdomains": ["Cognitive Neuroscience", "Deep Learning", "Synaptic Plasticity"],
    "example_keywords": ["Hebbian Learning", "PFC function", "Memory Consolidation"]
  },
  
  "vocabulary": {
    "primary_keywords": [
      "neuromorphic", "spiking neural networks", "event-based",
      "brain-inspired", "spike-timing", "synaptic plasticity"
    ],
    "secondary_keywords": [
      "DVS", "Loihi", "TrueNorth", "SpiNNaker", "STDP", "LIF neurons"
    ],
    "exclusion_keywords": []
  },
  
  "file_naming": {
    "database": "{domain_id}-research_database.csv",
    "non_journal": "{domain_id}-non_journal_database.csv",
    "gap_report": "{domain_id}-gap_analysis_report.json",
    "deep_coverage": "{domain_id}-deep_coverage.json"
  },
  
  "pillar_definitions_file": "pillar_definitions.json",
  
  "scoring": {
    "relevance_thresholds": {
      "highly_relevant": 80,
      "moderately_relevant": 50,
      "tangentially_relevant": 30
    }
  },
  
  "search_context": {
    "default_query_prefix": "neuromorphic",
    "ai_pillar_context": "neuromorphic computing"
  }
}
```

---

### 2.3 Configuration Loader Module

**New File:** `literature_review/config/research_config.py`

```python
"""
Research Configuration Loader

Provides a centralized interface for loading and accessing 
research-domain-specific configuration.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ResearchConfig:
    """Holds loaded research configuration."""
    domain_id: str
    domain_name: str
    research_topic: str
    short_description: str
    researcher_role: str
    domain_focus: str
    example_domains: list
    primary_keywords: list
    secondary_keywords: list
    database_filename: str
    pillar_definitions: dict
    raw_config: dict
    
    @classmethod
    def load(cls, config_path: str = "research_config.json") -> "ResearchConfig":
        """Load research configuration from JSON file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        domain = config['domain']
        topic = config['research_topic']
        prompt_ctx = config['prompt_context']
        vocab = config['vocabulary']
        naming = config['file_naming']
        
        # Load pillar definitions
        pillar_file = config.get('pillar_definitions_file', 'pillar_definitions.json')
        with open(pillar_file, 'r', encoding='utf-8') as f:
            pillar_definitions = json.load(f)
        
        return cls(
            domain_id=domain['id'],
            domain_name=domain['name'],
            research_topic=topic['primary'],
            short_description=topic['short_description'],
            researcher_role=prompt_ctx['researcher_role'],
            domain_focus=prompt_ctx['domain_focus'],
            example_domains=prompt_ctx['example_domains'],
            primary_keywords=vocab['primary_keywords'],
            secondary_keywords=vocab['secondary_keywords'],
            database_filename=naming['database'].format(domain_id=domain['id']),
            pillar_definitions=pillar_definitions,
            raw_config=config
        )
    
    def get_pillar_definitions_str(self) -> str:
        """Return pillar definitions as formatted JSON string for prompts."""
        return json.dumps(self.pillar_definitions, indent=2)


# Global singleton instance
_config: Optional[ResearchConfig] = None

def load_config(config_path: str = "research_config.json") -> ResearchConfig:
    """Load and cache research configuration."""
    global _config
    if _config is None:
        _config = ResearchConfig.load(config_path)
    return _config

def get_config() -> ResearchConfig:
    """Get cached research configuration. Raises if not loaded."""
    if _config is None:
        raise RuntimeError("Research config not loaded. Call load_config() first.")
    return _config

def reset_config():
    """Reset cached config (useful for testing)."""
    global _config
    _config = None
```

---

### 2.4 Refactored Prompt Examples

#### Before (journal_reviewer.py)
```python
def get_chunk_summary_prompt(chunk_text: str, chunk_num: int, 
                             total_chunks: int, pillar_definitions_str: str) -> str:
    return f"""
You are a research summarization agent.
Your task is to read a chunk of a larger academic paper and extract its most 
critical information relevant to neuromorphic computing and brain-inspired AI.

Our core research interest is: "The mapping of human brain functions to machine 
learning frameworks, specifically in the areas of skill acquisition, memory 
consolidation, and stimulus-response, with emphasis on neuromorphic computing 
architectures."
...
"""
```

#### After (journal_reviewer.py)
```python
from literature_review.config.research_config import get_config

def get_chunk_summary_prompt(chunk_text: str, chunk_num: int, 
                             total_chunks: int, pillar_definitions_str: str) -> str:
    config = get_config()
    return f"""
You are a research summarization agent.
Your task is to read a chunk of a larger academic paper and extract its most 
critical information relevant to {config.short_description}.

Our core research interest is: "{config.research_topic}"
...
"""
```

---

### 2.5 Directory Structure (Target State)

```
Literature-Review/
├── research_config.json              # Active research domain configuration
├── pillar_definitions.json           # Active pillar definitions
├── pipeline_config.json              # Pipeline settings (existing)
│
├── domains/                          # Research domain configurations (NEW)
│   ├── neuromorphic-computing/
│   │   ├── research_config.json
│   │   └── pillar_definitions.json
│   ├── quantum-computing/            # Example: different domain
│   │   ├── research_config.json
│   │   └── pillar_definitions.json
│   └── README.md                     # Guide for creating new domains
│
├── literature_review/
│   ├── config/                       # Configuration management (NEW)
│   │   ├── __init__.py
│   │   └── research_config.py        # ResearchConfig class
│   ├── reviewers/
│   │   ├── journal_reviewer.py       # REFACTORED: Uses get_config()
│   │   └── deep_reviewer.py          # REFACTORED: Uses get_config()
│   ├── analysis/
│   │   ├── judge.py                  # REFACTORED
│   │   ├── recommendation.py         # REFACTORED
│   │   ├── proof_scorecard.py        # REFACTORED
│   │   └── requirements.py           # REFACTORED
│   ├── orchestrator.py               # REFACTORED
│   ├── utils/
│   │   └── state_manager.py          # REFACTORED
│   └── ...
│
└── data/
    └── processed/
        └── {domain_id}/              # Domain-specific outputs
            ├── database.csv
            └── gap_analysis/
```

---

## 3. Implementation Plan

### Phase 1: Foundation (Est. 8-12 hours)

| Task | Files | Description |
|------|-------|-------------|
| 1.1 | `literature_review/config/__init__.py` | Create config module |
| 1.2 | `literature_review/config/research_config.py` | Implement ResearchConfig class |
| 1.3 | `research_config.json` | Create initial config from current hardcoded values |
| 1.4 | `tests/test_research_config.py` | Unit tests for config loading |

**Deliverables:**
- ✅ Config module loads and provides research context
- ✅ Existing `pillar_definitions.json` works with new system
- ✅ Tests validate config schema

---

### Phase 2: Core Module Refactoring (Est. 16-24 hours)

| Task | File | Changes Required |
|------|------|------------------|
| 2.1 | `journal_reviewer.py` | Replace 4 hardcoded prompts with config references |
| 2.2 | `deep_reviewer.py` | Replace 1 hardcoded prompt, update file paths |
| 2.3 | `recommendation.py` | Replace researcher role, update file paths |
| 2.4 | `orchestrator.py` | Update file paths, search context |
| 2.5 | `judge.py` | Update any remaining file path references |
| 2.6 | `state_manager.py` | Make database path configurable |
| 2.7 | `proof_scorecard.py` | Replace goal text and error messages |

**Refactoring Pattern:**
```python
# Add at top of each module
from literature_review.config.research_config import get_config

# Replace hardcoded strings
- OUTPUT_CSV_FILE = 'neuromorphic-research_database.csv'
+ OUTPUT_CSV_FILE = get_config().database_filename

# Replace prompt text
- "relevant to neuromorphic computing and brain-inspired AI"
+ f"relevant to {get_config().short_description}"
```

**Deliverables:**
- ✅ All modules use `get_config()` for domain knowledge
- ✅ No hardcoded research topic strings remain
- ✅ File names derive from configuration

---

### Phase 3: Initialization & CLI Updates (Est. 8-12 hours)

| Task | Description |
|------|-------------|
| 3.1 | Update `pipeline_orchestrator.py` to call `load_config()` at startup |
| 3.2 | Add `--config` CLI flag to specify research config file |
| 3.3 | Update dashboard to display active research domain |
| 3.4 | Create domain switching logic for multi-domain support |

**CLI Example:**
```bash
# Use default research_config.json
python pipeline_orchestrator.py

# Use specific domain
python pipeline_orchestrator.py --config domains/quantum-computing/research_config.json
```

---

### Phase 4: Multi-Domain Support (Est. 8-12 hours)

| Task | Description |
|------|-------------|
| 4.1 | Create `domains/` directory structure |
| 4.2 | Create domain README with creation guide |
| 4.3 | Implement domain output isolation (separate data directories) |
| 4.4 | Create example second domain (e.g., `quantum-computing`) |

---

### Phase 5: Testing & Documentation (Est. 8-12 hours)

| Task | Description |
|------|-------------|
| 5.1 | Integration tests with different domain configs |
| 5.2 | Update user documentation |
| 5.3 | Create "Creating a New Research Domain" guide |
| 5.4 | Validate backward compatibility |

---

### Total Estimated Effort: 48-72 hours (2-3 weeks)

---

## 4. Migration Strategy

### 4.1 Backward Compatibility

The refactoring maintains backward compatibility:

1. **Default Config:** If `research_config.json` exists in root, it's used automatically
2. **Fallback:** If config not found, use existing hardcoded values (deprecated warning)
3. **Existing Data:** Current `neuromorphic-research_database.csv` continues to work

### 4.2 Migration Steps

```bash
# Step 1: Create research_config.json from current hardcoded values
cp docs/templates/research_config.template.json research_config.json
# Edit to match current neuromorphic values

# Step 2: Run pipeline - should work identically
python pipeline_orchestrator.py

# Step 3: Gradually refactor modules (one at a time, with tests)

# Step 4: Remove hardcoded fallbacks once all modules migrated
```

### 4.3 Deprecation Warnings

```python
# Add to modules during transition
import warnings

def get_research_topic():
    try:
        return get_config().research_topic
    except RuntimeError:
        warnings.warn(
            "Using hardcoded research topic. Please create research_config.json",
            DeprecationWarning
        )
        return "The mapping of human brain functions to machine learning..."
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# tests/test_research_config.py
def test_config_loads_successfully():
    config = ResearchConfig.load("test_fixtures/valid_config.json")
    assert config.domain_id == "test-domain"
    assert config.research_topic != ""

def test_config_missing_required_fields():
    with pytest.raises(KeyError):
        ResearchConfig.load("test_fixtures/invalid_config.json")

def test_database_filename_generation():
    config = ResearchConfig.load("test_fixtures/valid_config.json")
    assert config.database_filename == "test-domain-research_database.csv"
```

### 5.2 Integration Tests

```python
# tests/integration/test_domain_switching.py
def test_pipeline_with_neuromorphic_domain():
    load_config("domains/neuromorphic-computing/research_config.json")
    # Run pipeline subset
    # Assert outputs use correct domain context

def test_pipeline_with_different_domain():
    load_config("domains/test-domain/research_config.json")
    # Run pipeline subset
    # Assert outputs use different domain context
```

### 5.3 Prompt Validation Tests

```python
def test_prompts_contain_config_values():
    config = load_config()
    prompt = get_chunk_summary_prompt("test", 1, 1, "{}")
    
    assert config.research_topic in prompt
    assert config.short_description in prompt
    assert "neuromorphic" not in prompt  # Unless that's the active domain
```

---

## Appendix: Original Proposal Status

### November 2025 Proposal (v1.0)

The original document (now archived as `RESEARCH_AGNOSTIC_ARCHITECTURE_v1_archived.md`) proposed:
- `ResearchDomainConfig` class with Jinja2 templating
- Full template system with `.jinja2` files
- Complex multi-layer architecture with template directories

### What Was Implemented

**None of the proposed components were implemented:**
- ❌ No `domains/` directory
- ❌ No `ResearchDomainConfig` class
- ❌ No Jinja2 templates
- ❌ No `research_domain_config.json`
- ❌ All hardcoded strings remain in codebase

### v2.0 Simplifications

This updated plan simplifies the approach:
- **No Jinja2:** Use Python f-strings with config variables (simpler, no new dependencies)
- **Single Config File:** One `research_config.json` instead of complex template system
- **Incremental Migration:** Refactor one module at a time with tests
- **Smaller Scope:** Focus on extracting hardcoded values, not building a template engine

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | GitHub Copilot | Initial proposal (Jinja2-based, never implemented) |
| 2.0 | 2025-12-10 | GitHub Copilot | Complete rewrite: current state audit, simplified approach, actionable implementation plan |

---

## Quick Reference: Files to Modify

| Priority | File | Hardcoded Items |
|----------|------|-----------------|
| HIGH | `literature_review/reviewers/journal_reviewer.py` | 4 prompt strings, 1 file path |
| HIGH | `literature_review/reviewers/deep_reviewer.py` | 1 prompt string, 1 file path |
| MEDIUM | `literature_review/orchestrator.py` | 1 file path, search context |
| MEDIUM | `literature_review/analysis/recommendation.py` | 1 prompt string, 1 file path |
| MEDIUM | `literature_review/utils/state_manager.py` | 2 file paths |
| LOW | `literature_review/analysis/proof_scorecard.py` | 2 display strings |
| LOW | `literature_review/analysis/judge.py` | 1 deprecated file path |

---

**Next Steps:**
1. ☐ Review and approve this updated architecture
2. ☐ Create `literature_review/config/` module (Phase 1)
3. ☐ Create `research_config.json` with current neuromorphic values
4. ☐ Begin incremental module refactoring (Phase 2)
