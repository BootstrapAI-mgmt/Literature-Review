# RESEARCH_AGNOSTIC_PHASE_4: Multi-Domain Output Isolation

**Status:** NOT STARTED  
**Priority:** 🟡 Medium  
**Effort Estimate:** 4-6 hours  
**Category:** Research-Agnostic Architecture  
**Created:** December 10, 2025  
**Related:** RESEARCH_AGNOSTIC_ARCHITECTURE.md v2.0

---

## 📋 Overview

Refactor output paths to use domain-specific subdirectories, enabling concurrent work across multiple research domains without file conflicts.

**Current State:**
- All outputs go to flat directories: `reviews/`, `gap_analysis_output/`, `data/`
- Running analysis for different domains overwrites previous results
- No way to maintain multiple domain analyses simultaneously
- Database files hardcoded in root directory

**Target State:**
- Domain-isolated outputs: `reviews/{domain_id}/`, `gap_analysis_output/{domain_id}/`
- Each domain maintains independent state and history
- Easy comparison across domains
- Clean separation of concerns

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Output directories include domain_id as subdirectory
- [ ] `reviews/{domain_id}/` for review JSON files
- [ ] `gap_analysis_output/{domain_id}/` for gap analysis reports
- [ ] Checkpoint files include domain context: `pipeline_checkpoint_{domain_id}.json`
- [ ] State manager uses domain-specific paths
- [ ] Backward compatibility: detect and migrate existing flat structure

### Should Have
- [ ] `data/{domain_id}/` for domain-specific raw data (PDFs, CSVs)
- [ ] Automatic domain directory creation on first run
- [ ] Cross-domain summary report capability
- [ ] Clean separation of `pillar_definitions_{domain_id}.json` per domain

### Nice to Have
- [ ] Domain archival/cleanup commands
- [ ] Storage usage reporting by domain
- [ ] Domain cloning for comparative studies
- [ ] Symlink support for shared resources across domains

---

## 🛠️ Technical Implementation

### 1. Output Path Configuration

**Update ResearchConfig** (`literature_review/config/research_config.py`):

```python
@dataclass
class ResearchConfig:
    # ... existing fields ...
    
    def get_output_dir(self, base_dir: str = "gap_analysis_output") -> Path:
        """Get domain-isolated output directory."""
        return Path(base_dir) / self.domain_id
    
    def get_reviews_dir(self, base_dir: str = "reviews") -> Path:
        """Get domain-isolated reviews directory."""
        return Path(base_dir) / self.domain_id
    
    def get_checkpoint_path(self, base_name: str = "pipeline_checkpoint.json") -> Path:
        """Get domain-specific checkpoint file path."""
        stem = Path(base_name).stem
        suffix = Path(base_name).suffix
        return Path(f"{stem}_{self.domain_id}{suffix}")
```

### 2. Pipeline Orchestrator Updates

**Update `pipeline_orchestrator.py`**:

```python
# After loading research config
if is_config_loaded():
    cfg = get_config()
    # Use domain-isolated output directory
    if args.output_dir == "gap_analysis_output":  # default
        args.output_dir = str(cfg.get_output_dir())
    
    # Create domain directory if needed
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
```

### 3. State Manager Integration

**Update `literature_review/state_manager.py`**:

```python
def get_default_paths(self) -> dict:
    """Get domain-aware default paths."""
    if is_config_loaded():
        cfg = get_config()
        return {
            "reviews_dir": cfg.get_reviews_dir(),
            "output_dir": cfg.get_output_dir(),
            "checkpoint": cfg.get_checkpoint_path(),
        }
    # Legacy fallback
    return {
        "reviews_dir": Path("reviews"),
        "output_dir": Path("gap_analysis_output"),
        "checkpoint": Path("pipeline_checkpoint.json"),
    }
```

### 4. Migration Helper

**Create `scripts/migrate_to_domain_structure.py`**:

```python
#!/usr/bin/env python3
"""Migrate flat file structure to domain-isolated structure."""

import shutil
from pathlib import Path
from literature_review.config import load_config, get_config

def migrate_outputs(domain_id: str, dry_run: bool = True):
    """Move existing outputs to domain subdirectory."""
    migrations = [
        ("reviews", f"reviews/{domain_id}"),
        ("gap_analysis_output", f"gap_analysis_output/{domain_id}"),
    ]
    
    for src, dst in migrations:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if src_path.exists() and not dst_path.exists():
            print(f"{'[DRY-RUN] ' if dry_run else ''}Move {src} -> {dst}")
            if not dry_run:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_path), str(dst_path))
```

---

## 📁 Directory Structure (After Implementation)

```
Literature-Review/
├── research_config.json              # Points to active domain
├── domains/
│   ├── neuromorphic-computing/
│   │   ├── research_config.json
│   │   └── pillar_definitions.json
│   └── climate-science/
│       ├── research_config.json
│       └── pillar_definitions.json
├── reviews/
│   ├── neuromorphic-computing/       # Domain-isolated
│   │   ├── paper_001_review.json
│   │   └── paper_002_review.json
│   └── climate-science/
│       └── paper_001_review.json
├── gap_analysis_output/
│   ├── neuromorphic-computing/       # Domain-isolated
│   │   ├── gap_analysis_report.json
│   │   └── recommendations.json
│   └── climate-science/
│       └── gap_analysis_report.json
├── data/
│   ├── neuromorphic-computing/       # Domain-specific data
│   │   └── papers.csv
│   └── climate-science/
│       └── papers.csv
└── pipeline_checkpoint_neuromorphic-computing.json
```

---

## 🧪 Testing Requirements

### Unit Tests
- [ ] `test_research_config_paths.py` - Test path generation methods
- [ ] `test_domain_isolation.py` - Verify no cross-domain leakage

### Integration Tests
- [ ] Run pipeline for domain A, then domain B, verify isolation
- [ ] Migrate existing flat structure, verify data integrity
- [ ] Resume checkpoint across domain switch (should fail gracefully)

### Manual Verification
- [ ] Run `--dry-run` for two different domains consecutively
- [ ] Verify output directories are correctly isolated
- [ ] Check logs show correct domain paths

---

## 🔗 Dependencies

- **Depends On:** Phases 1-3 (config module, module refactoring, CLI flag) ✅ COMPLETE
- **Blocks:** Phase 5 (comprehensive testing requires stable output structure)

---

## 📝 Implementation Notes

1. **Backward Compatibility:** Detect existing flat structure and offer migration
2. **Environment Variable:** Support `LITERATURE_REVIEW_DOMAIN` for CI/CD
3. **Error Handling:** Clear error if switching domains mid-checkpoint
4. **Documentation:** Update USER_MANUAL.md with multi-domain examples

---

## 🚀 Rollout Plan

1. Implement path methods in ResearchConfig (low risk)
2. Add migration script with `--dry-run` mode
3. Update pipeline orchestrator to use domain paths
4. Update state manager for domain-aware persistence
5. Test with existing neuromorphic domain
6. Document migration process
7. Create example second domain for testing

---

## 📊 Success Metrics

- Zero file overwrites when running multiple domains
- < 5 files need modification for full implementation
- Migration script handles 100% of existing files
- No breaking changes to existing single-domain usage
