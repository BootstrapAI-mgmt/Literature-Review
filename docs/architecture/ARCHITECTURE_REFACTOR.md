# Architecture Refactor Plan

This document outlines the plan to refactor the `literature-review` repository into a more robust, scalable, and maintainable structure.

## 1. Proposed Enterprise-Grade Structure

The new structure organizes the project as a formal Python package, separating concerns and improving modularity.

```
literature-review/
├── .github/                    # GitHub Actions, issue templates, etc.
├── .vscode/                    # VS Code workspace settings
├── data/                       # All non-code assets and data
│   ├── processed/              # Output from the pipeline (e.g., reports)
│   ├── raw/                    # Input documents (e.g., Research-Papers/)
│   └── examples/               # Example data files for reference
├── docs/                       # Project documentation
├── literature_review/          # Main Python source code as an installable package
│   ├── __init__.py
│   ├── analysis/               # Modules for analysis and judgment
│   │   ├── __init__.py
│   │   ├── judge.py
│   │   ├── recommendation.py
│   │   └── requirements.py
│   ├── io/                     # Modules for data input/output
│   │   ├── __init__.py
│   │   └── data_manager.py
│   ├── reviewers/              # Core reviewer agent modules
│   │   ├── __init__.py
│   │   ├── deep_reviewer.py
│   │   └── journal_reviewer.py
│   ├── utils/                  # Shared utility functions
│   │   └── __init__.py
│   ├── config.py               # Handles loading configurations
│   └── orchestrator.py         # Main pipeline orchestrator
├── scripts/                    # Standalone helper and maintenance scripts
├── tests/                      # All tests (unit, integration, e2e)
│   ├── component/
│   ├── e2e/
│   ├── integration/
│   └── unit/
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── pipeline_config.json        # High-level pipeline configuration
└── pillar_definitions.json     # Core ground truth definitions
```

## 2. File Modifications and Migration Plan

To transition to this new structure without breaking functionality, the following steps will be taken.

### Step 1: Create New Directory Structure

Create the new directories that will house the refactored code and data.

- `literature_review/`
- `literature_review/analysis/`
- `literature_review/io/`
- `literature_review/reviewers/`
- `literature_review/utils/`
- `data/`
- `data/raw/`
- `data/processed/`
- `data/examples/`
- `scripts/`

### Step 2: Move Existing Files

Move the existing Python scripts and data files into their new locations.

| Current File Path                      | New File Path                                         |
| -------------------------------------- | ----------------------------------------------------- |
| `Orchestrator.py`                      | `literature_review/orchestrator.py`                   |
| `Deep-Reviewer.py`                     | `literature_review/reviewers/deep_reviewer.py`        |
| `Journal-Reviewer.py`                  | `literature_review/reviewers/journal_reviewer.py`     |
| `Judge.py`                             | `literature_review/analysis/judge.py`                 |
| `DeepRequirementsAnalyzer.py`          | `literature_review/analysis/requirements.py`          |
| `RecommendationEngine.py`              | `literature_review/analysis/recommendation.py`        |
| `diagnostics.py`                       | `scripts/diagnostics.py`                              |
| `generate_plots.py`                    | `scripts/generate_plots.py`                           |
| `migrate_deep_coverage.py`             | `scripts/migrate_deep_coverage.py`                    |
| `post_merge_validation.py`             | `scripts/post_merge_validation.py`                    |
| `sync_history_to_db.py`                | `scripts/sync_history_to_db.py`                       |
| `Research-Papers/`                     | `data/raw/Research-Papers/`                           |
| `review_version_history_EXAMPLE.json`  | `data/examples/review_version_history_EXAMPLE.json`   |
| `neuromorphic-research_database_EXAMPLE.csv` | `data/examples/neuromorphic-research_database_EXAMPLE.csv` |
| `non-journal_database_EXAMPLE.csv`     | `data/examples/non-journal_database_EXAMPLE.csv`      |
| `pillar_definitions_enhanced.json`     | `pillar_definitions.json`                             |
| `demos/`                               | `scripts/demos/`                                      |

### Step 3: Update Import Statements

The most critical part of the refactor is updating the Python import statements within the moved files. Since the core logic will now be part of the `literature_review` package, all cross-module imports must be updated.

**Example:**
In `literature_review/orchestrator.py`, an import that was previously a direct script execution via `subprocess` will need to be changed to a direct import.

- **Before:** `subprocess.run(["python", "Deep-Reviewer.py"])`
- **After:** `from .reviewers import deep_reviewer` and then calling a main function like `deep_reviewer.run()`.

This change will need to be applied to all modules that call each other.

### Step 4: Update Configuration and Path References

Files like `pipeline_config.json` and any scripts that reference file paths will need to be updated to point to the new locations (e.g., `data/raw/` instead of `Research-Papers/`).

- **`pipeline_config.json`**: Update paths for `review_version_history_file`, `pillar_definitions_file`, etc.
- **Test Files**: Update paths in all test files under `tests/` to correctly locate test data and modules.
- **Demo Scripts**: Update paths in `scripts/demos/` to reflect the new data and source code locations.

### Step 5: Create `__init__.py` Files

Create empty `__init__.py` files in all new subdirectories within `literature_review/` to ensure they are treated as Python packages.

- `literature_review/__init__.py`
- `literature_review/analysis/__init__.py`
- `literature_review/io/__init__.py`
- `literature_review/reviewers/__init__.py`
- `literature_review/utils/__init__.py`

### Step 6: Verify Functionality

After all files are moved and code is updated, run all tests and demo scripts to ensure that the refactoring was successful and that no functionality has been broken.

- Run `pytest` to execute the entire test suite.
- Manually run each script in the `scripts/demos/` directory.
