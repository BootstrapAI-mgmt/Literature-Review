# RESEARCH_AGNOSTIC_PHASE_5: Comprehensive Testing & Documentation

**Status:** NOT STARTED  
**Priority:** 🟢 Low  
**Effort Estimate:** 6-8 hours  
**Category:** Research-Agnostic Architecture  
**Created:** December 10, 2025  
**Related:** RESEARCH_AGNOSTIC_ARCHITECTURE.md v2.0

---

## 📋 Overview

Complete the research-agnostic architecture with comprehensive testing, documentation updates, and a migration guide for users transitioning from hardcoded to configurable research domains.

**Current State:**
- Phases 1-3 complete: Config module, module refactoring, CLI flag
- Phase 4 (output isolation) planned
- Documentation partially updated (architecture doc v2.0)
- No integration tests for multi-domain scenarios
- No user-facing migration guide

**Target State:**
- Full test coverage for research configuration
- Updated user documentation with domain examples
- Step-by-step migration guide
- Example domains for different research areas
- CI/CD integration for multi-domain testing

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Integration tests for research config loading in all modules
- [ ] End-to-end test: create domain → run pipeline → verify outputs
- [ ] Migration guide: "Converting Existing Setup to Domain Structure"
- [ ] Updated USER_MANUAL.md with `--research-config` examples
- [ ] At least 2 example domains (neuromorphic + one other)

### Should Have
- [ ] DASHBOARD_GUIDE.md updated for domain selection
- [ ] API_DOCUMENTATION.md updated with config endpoints
- [ ] Troubleshooting section for common migration issues
- [ ] Domain validation command: `python -m literature_review.config validate`

### Nice to Have
- [ ] Interactive domain creation wizard
- [ ] Domain template generator script
- [ ] Video/GIF walkthrough of domain setup
- [ ] Benchmark comparison across domains

---

## 🛠️ Technical Implementation

### 1. Integration Test Suite

**Create `tests/integration/test_research_agnostic.py`**:

```python
"""Integration tests for research-agnostic architecture."""
import pytest
import tempfile
import json
from pathlib import Path

from literature_review.config import load_config, reset_config, get_config


class TestResearchAgnosticIntegration:
    """Integration tests for multi-domain support."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset config before each test."""
        reset_config()
        yield
        reset_config()
    
    def test_pipeline_with_custom_domain(self, tmp_path):
        """Test pipeline runs with a custom research domain."""
        # Create minimal domain config
        domain_config = {
            "domain_id": "test-domain",
            "domain_name": "Test Research Domain",
            "research_topic": "test topic analysis",
            "short_description": "testing multi-domain support",
            "researcher_role": "Test Researcher",
            "pillar_definitions": [
                {"name": "Test Pillar", "focus_area": "Testing"}
            ]
        }
        
        config_path = tmp_path / "research_config.json"
        config_path.write_text(json.dumps(domain_config))
        
        # Load config
        cfg = load_config(str(config_path))
        
        assert cfg.domain_id == "test-domain"
        assert cfg.research_topic == "test topic analysis"
    
    def test_module_uses_loaded_config(self, tmp_path):
        """Test that refactored modules use the loaded config."""
        domain_config = {
            "domain_id": "custom-domain",
            "domain_name": "Custom Domain",
            "research_topic": "custom research area",
            "short_description": "custom domain test",
            "researcher_role": "Custom Researcher",
            "pillar_definitions": []
        }
        
        config_path = tmp_path / "research_config.json"
        config_path.write_text(json.dumps(domain_config))
        
        load_config(str(config_path))
        
        # Import after config is loaded
        from literature_review.config import get_research_topic_safe
        
        topic = get_research_topic_safe()
        assert topic == "custom research area"
    
    def test_fallback_when_no_config(self):
        """Test graceful fallback when no config is loaded."""
        from literature_review.config import get_research_topic_safe
        
        # Should return legacy fallback without error
        topic = get_research_topic_safe()
        assert "neuromorphic" in topic.lower()  # Legacy default
    
    def test_domain_switching(self, tmp_path):
        """Test switching between domains."""
        # Domain A
        domain_a = tmp_path / "domain_a.json"
        domain_a.write_text(json.dumps({
            "domain_id": "domain-a",
            "domain_name": "Domain A",
            "research_topic": "topic A",
            "short_description": "first domain",
            "pillar_definitions": []
        }))
        
        # Domain B
        domain_b = tmp_path / "domain_b.json"
        domain_b.write_text(json.dumps({
            "domain_id": "domain-b",
            "domain_name": "Domain B",
            "research_topic": "topic B",
            "short_description": "second domain",
            "pillar_definitions": []
        }))
        
        # Load A
        load_config(str(domain_a))
        assert get_config().domain_id == "domain-a"
        
        # Switch to B (requires reset first)
        reset_config()
        load_config(str(domain_b))
        assert get_config().domain_id == "domain-b"
```

### 2. Migration Guide

**Create `docs/RESEARCH_AGNOSTIC_MIGRATION_GUIDE.md`**:

```markdown
# Migration Guide: Research-Agnostic Architecture

## Overview

This guide helps you transition from the legacy hardcoded neuromorphic 
computing focus to the new research-agnostic architecture.

## Quick Start (5 minutes)

1. **Create your research_config.json**:
   ```bash
   cp domains/example-domain/research_config.json research_config.json
   ```

2. **Edit the configuration** for your research area:
   ```json
   {
     "domain_id": "your-domain-id",
     "domain_name": "Your Research Domain",
     "research_topic": "your research topic and focus",
     ...
   }
   ```

3. **Run the pipeline**:
   ```bash
   python pipeline_orchestrator.py --research-config research_config.json
   ```

## Migration from Legacy Setup

If you have existing reviews and analysis results...
[detailed migration steps]

## Creating New Domains

To analyze a completely different research area...
[domain creation steps]

## Troubleshooting

### "Research config not found" warning
[solution]

### Pillar definitions not loading
[solution]
```

### 3. Example Domain: Climate Science

**Create `domains/climate-science/research_config.json`**:

```json
{
  "domain_id": "climate-science",
  "domain_name": "Climate Science & Environmental Research",
  "research_topic": "climate change mitigation and environmental sustainability",
  "short_description": "climate science, carbon sequestration, and renewable energy",
  "researcher_role": "Climate Research Scientist",
  "keywords": [
    "climate change", "carbon sequestration", "renewable energy",
    "greenhouse gases", "sustainability", "environmental policy"
  ],
  "example_domains": [
    "atmospheric science", "oceanography", "ecology", "energy systems"
  ],
  "pillar_definitions": [
    {
      "name": "Emission Reduction Technologies",
      "focus_area": "Technologies and methods for reducing greenhouse gas emissions"
    },
    {
      "name": "Carbon Capture & Storage",
      "focus_area": "Methods for capturing and storing atmospheric carbon"
    },
    {
      "name": "Renewable Energy Systems",
      "focus_area": "Solar, wind, hydro, and other renewable energy technologies"
    },
    {
      "name": "Climate Modeling & Prediction",
      "focus_area": "Models and methods for predicting climate patterns"
    },
    {
      "name": "Policy & Economics",
      "focus_area": "Economic and policy frameworks for climate action"
    }
  ],
  "database_filename": "climate_science_database.json"
}
```

### 4. Documentation Updates Checklist

| Document | Section to Update | Changes Needed |
|----------|-------------------|----------------|
| `USER_MANUAL.md` | CLI Reference | Add `--research-config` flag |
| `USER_MANUAL.md` | Quick Start | Add domain setup step |
| `DASHBOARD_GUIDE.md` | Configuration | Add domain selection |
| `API_REFERENCE.md` | Endpoints | Add `/config` endpoints |
| `DEPLOYMENT_GUIDE.md` | Setup | Add domain configuration |
| `README.md` | Quick Start | Mention research config |

### 5. Validation Command

**Add to `literature_review/config/research_config.py`**:

```python
def validate_config(config_path: str) -> tuple[bool, list[str]]:
    """Validate a research configuration file.
    
    Returns:
        (is_valid, list of error messages)
    """
    errors = []
    
    try:
        cfg = ResearchConfig.load(config_path)
    except FileNotFoundError:
        return False, [f"Config file not found: {config_path}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except ValueError as e:
        return False, [f"Invalid config: {e}"]
    
    # Additional validation
    if not cfg.domain_id:
        errors.append("domain_id is required")
    if not cfg.pillar_definitions:
        errors.append("At least one pillar_definition is recommended")
    if len(cfg.domain_id) > 50:
        errors.append("domain_id should be <= 50 characters")
    
    # Check pillar definitions
    for i, pillar in enumerate(cfg.pillar_definitions):
        if not pillar.get("name"):
            errors.append(f"Pillar {i+1} missing 'name'")
        if not pillar.get("focus_area"):
            errors.append(f"Pillar {i+1} missing 'focus_area'")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m literature_review.config.research_config <config_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    is_valid, errors = validate_config(config_path)
    
    if is_valid:
        print(f"✅ {config_path} is valid")
        cfg = ResearchConfig.load(config_path)
        print(f"   Domain: {cfg.domain_name}")
        print(f"   Pillars: {len(cfg.pillar_definitions)}")
    else:
        print(f"❌ {config_path} has errors:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
```

---

## 🧪 Testing Requirements

### Unit Tests (Already Complete)
- [x] `tests/test_research_config.py` - 15 tests passing

### Integration Tests (New)
- [ ] `tests/integration/test_research_agnostic.py`
- [ ] `tests/integration/test_domain_switching.py`
- [ ] `tests/integration/test_migration.py`

### End-to-End Tests
- [ ] Full pipeline with neuromorphic domain
- [ ] Full pipeline with climate-science domain
- [ ] Domain migration from flat structure

### Manual Verification
- [ ] Fresh clone → domain setup → pipeline run
- [ ] Existing user migration path
- [ ] Dashboard domain selection (if applicable)

---

## 📁 Deliverables

1. **Test Files:**
   - `tests/integration/test_research_agnostic.py`
   - `tests/integration/test_domain_switching.py`

2. **Documentation:**
   - `docs/RESEARCH_AGNOSTIC_MIGRATION_GUIDE.md`
   - Updates to USER_MANUAL.md, README.md, etc.

3. **Example Domains:**
   - `domains/climate-science/`
   - `domains/biomedical-research/` (optional)

4. **Scripts:**
   - `scripts/validate_domain.py`
   - `scripts/create_domain.py` (optional wizard)

---

## 🔗 Dependencies

- **Depends On:** 
  - Phases 1-3 ✅ COMPLETE
  - Phase 4 (output isolation) - should be complete first
  
- **Blocks:** None (this is the final phase)

---

## 📝 Implementation Notes

1. **Testing Priority:** Integration tests before documentation
2. **Example Domain:** Climate science chosen for broad applicability
3. **Validation:** Focus on catching common mistakes early
4. **Migration:** Prioritize non-destructive operations

---

## 🚀 Rollout Plan

1. Write integration tests for existing Phase 1-3 functionality
2. Create climate-science example domain
3. Write migration guide (draft)
4. Update USER_MANUAL.md with examples
5. Add validation command to research_config.py
6. Test validation with various configs
7. Update README.md quick start
8. Final documentation review

---

## 📊 Success Metrics

- 100% of integration tests pass
- Migration guide tested by fresh user
- Zero hardcoded neuromorphic strings in prompts (verified by grep)
- At least 2 complete example domains
- User can set up new domain in < 10 minutes
