# Research Domains

This directory contains research domain configurations for the Literature Review pipeline.

## What is a Research Domain?

A research domain defines the **subject matter** that the pipeline analyzes. Each domain includes:

- **Research Topic**: The primary research question being investigated
- **Pillar Definitions**: A framework of requirements to evaluate against
- **Vocabulary**: Keywords relevant to the domain
- **Scoring Criteria**: How to prioritize and score relevance

## Directory Structure

```
domains/
├── neuromorphic-computing/     # Active neuromorphic computing domain
│   ├── research_config.json    # Domain configuration
│   └── pillar_definitions.json # Requirements framework
├── example-domain/             # Template for new domains
│   ├── research_config.json
│   └── pillar_definitions.json
└── README.md                   # This file
```

## Using a Domain

### Default Domain

By default, the pipeline uses `research_config.json` and `pillar_definitions.json` from the repository root.

### Switching Domains

To use a different domain, specify the config path:

```bash
# Use a specific domain configuration
python pipeline_orchestrator.py --config domains/neuromorphic-computing/research_config.json
```

Or copy the domain files to the root:

```bash
cp domains/quantum-computing/research_config.json ./
cp domains/quantum-computing/pillar_definitions.json ./
```

## Creating a New Domain

### Step 1: Create Domain Directory

```bash
mkdir domains/my-new-domain
```

### Step 2: Create research_config.json

Copy the template and customize:

```bash
cp domains/example-domain/research_config.json domains/my-new-domain/
```

Edit the following fields:

```json
{
  "domain": {
    "id": "my-new-domain",
    "name": "My New Research Domain",
    ...
  },
  "research_topic": {
    "primary": "Your primary research question here...",
    "short_description": "brief domain focus",
    ...
  },
  ...
}
```

### Step 3: Create pillar_definitions.json

Define your requirements framework:

```json
{
  "Framework_Overview": {
    "vision": "Your research vision",
    "core_principles": ["Principle 1", "Principle 2"]
  },
  "Pillar 1: Your First Pillar": {
    "description": "What this pillar covers",
    "keywords": ["keyword1", "keyword2"],
    "requirements": {
      "REQ-1.1: First Requirement": [
        "Sub-1.1.1: First sub-requirement",
        "Sub-1.1.2: Second sub-requirement"
      ]
    }
  }
}
```

### Step 4: Test Your Domain

```bash
# Validate config loads correctly
python -c "from literature_review.config import load_config; c = load_config('domains/my-new-domain/research_config.json'); print(f'Loaded: {c.domain_name}')"
```

## Configuration Reference

### research_config.json Schema

| Field | Type | Description |
|-------|------|-------------|
| `domain.id` | string | Unique identifier (used in filenames) |
| `domain.name` | string | Human-readable name |
| `research_topic.primary` | string | Full research question |
| `research_topic.short_description` | string | Brief description for prompts |
| `prompt_context.researcher_role` | string | AI persona for prompts |
| `vocabulary.primary_keywords` | array | Main domain keywords |
| `vocabulary.secondary_keywords` | array | Technical/specific keywords |
| `file_naming.database` | string | Template for database filename |
| `pillar_definitions_file` | string | Path to pillar definitions |

### pillar_definitions.json Structure

```json
{
  "Framework_Overview": {
    "vision": "...",
    "core_principles": [...],
    "developmental_sequence": [...]
  },
  "Pillar N: Name": {
    "description": "...",
    "keywords": [...],
    "requirements": {
      "REQ-X.Y: Name": [
        "Sub-X.Y.Z: Description"
      ]
    },
    "quantitative_metrics": {...},
    "validation_criteria": {...}
  }
}
```

## Available Domains

| Domain ID | Name | Status |
|-----------|------|--------|
| `neuromorphic-computing` | Neuromorphic Computing & Brain-Inspired AI | Active |

## Best Practices

1. **Use descriptive IDs**: Domain IDs become part of filenames
2. **Keep prompts focused**: Short descriptions should be 5-10 words
3. **Define clear requirements**: Each sub-requirement should be testable
4. **Include diverse keywords**: Both technical and conceptual terms
5. **Version your domains**: Use `domain.version` for tracking changes

## Troubleshooting

### Config Not Loading

```python
# Check if file exists and is valid JSON
import json
with open('domains/my-domain/research_config.json') as f:
    json.load(f)  # Will raise if invalid
```

### Pillar Definitions Not Found

Ensure `pillar_definitions_file` path is correct:
- Relative to the research_config.json location, OR
- Absolute path, OR  
- In the current working directory
