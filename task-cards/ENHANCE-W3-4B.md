# ENHANCE-W3-4B: Field-Specific Half-Life Presets

**Status:** MANUAL CONFIGURATION ONLY  
**Priority:** 🟢 Low  
**Effort Estimate:** 2 hours  
**Category:** Enhancement Wave 3 - Evidence Decay Tracker  
**Created:** November 17, 2025  
**Related PR:** #45 (Evidence Decay Tracker)

---

## 📋 Overview

Add pre-configured half-life presets for different research fields instead of requiring users to manually set half-life values.

**Current Limitation:**
- Users must manually configure `half_life_years` in config
- No guidance on appropriate values for different fields
- Trial and error to find good half-life

**Proposed Enhancement:**
- Dropdown in UI to select research field
- Auto-populate half-life based on field
- Option to override with custom value
- Presets based on research literature publication cycles

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Predefined half-life presets for 7+ research fields
- [ ] UI dropdown to select research field
- [ ] Auto-set half-life when field selected
- [ ] Option to use custom half-life value

### Should Have
- [ ] Tooltip explaining each preset
- [ ] "Recommended" badge on suggested presets
- [ ] Save selected field to job metadata
- [ ] Display field in results (e.g., "AI/ML field, 3-year half-life")

### Nice to Have
- [ ] Learn from user's papers (auto-detect field from titles/abstracts)
- [ ] Field-specific decay curves visualization
- [ ] Multiple half-lives per job (different pillars = different fields)

---

## 🛠️ Technical Implementation

### 1. Half-Life Presets

**New Module:** `literature_review/decay_presets.py`

```python
from typing import Dict

FIELD_PRESETS = {
    'ai_ml': {
        'name': 'AI & Machine Learning',
        'half_life_years': 3.0,
        'description': 'Rapidly evolving field. Papers older than 3 years may be outdated.',
        'examples': ['Deep Learning', 'NLP', 'Computer Vision', 'Reinforcement Learning'],
        'recommended_for': ['artificial intelligence', 'machine learning', 'neural networks']
    },
    'software_engineering': {
        'name': 'Software Engineering',
        'half_life_years': 5.0,
        'description': 'Moderate pace. Practices evolve but core principles remain valid.',
        'examples': ['Design Patterns', 'Testing', 'DevOps', 'Agile'],
        'recommended_for': ['software', 'programming', 'development']
    },
    'computer_science': {
        'name': 'Computer Science (General)',
        'half_life_years': 7.0,
        'description': 'Broad field with varied sub-areas. Moderate decay rate.',
        'examples': ['Algorithms', 'Data Structures', 'HCI', 'Databases'],
        'recommended_for': ['computer science', 'algorithms', 'data structures']
    },
    'mathematics': {
        'name': 'Mathematics',
        'half_life_years': 10.0,
        'description': 'Slow-changing field. Theorems and proofs remain valid indefinitely.',
        'examples': ['Number Theory', 'Algebra', 'Topology', 'Analysis'],
        'recommended_for': ['mathematics', 'theorem', 'proof']
    },
    'medicine': {
        'name': 'Medicine & Healthcare',
        'half_life_years': 5.0,
        'description': 'Clinical guidelines update regularly. Moderate decay.',
        'examples': ['Clinical Trials', 'Treatments', 'Diagnostics', 'Public Health'],
        'recommended_for': ['medicine', 'healthcare', 'clinical', 'treatment']
    },
    'biology': {
        'name': 'Biology & Life Sciences',
        'half_life_years': 6.0,
        'description': 'Research builds incrementally. Moderate-slow decay.',
        'examples': ['Genetics', 'Molecular Biology', 'Ecology', 'Neuroscience'],
        'recommended_for': ['biology', 'genetics', 'molecular', 'cell']
    },
    'physics': {
        'name': 'Physics',
        'half_life_years': 8.0,
        'description': 'Foundational science. Discoveries endure.',
        'examples': ['Particle Physics', 'Astrophysics', 'Quantum Mechanics'],
        'recommended_for': ['physics', 'quantum', 'particle', 'relativity']
    },
    'chemistry': {
        'name': 'Chemistry',
        'half_life_years': 7.0,
        'description': 'Established field with ongoing discoveries.',
        'examples': ['Organic Chemistry', 'Materials Science', 'Catalysis'],
        'recommended_for': ['chemistry', 'chemical', 'molecular']
    },
    'custom': {
        'name': 'Custom',
        'half_life_years': 5.0,
        'description': 'Set your own half-life value',
        'examples': [],
        'recommended_for': []
    }
}

def get_preset(field_key: str) -> Dict:
    """Get preset configuration for a field"""
    return FIELD_PRESETS.get(field_key, FIELD_PRESETS['custom'])

def suggest_field_from_papers(papers: list) -> str:
    """Auto-detect research field from paper titles/abstracts"""
    # Aggregate all text
    all_text = ' '.join([
        p.get('title', '') + ' ' + p.get('abstract', '') 
        for p in papers
    ]).lower()
    
    # Score each field based on keyword matches
    field_scores = {}
    for field_key, preset in FIELD_PRESETS.items():
        if field_key == 'custom':
            continue
        
        keywords = preset.get('recommended_for', [])
        score = sum([all_text.count(keyword) for keyword in keywords])
        field_scores[field_key] = score
    
    # Return field with highest score
    if not field_scores or max(field_scores.values()) == 0:
        return 'custom'
    
    return max(field_scores, key=field_scores.get)
```

### 2. Configuration Integration

**Enhanced:** `pipeline_config.json`

```json
{
  "evidence_decay": {
    "enabled": true,
    "research_field": "ai_ml",  // NEW: Field preset key
    "half_life_years": null,  // NEW: Null = use preset, number = custom override
    "weight_in_gap_analysis": false
  }
}
```

**Modified:** `literature_review/evidence_decay.py`

```python
from literature_review.decay_presets import get_preset, FIELD_PRESETS

class EvidenceDecayTracker:
    def __init__(self, config=None):
        self.config = config or load_config()
        
        # Load field preset or custom half-life
        field_key = self.config.get('evidence_decay', {}).get('research_field', 'custom')
        custom_half_life = self.config.get('evidence_decay', {}).get('half_life_years')
        
        if custom_half_life is not None:
            # User override
            self.half_life_years = custom_half_life
            self.field_name = 'Custom'
        else:
            # Use preset
            preset = get_preset(field_key)
            self.half_life_years = preset['half_life_years']
            self.field_name = preset['name']
        
        print(f"Evidence Decay: Using {self.field_name} preset (half-life: {self.half_life_years} years)")
```

### 3. Frontend UI

**New Component:** Field selector in job configuration

```html
<!-- Job Configuration Form -->
<div class="card">
    <div class="card-header">Evidence Decay Configuration</div>
    <div class="card-body">
        <div class="mb-3">
            <label for="research-field" class="form-label">Research Field</label>
            <select id="research-field" class="form-select" onchange="updateHalfLife()">
                <option value="">-- Select Field --</option>
                {% for key, preset in field_presets.items() %}
                <option value="{{ key }}" data-half-life="{{ preset.half_life_years }}">
                    {{ preset.name }} ({{ preset.half_life_years }} year half-life)
                </option>
                {% endfor %}
            </select>
            <small class="form-text text-muted" id="field-description"></small>
        </div>
        
        <div class="mb-3">
            <label for="half-life" class="form-label">
                Half-Life (years)
                <span class="badge bg-info" id="preset-badge" style="display:none;">From Preset</span>
            </label>
            <input type="number" id="half-life" class="form-control" 
                   step="0.5" min="1" max="20" value="5.0">
            <small class="form-text text-muted">
                Time for evidence weight to decay to 50%. Lower = faster decay.
            </small>
        </div>
        
        <div class="form-check">
            <input type="checkbox" id="use-preset" class="form-check-input" checked>
            <label for="use-preset" class="form-check-label">
                Use preset (uncheck for custom half-life)
            </label>
        </div>
    </div>
</div>
```

**JavaScript:**
```javascript
const FIELD_PRESETS = {{ field_presets|tojson }};

function updateHalfLife() {
    const fieldSelect = document.getElementById('research-field');
    const selectedField = fieldSelect.value;
    const usePreset = document.getElementById('use-preset').checked;
    
    if (selectedField && usePreset) {
        const preset = FIELD_PRESETS[selectedField];
        
        // Update half-life input
        document.getElementById('half-life').value = preset.half_life_years;
        document.getElementById('half-life').disabled = true;
        
        // Show description
        document.getElementById('field-description').innerHTML = `
            <strong>${preset.description}</strong><br>
            Examples: ${preset.examples.join(', ')}
        `;
        
        // Show preset badge
        document.getElementById('preset-badge').style.display = 'inline';
    } else {
        // Custom mode
        document.getElementById('half-life').disabled = false;
        document.getElementById('preset-badge').style.display = 'none';
        
        if (!selectedField) {
            document.getElementById('field-description').textContent = '';
        }
    }
}

// Auto-suggest field based on uploaded papers
async function autoSuggestField(papers) {
    const response = await fetch('/api/suggest-field', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({papers: papers})
    });
    
    const data = await response.json();
    
    if (data.suggested_field) {
        document.getElementById('research-field').value = data.suggested_field;
        updateHalfLife();
        
        // Show suggestion notification
        showNotification(`Detected research field: ${data.field_name}`, 'info');
    }
}

document.getElementById('use-preset').addEventListener('change', (e) => {
    if (e.target.checked) {
        updateHalfLife();
    } else {
        document.getElementById('half-life').disabled = false;
        document.getElementById('preset-badge').style.display = 'none';
    }
});
```

### 4. Backend API Endpoint

**New Route:** `POST /api/suggest-field`

```python
from literature_review.decay_presets import suggest_field_from_papers, get_preset

@app.route('/api/suggest-field', methods=['POST'])
def suggest_field():
    """Auto-suggest research field based on papers"""
    data = request.json
    papers = data.get('papers', [])
    
    if not papers:
        return jsonify({'error': 'No papers provided'}), 400
    
    # Analyze papers
    suggested_field_key = suggest_field_from_papers(papers)
    preset = get_preset(suggested_field_key)
    
    return jsonify({
        'suggested_field': suggested_field_key,
        'field_name': preset['name'],
        'half_life_years': preset['half_life_years'],
        'description': preset['description']
    })
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_decay_presets.py`

```python
def test_get_preset():
    """Test preset retrieval"""
    ai_preset = get_preset('ai_ml')
    
    assert ai_preset['name'] == 'AI & Machine Learning'
    assert ai_preset['half_life_years'] == 3.0

def test_custom_preset():
    """Test custom preset fallback"""
    custom_preset = get_preset('nonexistent_field')
    
    assert custom_preset['name'] == 'Custom'

def test_suggest_field_from_papers():
    """Test auto-detection of research field"""
    papers = [
        {'title': 'Deep Learning for Image Recognition', 'abstract': 'Neural networks...'},
        {'title': 'Attention Mechanisms in NLP', 'abstract': 'Machine learning...'},
        {'title': 'Reinforcement Learning Algorithms', 'abstract': 'AI agent...'}
    ]
    
    suggested = suggest_field_from_papers(papers)
    
    assert suggested == 'ai_ml'  # Should detect AI/ML field

def test_suggest_field_mathematics():
    """Test detection of mathematics field"""
    papers = [
        {'title': 'Proof of the Riemann Hypothesis', 'abstract': 'Theorem...'},
        {'title': 'Number Theory Applications', 'abstract': 'Mathematical...'}
    ]
    
    suggested = suggest_field_from_papers(papers)
    
    assert suggested == 'mathematics'

def test_config_with_preset():
    """Test configuration using preset"""
    config = {
        'evidence_decay': {
            'research_field': 'ai_ml',
            'half_life_years': None  # Use preset
        }
    }
    
    tracker = EvidenceDecayTracker(config=config)
    
    assert tracker.half_life_years == 3.0
    assert tracker.field_name == 'AI & Machine Learning'

def test_config_with_custom_override():
    """Test custom half-life override"""
    config = {
        'evidence_decay': {
            'research_field': 'ai_ml',
            'half_life_years': 7.5  # Custom override
        }
    }
    
    tracker = EvidenceDecayTracker(config=config)
    
    assert tracker.half_life_years == 7.5  # Uses custom value
    assert tracker.field_name == 'Custom'
```

---

## 📚 Documentation Updates

**File:** `docs/EVIDENCE_DECAY_README.md`

**New Section:**
```markdown
## Research Field Presets

### Choosing the Right Half-Life

Different research fields evolve at different rates:

| Field | Half-Life | Why? |
|-------|-----------|------|
| **AI & Machine Learning** | 3 years | Rapidly evolving. Models/techniques obsolete quickly. |
| **Software Engineering** | 5 years | Practices evolve but core principles endure. |
| **Computer Science** | 7 years | Broad field with varied sub-areas. |
| **Mathematics** | 10 years | Theorems and proofs timeless. |
| **Medicine** | 5 years | Clinical guidelines update regularly. |
| **Biology** | 6 years | Incremental research buildup. |
| **Physics** | 8 years | Foundational discoveries last. |
| **Chemistry** | 7 years | Established field with ongoing work. |

### Using Presets

**Dashboard:**
1. Select "Research Field" dropdown
2. Choose your field (e.g., "AI & Machine Learning")
3. Half-life auto-populates (e.g., 3 years)
4. Uncheck "Use preset" for custom value

**Terminal:**
```json
{
  "evidence_decay": {
    "research_field": "ai_ml",
    "half_life_years": null  // Use preset
  }
}
```

**Custom Override:**
```json
{
  "evidence_decay": {
    "research_field": "ai_ml",
    "half_life_years": 4.5  // Custom: 4.5 years
  }
}
```

### Auto-Detection

The system can auto-suggest a field based on your papers:

```python
from literature_review.decay_presets import suggest_field_from_papers

papers = load_papers()
suggested = suggest_field_from_papers(papers)
print(f"Suggested field: {suggested}")
```

**Example:**
```
Papers contain: "neural networks", "deep learning", "AI"
→ Suggested field: AI & Machine Learning (3-year half-life)
```
```

---

## 🚀 Deployment Notes

### No Breaking Changes

- Existing configs without `research_field` default to 'custom' preset
- `half_life_years` still works as before (takes precedence over preset)
- Backward compatible with PR #45

### Migration Path

**Old Config:**
```json
{"evidence_decay": {"half_life_years": 5.0}}
```

**New Config (equivalent):**
```json
{"evidence_decay": {"research_field": "software_engineering"}}
```

---

## 📈 Success Metrics

**User Impact:**
- 80% reduction in config errors (no more guessing half-life)
- Improved decay accuracy (field-appropriate values)
- Faster job setup (auto-suggestion)

**Technical Metrics:**
- Auto-detection accuracy: >70% for common fields
- Preset usage: >60% of jobs use presets vs custom

---

## ✅ Definition of Done

- [ ] `FIELD_PRESETS` dictionary with 8+ fields
- [ ] `suggest_field_from_papers()` function implemented
- [ ] Frontend field selector dropdown
- [ ] Auto-suggest API endpoint
- [ ] Config integration (preset vs custom logic)
- [ ] Unit tests (≥90% coverage)
- [ ] Documentation updated (EVIDENCE_DECAY_README.md)
- [ ] Manual testing with different fields
- [ ] Code review approved
- [ ] Merged to main branch
