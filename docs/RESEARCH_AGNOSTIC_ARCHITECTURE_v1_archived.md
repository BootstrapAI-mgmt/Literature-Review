# Research-Agnostic Architecture Analysis & Generalization Strategy

**Date:** November 14, 2025  
**Version:** 1.0  
**Status:** Architecture Analysis & Proposal

---

## Executive Summary

This document provides a comprehensive analysis of research-specific components within the Literature Review pipeline and proposes a generalization strategy to make the system research-topic agnostic. The goal is to decouple domain-specific knowledge from the core processing logic, enabling the pipeline to analyze any research area by simply providing a research-specific configuration.

**Current State:** The pipeline is tightly coupled to neuromorphic computing research through hardcoded prompts, file names, and domain knowledge.

**Target State:** A fully research-agnostic system where all domain-specific knowledge is externalized into configuration files and can be iterated upon independently of the core pipeline.

---

## Table of Contents

1. [Current Research-Specific Components](#1-current-research-specific-components)
2. [Generalization Strategy](#2-generalization-strategy)
3. [Proposed Architecture](#3-proposed-architecture)
4. [Implementation Roadmap](#4-implementation-roadmap)
5. [Benefits & Trade-offs](#5-benefits--trade-offs)

---

## 1. Current Research-Specific Components

### 1.1 Hardcoded Research Topic Strings

**Location:** Multiple modules with embedded prompts

**Instances Found:**

#### Journal Reviewer (`journal_reviewer.py`)
```python
# Line 660-663: Chunk Summary Prompt
Our core research interest is: "The mapping of human brain functions to machine 
learning frameworks, specifically in the areas of skill acquisition, memory 
consolidation, and stimulus-response, with emphasis on neuromorphic computing 
architectures."

# Line 734: Enhanced Analysis Prompt
"The mapping of human brain functions to machine learning frameworks, 
specifically in the areas of skill acquisition, memory consolidation, 
and stimulus-response, with emphasis on neuromorphic computing architectures."

# Line 805: Non-Journal Topic Extraction Prompt
Our core research topic is: "The mapping of human brain functions to machine 
learning frameworks, specifically in the areas of skill acquisition, memory 
consolidation, and stimulus-response, with emphasis on neuromorphic computing 
architectures."
```

**Impact:** High - These prompts guide the AI's understanding of relevance, scoring, and topic extraction across the entire pipeline.

#### Deep Reviewer (`deep_reviewer.py`)
```python
# Line 681: Deep Analysis Prompt
Our core research topic is: "The mapping of human brain functions to machine 
learning frameworks, specifically in the areas of skill acquisition, memory 
consolidation, and stimulus-response, with emphasis on neuromorphic computing 
architectures."
```

**Impact:** High - Affects deep requirement matching and claim extraction.

---

### 1.2 Research-Specific File Names

**Instances Found:**

#### Database File Names
```python
# journal_reviewer.py, line 61
OUTPUT_CSV_FILE = 'neuromorphic-research_database.csv'

# deep_reviewer.py, line 41
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'

# orchestrator.py, line 57
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'

# recommendation.py, line 37
RESEARCH_DB_FILE = 'data/processed/neuromorphic-research_database.csv'
```

**Impact:** Medium - These are referenced in multiple test files and documentation, creating coupling.

---

### 1.3 Pillar Definitions (Domain-Specific Research Framework)

**File:** `pillar_definitions.json` (311 lines)

**Content:** Neuromorphic computing research framework with 7 pillars:
1. Biological Stimulus-Response
2. AI Stimulus-Response (Bridge)
3. Biological Skill Automatization
4. AI Skill Automatization (Bridge)
5. Biological Memory Systems
6. AI Memory Systems (Bridge)
7. System Integration & Orchestration

**Research-Specific Elements:**
- **Vision:** "Create neuromorphic systems..."
- **Core Principles:** "Biological fidelity", "Multi-timescale adaptation"
- **Keywords:** "neuromorphic", "spiking neural networks", "event-based", "DVS"
- **Requirements:** 31 detailed requirements with sub-requirements
- **Metrics:** Neuromorphic-specific targets (latency, power, sparsity)
- **Validation Criteria:** Neuromorphic benchmarks (N-MNIST, DVS128)

**Usage Pattern:**
```python
# journal_reviewer.py, lines 1513-1517
with open(DEFINITIONS_FILE, 'r', encoding='utf-8') as f:
    pillar_definitions_json = json.load(f)
pillar_definitions_str = json.dumps(pillar_definitions_json, indent=2)

# Passed to prompts throughout the pipeline
prompt = get_enhanced_analysis_prompt(text, metadata, pillar_definitions_str)
```

**Impact:** CRITICAL - This is the single largest source of domain knowledge in the system. It drives:
- Requirement matching
- Claim extraction
- Relevance scoring
- Gap analysis
- Search recommendations

---

### 1.4 Research-Specific Schema & Scoring Fields

**Location:** CSV schema definitions

**Domain-Coupled Fields:**
```python
# journal_reviewer.py, lines 636-656
MASTER_COLUMN_ORDER = [
    # ... standard fields ...
    "CORE_DOMAIN",                        # e.g., "Neuromorphic Engineering"
    "CORE_DOMAIN_RELEVANCE_SCORE",       # Relevance to neuromorphic domain
    "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE",  # Relevance to our specific research
    # ...
]

# Lines 747-750: Scoring definitions in prompt
- "CORE_DOMAIN": (String) Primary field (e.g., "Machine Learning", 
  "Neuroscience", "Neuromorphic Engineering").
- "CORE_DOMAIN_RELEVANCE_SCORE": (Integer 0-100) Paper's depth/quality 
  within its core domain.
- "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE": (Integer 0-100) Relevance of 
  the SUB_DOMAIN to *our* core research topic.
```

**Impact:** Medium - These fields are domain-neutral in structure but semantically coupled to neuromorphic research in scoring criteria.

---

### 1.5 Example Domains & Keywords (In Prompts)

**Location:** Prompt examples

**Instances:**
```python
# journal_reviewer.py, line 747
"e.g., 'Machine Learning', 'Neuroscience', 'Neuromorphic Engineering'"

# journal_reviewer.py, line 811
"e.g., 'Cognitive Neuroscience', 'Deep Learning', 'Synaptic Plasticity'"

# journal_reviewer.py, line 812
"e.g., 'Hebbian Learning', 'MIT 9.40S18', 'PFC function', 'Memory Consolidation'"
```

**Impact:** Low - These are examples, but they bias the AI's understanding of what constitutes a relevant topic.

---

### 1.6 Test Data & Fixtures

**Location:** Test files

**Domain-Specific Test Data:**
```python
# tests/fixtures/test_data_generator.py, lines 36-53
titles = [
    "Neuromorphic Computing with Spiking Neural Networks",
    "Memristive Devices for Brain-Inspired Computing",
    # ...
]
pillars = [
    "Pillar 2: Neuromorphic Hardware",
    # ...
]
domains = ["Neuromorphic Computing", "Spiking Neural Networks"]
```

**Impact:** Low - Test data can be parameterized or generated dynamically.

---

## 2. Generalization Strategy

### 2.1 Core Principle: Separation of Concerns

**Objective:** Separate **what to analyze** (research domain) from **how to analyze** (processing logic).

**Three-Layer Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Research Domain Configuration                 │
│  - Research topic definition                            │
│  - Requirements framework                               │
│  - Domain vocabulary                                    │
│  - Scoring criteria                                     │
│  - Example searches                                     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Research-Agnostic Pipeline Core               │
│  - Document processing                                  │
│  - AI orchestration                                     │
│  - Requirement matching                                 │
│  - Consensus building                                   │
│  - Gap analysis                                         │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Infrastructure & Utilities                    │
│  - API management                                       │
│  - Caching                                              │
│  - Logging                                              │
│  - File I/O                                             │
└─────────────────────────────────────────────────────────┘
```

---

### 2.2 Research Domain Configuration Schema

**New File:** `research_domain_config.json`

```json
{
  "research_domain": {
    "id": "neuromorphic-computing-v1",
    "version": "1.0.0",
    "name": "Neuromorphic Computing & Brain-Inspired AI",
    "created_at": "2025-11-14",
    "description": "Mapping human brain functions to ML frameworks"
  },
  
  "core_research_question": {
    "primary": "The mapping of human brain functions to machine learning frameworks, specifically in the areas of skill acquisition, memory consolidation, and stimulus-response, with emphasis on neuromorphic computing architectures.",
    "secondary_questions": [
      "How can biological neural mechanisms inform AI architectures?",
      "What energy efficiency gains are achievable with neuromorphic systems?",
      "How do spike-based computations compare to traditional ANNs?"
    ]
  },
  
  "requirements_framework": {
    "framework_name": "Seven Pillars Framework",
    "source_file": "pillar_definitions.json",
    "structure": "hierarchical",
    "levels": ["pillar", "requirement", "sub_requirement"],
    "total_requirements": 31,
    "total_sub_requirements": 127
  },
  
  "domain_vocabulary": {
    "core_domains": [
      "Neuromorphic Engineering",
      "Computational Neuroscience",
      "Machine Learning",
      "Neuroscience",
      "Cognitive Science"
    ],
    "primary_keywords": [
      "neuromorphic", "spiking neural networks", "event-based",
      "brain-inspired", "spike-timing", "synaptic plasticity"
    ],
    "secondary_keywords": [
      "DVS", "Loihi", "TrueNorth", "SpiNNaker", "STDP", "LIF neurons"
    ],
    "exclusion_keywords": [
      "non-neural", "purely statistical", "traditional ML without bio-inspiration"
    ]
  },
  
  "scoring_criteria": {
    "relevance_thresholds": {
      "highly_relevant": 80,
      "moderately_relevant": 50,
      "tangentially_relevant": 30,
      "not_relevant": 0
    },
    "domain_prioritization": {
      "Neuromorphic Engineering": 1.0,
      "Computational Neuroscience": 0.9,
      "Machine Learning": 0.7,
      "Neuroscience": 0.8,
      "Cognitive Science": 0.6
    }
  },
  
  "prompt_templates": {
    "chunk_summary": "templates/chunk_summary_prompt.txt",
    "paper_analysis": "templates/paper_analysis_prompt.txt",
    "requirement_matching": "templates/requirement_matching_prompt.txt",
    "gap_analysis": "templates/gap_analysis_prompt.txt"
  },
  
  "file_paths": {
    "database": "{{domain_id}}_database.csv",
    "non_journal": "{{domain_id}}_non_journal.csv",
    "definitions": "{{domain_id}}_definitions.json",
    "gap_report": "{{domain_id}}_gap_analysis.json"
  },
  
  "validation_datasets": [
    "N-MNIST",
    "DVS128 Gesture",
    "NCALTECH101",
    "DvsGesture"
  ],
  
  "example_searches": [
    "spiking neural networks hardware implementation",
    "neuromorphic computing energy efficiency",
    "brain-inspired learning algorithms"
  ]
}
```

**Usage Pattern:**
```python
# Load research domain configuration
config = ResearchDomainConfig.load('research_domain_config.json')

# Use in prompts
prompt = f"""
Our core research topic is: {config.core_research_question.primary}

Research Framework:
{config.requirements_framework.to_string()}
"""
```

---

### 2.3 Prompt Template System

**New Directory:** `templates/prompts/`

**Template Structure:**
```
templates/
├── prompts/
│   ├── chunk_summary.jinja2
│   ├── paper_analysis.jinja2
│   ├── requirement_matching.jinja2
│   ├── judge_evaluation.jinja2
│   ├── gap_analysis.jinja2
│   └── search_recommendation.jinja2
├── schemas/
│   ├── paper_review_schema.json
│   └── claim_schema.json
└── examples/
    ├── high_relevance_paper.json
    └── low_relevance_paper.json
```

**Example Template:** `chunk_summary.jinja2`
```jinja2
You are analyzing academic literature for the following research domain:

**Research Topic:**
{{ research_domain.core_research_question.primary }}

**Research Framework:**
{{ research_domain.requirements_framework | to_json(indent=2) }}

**Domain Keywords:**
Primary: {{ research_domain.domain_vocabulary.primary_keywords | join(", ") }}
Secondary: {{ research_domain.domain_vocabulary.secondary_keywords | join(", ") }}

**Your Task:**
Extract information relevant to the above research topic from the following text chunk.

**Chunk {{ chunk_num }} of {{ total_chunks }}:**
{{ chunk_text }}

**Required Output Fields:**
{{ output_schema | to_json(indent=2) }}
```

**Benefits:**
- ✅ Prompts version-controlled separately from code
- ✅ Easy A/B testing of prompt variations
- ✅ Non-developers can iterate on prompts
- ✅ Multi-language support (if needed)
- ✅ Consistent formatting across modules

---

### 2.4 ResearchDomainConfig Class

**New Module:** `literature_review/config/research_domain.py`

```python
"""
Research Domain Configuration Management
Provides a research-agnostic interface to domain-specific knowledge.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from jinja2 import Environment, FileSystemLoader

@dataclass
class CoreResearchQuestion:
    primary: str
    secondary_questions: List[str] = field(default_factory=list)

@dataclass
class RequirementsFramework:
    framework_name: str
    source_file: str
    structure: str  # 'hierarchical', 'flat', 'matrix'
    levels: List[str]
    data: Dict = field(default_factory=dict)
    
    def to_string(self, indent: int = 2) -> str:
        """Convert framework to formatted string for prompts."""
        return json.dumps(self.data, indent=indent)
    
    def get_requirement(self, path: str) -> Optional[str]:
        """
        Get requirement by path (e.g., 'Pillar 1/REQ-B1.1/Sub-1.1.1').
        """
        parts = path.split('/')
        current = self.data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

@dataclass
class DomainVocabulary:
    core_domains: List[str]
    primary_keywords: List[str]
    secondary_keywords: List[str]
    exclusion_keywords: List[str] = field(default_factory=list)

@dataclass
class ScoringCriteria:
    relevance_thresholds: Dict[str, int]
    domain_prioritization: Dict[str, float]

class ResearchDomainConfig:
    """
    Central configuration for a research domain.
    Loads and manages all domain-specific knowledge.
    """
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self._load_config()
        self._load_templates()
    
    def _load_config(self):
        """Load main configuration file."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse configuration sections
        self.domain_id = data['research_domain']['id']
        self.domain_name = data['research_domain']['name']
        self.version = data['research_domain']['version']
        
        self.core_research_question = CoreResearchQuestion(
            primary=data['core_research_question']['primary'],
            secondary_questions=data['core_research_question'].get('secondary_questions', [])
        )
        
        # Load requirements framework
        req_data = data['requirements_framework']
        framework_file = self.config_dir / req_data['source_file']
        with open(framework_file, 'r', encoding='utf-8') as f:
            framework_content = json.load(f)
        
        self.requirements_framework = RequirementsFramework(
            framework_name=req_data['framework_name'],
            source_file=req_data['source_file'],
            structure=req_data['structure'],
            levels=req_data['levels'],
            data=framework_content
        )
        
        self.domain_vocabulary = DomainVocabulary(**data['domain_vocabulary'])
        self.scoring_criteria = ScoringCriteria(**data['scoring_criteria'])
        
        # File path templates
        self.file_paths = data['file_paths']
        self.validation_datasets = data.get('validation_datasets', [])
        self.example_searches = data.get('example_searches', [])
    
    def _load_templates(self):
        """Load Jinja2 prompt templates."""
        template_dir = self.config_dir / 'templates' / 'prompts'
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
        
        # Add custom filters
        self.jinja_env.filters['to_json'] = lambda x, **kwargs: json.dumps(x, **kwargs)
    
    def render_prompt(self, template_name: str, **kwargs) -> str:
        """
        Render a prompt template with domain configuration.
        
        Args:
            template_name: Name of template file (e.g., 'chunk_summary.jinja2')
            **kwargs: Additional variables for template
        
        Returns:
            Rendered prompt string
        """
        template = self.jinja_env.get_template(template_name)
        
        # Inject research domain config into template context
        context = {
            'research_domain': self,
            **kwargs
        }
        
        return template.render(**context)
    
    def get_database_path(self) -> str:
        """Get path to main research database for this domain."""
        return self.file_paths['database'].replace('{{domain_id}}', self.domain_id)
    
    def get_definitions_path(self) -> str:
        """Get path to requirements definitions for this domain."""
        return self.file_paths['definitions'].replace('{{domain_id}}', self.domain_id)
    
    def is_keyword_match(self, text: str, threshold: str = 'primary') -> bool:
        """
        Check if text contains domain keywords.
        
        Args:
            text: Text to check
            threshold: 'primary' or 'secondary' keyword list
        
        Returns:
            True if keywords found
        """
        keywords = (self.domain_vocabulary.primary_keywords 
                   if threshold == 'primary' 
                   else self.domain_vocabulary.secondary_keywords)
        
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)
    
    def calculate_domain_score(self, domain: str) -> float:
        """
        Get prioritization weight for a given domain.
        
        Args:
            domain: Domain name
        
        Returns:
            Weight (0.0 to 1.0), default 0.5 if not specified
        """
        return self.scoring_criteria.domain_prioritization.get(domain, 0.5)


# Global instance (loaded at startup)
_research_config: Optional[ResearchDomainConfig] = None

def load_research_config(config_path: str = 'research_domain_config.json') -> ResearchDomainConfig:
    """Load and cache research domain configuration."""
    global _research_config
    if _research_config is None:
        _research_config = ResearchDomainConfig(config_path)
    return _research_config

def get_research_config() -> ResearchDomainConfig:
    """Get cached research domain configuration."""
    if _research_config is None:
        raise RuntimeError("Research domain configuration not loaded. Call load_research_config() first.")
    return _research_config
```

---

### 2.5 Refactored Module Integration

**Example: Journal Reviewer Refactoring**

**Before (journal_reviewer.py, lines 656-663):**
```python
def get_chunk_summary_prompt(chunk_text: str, chunk_num: int, 
                             total_chunks: int, pillar_definitions_str: str) -> str:
    return f"""
You are analyzing academic literature...

Our core research interest is: "The mapping of human brain functions to machine 
learning frameworks, specifically in the areas of skill acquisition, memory 
consolidation, and stimulus-response, with emphasis on neuromorphic computing 
architectures."

--- REQUIREMENTS FRAMEWORK ---
{pillar_definitions_str}
...
"""
```

**After (journal_reviewer.py, refactored):**
```python
from literature_review.config.research_domain import get_research_config

def get_chunk_summary_prompt(chunk_text: str, chunk_num: int, total_chunks: int) -> str:
    """
    Generate chunk summary prompt using research domain configuration.
    
    NOTE: No longer takes pillar_definitions_str as parameter.
    All domain knowledge comes from ResearchDomainConfig.
    """
    config = get_research_config()
    
    return config.render_prompt(
        'chunk_summary.jinja2',
        chunk_text=chunk_text,
        chunk_num=chunk_num,
        total_chunks=total_chunks,
        output_schema=CHUNK_SUMMARY_SCHEMA
    )
```

**Benefits:**
- ✅ **Prompt externalized:** Can be modified without code changes
- ✅ **Domain decoupled:** No hardcoded research topic
- ✅ **Testable:** Can inject different configs for testing
- ✅ **Reusable:** Same template system across all modules

---

## 3. Proposed Architecture

### 3.1 Directory Structure (After Refactoring)

```
Literature-Review/
├── domains/                          # Research domain configurations
│   ├── neuromorphic-computing-v1/    # Current domain
│   │   ├── config.json              # Domain configuration
│   │   ├── definitions.json         # Pillar definitions (renamed)
│   │   ├── templates/               # Domain-specific prompt templates
│   │   │   ├── chunk_summary.jinja2
│   │   │   ├── paper_analysis.jinja2
│   │   │   ├── requirement_matching.jinja2
│   │   │   ├── judge_evaluation.jinja2
│   │   │   └── gap_analysis.jinja2
│   │   ├── schemas/                 # JSON schemas for validation
│   │   │   ├── paper_review.json
│   │   │   └── claim.json
│   │   └── examples/                # Example outputs for testing
│   │       ├── high_relevance.json
│   │       └── low_relevance.json
│   ├── quantum-computing-v1/         # Example: Different research domain
│   │   ├── config.json
│   │   ├── definitions.json
│   │   └── templates/
│   └── medical-ai-v1/                # Example: Another domain
│       ├── config.json
│       ├── definitions.json
│       └── templates/
├── literature_review/                # Core pipeline (research-agnostic)
│   ├── config/                       # Configuration management
│   │   ├── __init__.py
│   │   ├── research_domain.py       # ResearchDomainConfig class (NEW)
│   │   └── pipeline_config.py       # Pipeline settings (existing)
│   ├── reviewers/
│   │   ├── journal_reviewer.py      # REFACTORED: Uses ResearchDomainConfig
│   │   └── deep_reviewer.py         # REFACTORED: Uses ResearchDomainConfig
│   ├── analysis/
│   │   ├── judge.py                 # REFACTORED: Uses ResearchDomainConfig
│   │   ├── requirements.py          # REFACTORED: Uses ResearchDomainConfig
│   │   └── recommendation.py        # REFACTORED: Uses ResearchDomainConfig
│   ├── orchestrator.py              # REFACTORED: Loads research domain
│   └── utils/
│       └── prompt_renderer.py       # Jinja2 template utilities (NEW)
├── data/
│   ├── raw/                          # Input PDFs
│   └── processed/
│       └── neuromorphic-computing-v1/  # Domain-specific outputs
│           ├── database.csv
│           ├── non_journal.csv
│           └── gap_analysis.json
└── tests/
    ├── domains/                      # Domain-specific test fixtures
    │   └── neuromorphic-computing-v1/
    │       └── test_papers/
    └── integration/
        └── test_domain_switching.py  # Test switching between domains
```

---

### 3.2 Workflow with Research-Agnostic Architecture

**1. Initialize Pipeline with Research Domain**

```python
# main.py or orchestrator.py
from literature_review.config.research_domain import load_research_config
from literature_review.orchestrator import run_pipeline

# Load research domain configuration
config = load_research_config('domains/neuromorphic-computing-v1/config.json')

# Run pipeline (all modules now use config automatically)
run_pipeline(
    papers_dir='data/raw',
    output_dir=f'data/processed/{config.domain_id}'
)
```

**2. Modules Pull Domain Knowledge Automatically**

```python
# journal_reviewer.py (simplified example)
from literature_review.config.research_domain import get_research_config

class PaperAnalyzer:
    @staticmethod
    def analyze_paper(text: str, metadata: dict) -> dict:
        config = get_research_config()
        
        # Render prompt using domain configuration
        prompt = config.render_prompt(
            'paper_analysis.jinja2',
            paper_text=text,
            metadata=metadata
        )
        
        # Call AI API
        response = api_manager.generate_content(prompt)
        
        # Parse and return
        return json.loads(response.text)
```

**3. Switching Research Domains**

```bash
# Analyze neuromorphic computing papers
python run_pipeline.py --domain neuromorphic-computing-v1

# Analyze quantum computing papers (different research area)
python run_pipeline.py --domain quantum-computing-v1

# Analyze medical AI papers
python run_pipeline.py --domain medical-ai-v1
```

**Each domain has:**
- Own research questions
- Own requirements framework
- Own keywords and vocabulary
- Own scoring criteria
- Own prompt templates
- Own output directory

**Core pipeline remains unchanged** - it just pulls configuration from the specified domain.

---

### 3.3 Iterative Prompt Development Workflow

**Current (Problematic):**
```
Developer modifies prompt in Python code
    ↓
Commits code change
    ↓
Run full pipeline to test
    ↓
Realize prompt needs adjustment
    ↓
Repeat (slow, requires code changes)
```

**With Research-Agnostic Architecture:**
```
Research Lead modifies prompt template (Jinja2 file)
    ↓
No code change needed - just file edit
    ↓
Run pipeline with new template
    ↓
Compare results (A/B testing)
    ↓
Iterate quickly (no commits, no code review)
    ↓
When satisfied, commit template change
```

**Benefits:**
- ✅ Non-developers can iterate on prompts
- ✅ Faster iteration cycle (no code changes)
- ✅ A/B testing by swapping template files
- ✅ Version control for prompts (Git tracks template changes)
- ✅ Rollback to previous prompts easily

---

### 3.4 Multi-Domain Support

**Use Case:** Research group analyzing multiple topics

**Setup:**
```bash
domains/
├── neuromorphic-computing-v1/
│   ├── config.json
│   └── templates/
├── quantum-computing-v1/
│   ├── config.json
│   └── templates/
└── medical-ai-v1/
    ├── config.json
    └── templates/
```

**Running Different Analyses:**
```bash
# Monday: Neuromorphic research
python run_pipeline.py --domain neuromorphic-computing-v1 --input papers/neuro/

# Tuesday: Quantum research
python run_pipeline.py --domain quantum-computing-v1 --input papers/quantum/

# Wednesday: Medical AI research
python run_pipeline.py --domain medical-ai-v1 --input papers/medical/
```

**Each maintains separate:**
- Databases
- Gap analyses
- Recommendations
- Version histories

**Shared infrastructure:**
- API management
- Caching
- Logging
- Test framework

---

## 4. Implementation Roadmap

### Phase 1: Foundation (Week 1-2) - 40-60 hours

**Tasks:**
1. **Create ResearchDomainConfig class** (8 hours)
   - Implement `research_domain.py` module
   - Add JSON schema validation
   - Write unit tests

2. **Extract neuromorphic config** (12 hours)
   - Create `domains/neuromorphic-computing-v1/config.json`
   - Migrate `pillar_definitions.json` to domain directory
   - Extract all hardcoded prompts to text files

3. **Implement prompt template system** (8 hours)
   - Set up Jinja2 templates
   - Create base templates for all major prompts
   - Add template rendering utilities

4. **Create template library** (16 hours)
   - Convert all 8 major prompts to Jinja2 templates
   - Add schema validation for prompt outputs
   - Create example outputs for testing

5. **Testing infrastructure** (8 hours)
   - Parametric tests for multiple domains
   - Mock domain configurations for testing
   - Integration tests for config loading

**Deliverables:**
- ✅ `ResearchDomainConfig` class fully functional
- ✅ `neuromorphic-computing-v1` domain fully configured
- ✅ All prompts externalized to templates
- ✅ Test suite passing with new architecture

---

### Phase 2: Refactor Core Modules (Week 3-4) - 60-80 hours

**Tasks:**
1. **Refactor Journal Reviewer** (16 hours)
   - Remove hardcoded prompts
   - Use `get_research_config()` for all domain knowledge
   - Update database file paths
   - Maintain backward compatibility

2. **Refactor Deep Reviewer** (12 hours)
   - Same refactoring as Journal Reviewer
   - Update DRA integration

3. **Refactor Judge** (16 hours)
   - Update judgment prompts
   - Refactor consensus logic to use config
   - Update version history integration

4. **Refactor DRA (Requirements Analyzer)** (12 hours)
   - Template-based requirement matching
   - Domain-agnostic claim extraction

5. **Refactor Recommendation Engine** (12 hours)
   - Template-based gap analysis
   - Domain-configurable search queries

6. **Refactor Orchestrator** (12 hours)
   - Load research domain at startup
   - Pass config to all stages
   - Update file path management

**Deliverables:**
- ✅ All 6 core modules refactored
- ✅ No hardcoded domain knowledge in code
- ✅ All tests passing (green across the board)
- ✅ Documentation updated

---

### Phase 3: Testing & Validation (Week 5) - 30-40 hours

**Tasks:**
1. **Create test domain** (8 hours)
   - Set up `quantum-computing-v1` as proof-of-concept
   - Create minimal requirements framework
   - Test full pipeline with new domain

2. **A/B testing framework** (8 hours)
   - Tool for comparing prompt variations
   - Metrics for prompt effectiveness
   - Automated comparison reports

3. **Integration testing** (8 hours)
   - End-to-end tests with different domains
   - Domain switching validation
   - Backward compatibility verification

4. **Performance testing** (8 hours)
   - Ensure no performance degradation
   - Template rendering overhead measurement
   - Cache effectiveness validation

**Deliverables:**
- ✅ Second domain successfully analyzed
- ✅ A/B testing framework operational
- ✅ Performance validated (< 5% overhead)
- ✅ Full test suite passing

---

### Phase 4: Documentation & Training (Week 6) - 20-30 hours

**Tasks:**
1. **User guide for creating new domains** (8 hours)
   - Step-by-step domain creation guide
   - Template examples
   - Best practices

2. **Prompt engineering guide** (8 hours)
   - How to write effective research prompts
   - Jinja2 template syntax
   - Common pitfalls

3. **Migration guide** (6 hours)
   - How to migrate existing research to new architecture
   - Backward compatibility notes
   - Troubleshooting

4. **API documentation** (6 hours)
   - ResearchDomainConfig API reference
   - Template variable reference
   - Configuration schema documentation

**Deliverables:**
- ✅ Comprehensive documentation
- ✅ Training materials for research leads
- ✅ Examples and tutorials

---

### Total Estimated Effort: 150-210 hours (4-6 weeks)

---

## 5. Benefits & Trade-offs

### 5.1 Benefits

#### For Researchers
1. **Domain Flexibility**
   - Analyze any research area without code changes
   - Switch between research topics seamlessly
   - Maintain multiple research domains simultaneously

2. **Rapid Prompt Iteration**
   - Edit prompts without coding knowledge
   - A/B test different prompt strategies
   - Version control for research methodology

3. **Collaborative Research**
   - Multiple researchers can work on different domains
   - Share domain configurations easily
   - Reproduce analyses exactly

4. **Quality Improvement**
   - Focus on research questions, not implementation
   - Iterate on prompts based on results
   - Continuous refinement of domain knowledge

#### For Developers
1. **Code Maintainability**
   - Single responsibility: code processes, config defines domain
   - Easier testing (mock different domains)
   - Reduced coupling

2. **Extensibility**
   - Add new domains without touching core code
   - Easy to add new prompt templates
   - Plugin-like architecture

3. **Debugging**
   - Isolate prompt issues from code issues
   - Compare domain configurations easily
   - Clear separation of concerns

#### For the System
1. **Scalability**
   - Support multiple research domains
   - Parallel processing of different domains
   - Reusable infrastructure

2. **Quality Assurance**
   - Consistent prompt structure across domains
   - Schema validation for all outputs
   - Reproducible results

3. **Future-Proofing**
   - Easy to adapt to new research areas
   - Prompt evolution without code changes
   - Support for emerging research methodologies

---

### 5.2 Trade-offs

#### Increased Complexity
- **Before:** Everything in Python files
- **After:** Configuration files + templates + Python code
- **Mitigation:** Clear documentation, examples, and training

#### Initial Development Effort
- **Cost:** 150-210 hours upfront
- **Benefit:** Saves time on every future domain or prompt change
- **ROI:** Break-even after ~3-5 domain configurations or major prompt iterations

#### Learning Curve
- **Challenge:** Researchers need to learn Jinja2 template syntax
- **Mitigation:** Simple templates, examples, and documentation
- **Reality:** Jinja2 is simpler than Python for non-developers

#### Indirection
- **Before:** Read prompt directly in code
- **After:** Read template file, understand variable substitution
- **Mitigation:** IDE support, clear naming, inline documentation

---

### 5.3 Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Template rendering errors | HIGH | MEDIUM | Schema validation, comprehensive testing |
| Breaking existing workflows | HIGH | LOW | Backward compatibility layer, gradual migration |
| Performance overhead | MEDIUM | LOW | Template caching, benchmarking |
| Configuration errors | MEDIUM | MEDIUM | JSON schema validation, clear error messages |
| Resistance to change | MEDIUM | MEDIUM | Training, documentation, demonstrable benefits |

---

## 6. Next Steps

### Immediate Actions (This Week)

1. **Review & Approve Architecture**
   - Team review of this document
   - Identify any missing requirements
   - Approve high-level design

2. **Create Proof-of-Concept**
   - Implement minimal `ResearchDomainConfig` class
   - Convert one prompt to Jinja2 template
   - Demonstrate end-to-end with template

3. **Define Second Domain**
   - Choose second research area (e.g., Quantum Computing)
   - Draft minimal requirements framework
   - Validate architecture meets needs

### Short-Term (Weeks 1-2)

1. **Phase 1 Implementation**
   - Build `ResearchDomainConfig` class
   - Create neuromorphic domain configuration
   - Set up template system

2. **Pilot Refactoring**
   - Refactor Journal Reviewer as pilot
   - Validate approach works
   - Gather team feedback

### Medium-Term (Weeks 3-6)

1. **Complete Refactoring**
   - All core modules refactored
   - Full test suite passing
   - Documentation complete

2. **Second Domain Launch**
   - Complete second domain configuration
   - Run full pipeline on new domain
   - Validate research-agnostic architecture

### Long-Term (Months 2-3)

1. **External Collaboration**
   - Share architecture with research community
   - Collect domain configurations from collaborators
   - Build library of research domains

2. **Advanced Features**
   - Prompt A/B testing dashboard
   - Automated prompt optimization
   - Multi-domain meta-analysis

---

## 7. Conclusion

The proposed research-agnostic architecture represents a fundamental shift from a **neuromorphic-specific pipeline** to a **general-purpose literature review system**. By externalizing all domain knowledge into configuration files and templates, we enable:

1. **Rapid domain switching** - Analyze any research area
2. **Iterative prompt development** - Non-developers can refine prompts
3. **Multi-domain support** - Parallel research projects
4. **Long-term maintainability** - Separation of concerns

The upfront investment of 150-210 hours will pay dividends through:
- Faster prompt iteration (hours vs. days)
- Support for multiple research domains
- Easier onboarding of new researchers
- Cleaner, more maintainable codebase

**Recommendation:** Proceed with Phase 1 implementation to validate the architecture with a proof-of-concept before committing to full refactoring.

---

**Document Version:** 1.0  
**Last Updated:** November 14, 2025  
**Authors:** GitHub Copilot  
**Status:** Proposal - Awaiting Team Review
