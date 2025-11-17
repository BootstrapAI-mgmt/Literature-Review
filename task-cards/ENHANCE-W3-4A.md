# ENHANCE-W3-4A: Integrate Evidence Decay with Gap Analysis Scoring

**Status:** TRACKING ONLY, NOT INTEGRATED  
**Priority:** 🟡 Medium  
**Effort Estimate:** 4 hours  
**Category:** Enhancement Wave 3 - Evidence Decay Tracker  
**Created:** November 17, 2025  
**Related PR:** #45 (Evidence Decay Tracker)

---

## 📋 Overview

Integrate evidence decay weights into gap analysis completeness scoring to penalize requirements with stale evidence and boost requirements with recent evidence.

**Current Behavior:**
- Evidence decay tracker generates `evidence_decay.json` report
- Flags requirements with stale evidence (old publication dates)
- Does NOT affect gap analysis scores
- Completeness calculation ignores evidence age

**Proposed Change:**
- Use `freshness_score` (decay-weighted) instead of raw alignment score
- Requirements with old evidence get lower completeness scores
- Requirements with recent evidence get higher scores
- Configurable via `pipeline_config.json` (enable/disable)

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Gap analysis uses decay-weighted scores when enabled
- [ ] Config option `evidence_decay.weight_in_gap_analysis` (default: false)
- [ ] Preserve backward compatibility (disabled by default)
- [ ] Documentation explaining when to enable

### Should Have
- [ ] A/B comparison report showing impact (with vs without decay)
- [ ] Configurable decay weight (0.0-1.0, how much to trust decay)
- [ ] Pillar-specific decay configuration
- [ ] UI toggle to enable/disable decay weighting

### Nice to Have
- [ ] Visualize decay impact in gap analysis results
- [ ] "Freshness" column in gap coverage table
- [ ] Alert when critical gaps have stale evidence
- [ ] Automatic refresh recommendations ("Update evidence for requirement X")

---

## 🛠️ Technical Implementation

### 1. Configuration Schema

**Enhanced:** `pipeline_config.json`

```json
{
  "evidence_decay": {
    "enabled": true,
    "half_life_years": 5.0,
    "weight_in_gap_analysis": true,  // NEW: Enable integration
    "decay_weight": 0.7,  // NEW: How much to trust decay (0.0-1.0)
    "apply_to_pillars": ["all"],  // NEW: Or specific pillars
    "min_freshness_threshold": 0.3  // NEW: Flag if freshness < 0.3
  }
}
```

**Parameters:**
- `weight_in_gap_analysis`: Enable/disable integration
- `decay_weight`: Blend factor (0.0 = ignore decay, 1.0 = full decay weight)
- `apply_to_pillars`: Which pillars use decay weighting
- `min_freshness_threshold`: Alert if freshness drops below this

### 2. Modified Gap Analysis Scoring

**Current Code:** `literature_review/gap_analyzer.py`

```python
# BEFORE (without decay)
def calculate_completeness(requirement, papers):
    """Calculate requirement completeness from papers"""
    max_alignment = max([align_score(req, paper) for paper in papers])
    return max_alignment  # Raw alignment score (0.0-1.0)
```

**Enhanced Code (with decay):**

```python
from literature_review.evidence_decay import EvidenceDecayTracker

class GapAnalyzer:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.decay_enabled = self.config.get('evidence_decay', {}).get('weight_in_gap_analysis', False)
        self.decay_weight = self.config.get('evidence_decay', {}).get('decay_weight', 0.7)
        
        if self.decay_enabled:
            self.decay_tracker = EvidenceDecayTracker(config=self.config)
    
    def calculate_completeness(self, requirement, papers, pillar_name=None):
        """Calculate requirement completeness with optional decay weighting"""
        # Calculate raw alignment scores
        alignments = [(paper, align_score(requirement, paper)) for paper in papers]
        
        if not alignments:
            return 0.0
        
        # Find best-matching paper
        best_paper, best_score = max(alignments, key=lambda x: x[1])
        
        # Apply decay weighting if enabled
        if self.decay_enabled and self._should_apply_decay(pillar_name):
            freshness_score = self._calculate_freshness(best_paper)
            
            # Blended score: (1-weight)*raw + weight*decay_adjusted
            decay_adjusted_score = best_score * freshness_score
            final_score = (1 - self.decay_weight) * best_score + self.decay_weight * decay_adjusted_score
            
            # Store metadata for reporting
            requirement['evidence_metadata'] = {
                'raw_score': best_score,
                'freshness_score': freshness_score,
                'final_score': final_score,
                'best_paper': best_paper['title'],
                'best_paper_year': best_paper.get('year'),
                'decay_applied': True
            }
            
            return final_score
        else:
            # No decay weighting
            requirement['evidence_metadata'] = {
                'raw_score': best_score,
                'final_score': best_score,
                'decay_applied': False
            }
            return best_score
    
    def _should_apply_decay(self, pillar_name):
        """Check if decay should be applied to this pillar"""
        apply_to = self.config.get('evidence_decay', {}).get('apply_to_pillars', ['all'])
        
        if 'all' in apply_to:
            return True
        
        return pillar_name in apply_to if pillar_name else True
    
    def _calculate_freshness(self, paper):
        """Calculate freshness score for a paper"""
        year = paper.get('year')
        if not year:
            return 0.5  # Neutral freshness if year unknown
        
        # Use decay tracker's formula
        current_year = datetime.now().year
        age_years = current_year - year
        half_life = self.config.get('evidence_decay', {}).get('half_life_years', 5.0)
        
        freshness = 0.5 ** (age_years / half_life)
        return freshness
```

### 3. A/B Comparison Report

**New Function:** Generate side-by-side comparison

```python
def generate_decay_impact_report(pillar_name, requirements, papers):
    """Generate report showing decay impact on completeness scores"""
    analyzer_no_decay = GapAnalyzer(config={'evidence_decay': {'weight_in_gap_analysis': False}})
    analyzer_with_decay = GapAnalyzer(config={'evidence_decay': {'weight_in_gap_analysis': True}})
    
    report = []
    
    for req in requirements:
        score_no_decay = analyzer_no_decay.calculate_completeness(req, papers)
        score_with_decay = analyzer_with_decay.calculate_completeness(req, papers)
        
        delta = score_with_decay - score_no_decay
        delta_pct = (delta / score_no_decay * 100) if score_no_decay > 0 else 0
        
        report.append({
            'requirement': req['description'],
            'score_no_decay': round(score_no_decay, 3),
            'score_with_decay': round(score_with_decay, 3),
            'delta': round(delta, 3),
            'delta_pct': round(delta_pct, 1),
            'freshness': req.get('evidence_metadata', {}).get('freshness_score', 0),
            'impact': 'decreased' if delta < -0.05 else 'increased' if delta > 0.05 else 'minimal'
        })
    
    # Summary statistics
    avg_delta = sum([r['delta'] for r in report]) / len(report) if report else 0
    significant_changes = [r for r in report if abs(r['delta']) > 0.1]
    
    return {
        'pillar': pillar_name,
        'requirements': report,
        'summary': {
            'total_requirements': len(report),
            'avg_delta': round(avg_delta, 3),
            'significant_changes': len(significant_changes),
            'impact_breakdown': {
                'decreased': len([r for r in report if r['impact'] == 'decreased']),
                'increased': len([r for r in report if r['impact'] == 'increased']),
                'minimal': len([r for r in report if r['impact'] == 'minimal'])
            }
        }
    }
```

### 4. Frontend Visualization

**Enhanced:** `webdashboard/templates/index.html`

```html
<!-- Gap Analysis Results with Decay Info -->
<div class="gap-coverage-table">
    <table class="table">
        <thead>
            <tr>
                <th>Requirement</th>
                <th>Coverage</th>
                <th>Freshness</th>  <!-- NEW -->
                <th>Best Evidence</th>
            </tr>
        </thead>
        <tbody>
            {% for req in requirements %}
            <tr>
                <td>{{ req.description }}</td>
                <td>
                    <div class="progress">
                        <div class="progress-bar" style="width: {{ req.coverage * 100 }}%">
                            {{ (req.coverage * 100)|round(1) }}%
                        </div>
                    </div>
                    {% if req.evidence_metadata.decay_applied %}
                    <small class="text-muted">
                        (raw: {{ (req.evidence_metadata.raw_score * 100)|round(1) }}%)
                    </small>
                    {% endif %}
                </td>
                <td>
                    {% if req.evidence_metadata.decay_applied %}
                    <span class="badge bg-{{ freshness_badge_color(req.evidence_metadata.freshness_score) }}">
                        {{ (req.evidence_metadata.freshness_score * 100)|round(0) }}%
                    </span>
                    {% else %}
                    <span class="text-muted">N/A</span>
                    {% endif %}
                </td>
                <td>
                    {{ req.evidence_metadata.best_paper }}
                    <small>({{ req.evidence_metadata.best_paper_year }})</small>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- Decay Impact Toggle -->
<div class="card mt-3">
    <div class="card-header">
        <input type="checkbox" id="enable-decay" {% if decay_enabled %}checked{% endif %}>
        <label for="enable-decay">Apply Evidence Decay Weighting</label>
    </div>
    <div class="card-body">
        <p class="text-muted">
            When enabled, older evidence receives lower weight in completeness calculations.
            Recent papers (last {{ half_life }} years) are prioritized.
        </p>
        <button class="btn btn-sm btn-primary" onclick="rerunWithDecay()">
            Rerun Analysis with Decay
        </button>
    </div>
</div>
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_decay_integration.py`

```python
def test_completeness_with_decay_enabled():
    """Test decay weighting affects completeness scores"""
    config = {'evidence_decay': {'weight_in_gap_analysis': True, 'decay_weight': 1.0, 'half_life_years': 5.0}}
    analyzer = GapAnalyzer(config=config)
    
    requirement = {'description': 'Test requirement'}
    old_paper = {'title': 'Old Paper', 'year': 2015, 'content': 'relevant'}  # 10 years old
    new_paper = {'title': 'New Paper', 'year': 2024, 'content': 'relevant'}  # 1 year old
    
    # Old paper should get lower score due to decay
    score_old = analyzer.calculate_completeness(requirement, [old_paper])
    score_new = analyzer.calculate_completeness(requirement, [new_paper])
    
    assert score_new > score_old  # Newer paper scores higher

def test_completeness_without_decay():
    """Test no decay weighting when disabled"""
    config = {'evidence_decay': {'weight_in_gap_analysis': False}}
    analyzer = GapAnalyzer(config=config)
    
    requirement = {'description': 'Test requirement'}
    old_paper = {'title': 'Old Paper', 'year': 2015, 'content': 'relevant'}
    new_paper = {'title': 'New Paper', 'year': 2024, 'content': 'relevant'}
    
    score_old = analyzer.calculate_completeness(requirement, [old_paper])
    score_new = analyzer.calculate_completeness(requirement, [new_paper])
    
    # Scores should be identical (both highly relevant)
    assert abs(score_old - score_new) < 0.01

def test_decay_weight_blending():
    """Test decay weight parameter"""
    requirement = {'description': 'Test'}
    paper = {'title': 'Paper', 'year': 2020, 'content': 'relevant'}
    
    # No decay (weight=0)
    config_no_decay = {'evidence_decay': {'weight_in_gap_analysis': True, 'decay_weight': 0.0}}
    analyzer_no_decay = GapAnalyzer(config=config_no_decay)
    score_no_decay = analyzer_no_decay.calculate_completeness(requirement, [paper])
    
    # Full decay (weight=1)
    config_full_decay = {'evidence_decay': {'weight_in_gap_analysis': True, 'decay_weight': 1.0}}
    analyzer_full_decay = GapAnalyzer(config=config_full_decay)
    score_full_decay = analyzer_full_decay.calculate_completeness(requirement, [paper])
    
    # Partial decay (weight=0.5)
    config_partial = {'evidence_decay': {'weight_in_gap_analysis': True, 'decay_weight': 0.5}}
    analyzer_partial = GapAnalyzer(config=config_partial)
    score_partial = analyzer_partial.calculate_completeness(requirement, [paper])
    
    # Partial should be between no decay and full decay
    assert score_no_decay >= score_partial >= score_full_decay

def test_ab_comparison_report():
    """Test A/B comparison report generation"""
    requirements = [
        {'description': 'Req 1'},
        {'description': 'Req 2'}
    ]
    papers = [
        {'title': 'Old Paper', 'year': 2015, 'content': 'relevant'},
        {'title': 'New Paper', 'year': 2024, 'content': 'relevant'}
    ]
    
    report = generate_decay_impact_report('Test Pillar', requirements, papers)
    
    assert 'summary' in report
    assert 'requirements' in report
    assert report['summary']['total_requirements'] == 2
    assert 'avg_delta' in report['summary']
```

---

## 📚 Documentation Updates

**File:** `docs/EVIDENCE_DECAY_README.md`

**New Section:**
```markdown
## Integration with Gap Analysis

### When to Enable Decay Weighting

**Enable if:**
- Research field changes rapidly (AI/ML, medicine)
- Recent evidence is more trustworthy
- You want to prioritize fresh papers

**Disable if:**
- Research field changes slowly (mathematics, physics)
- Historical evidence is equally valid
- Paper age doesn't affect relevance

### How It Works

When enabled, completeness scores are adjusted based on evidence freshness:

**Example:**
```
Requirement: "System must support X"

Without Decay:
- Old Paper (2015): 90% alignment → 90% completeness
- New Paper (2024): 90% alignment → 90% completeness

With Decay (5-year half-life):
- Old Paper (2015): 90% alignment × 25% freshness → 22.5% completeness
- New Paper (2024): 90% alignment × 87% freshness → 78% completeness
```

### Configuration

```json
{
  "evidence_decay": {
    "weight_in_gap_analysis": true,
    "decay_weight": 0.7,  // 70% decay, 30% raw score
    "half_life_years": 5.0,
    "apply_to_pillars": ["all"]
  }
}
```

### Interpreting Results

**Freshness Score:**
- 🟢 >70%: Recent evidence (last 3 years)
- 🟡 40-70%: Moderate age (3-7 years)
- 🔴 <40%: Stale evidence (>7 years)

**Impact on Completeness:**
- Requirements with old evidence drop in score
- Requirements with recent evidence maintain score
- Overall completeness may decrease (be prepared!)

### A/B Comparison

Run `--generate-decay-report` to see impact:

```bash
python scripts/run_gap_analysis.py --generate-decay-report
```

**Sample Output:**
```
Decay Impact Report for Pillar: Security
=========================================
Total Requirements: 15
Average Delta: -8.5%
Significant Changes: 5

Requirements:
1. "Authentication required" 
   - Without Decay: 85%
   - With Decay: 45% (-40%)
   - Freshness: 30% (evidence from 2016)
   - Impact: DECREASED

2. "Encryption standard"
   - Without Decay: 92%
   - With Decay: 88% (-4%)
   - Freshness: 82% (evidence from 2023)
   - Impact: MINIMAL
```
```

---

## ✅ Definition of Done

- [ ] Gap analysis scoring modified to use decay weights
- [ ] Configuration options added to `pipeline_config.json`
- [ ] Backward compatibility preserved (disabled by default)
- [ ] A/B comparison report generator implemented
- [ ] Frontend shows freshness scores in gap coverage table
- [ ] Unit tests (≥90% coverage)
- [ ] Integration tests (with/without decay)
- [ ] Documentation updated (EVIDENCE_DECAY_README.md)
- [ ] User guide with when to enable/disable
- [ ] Code review approved
- [ ] Merged to main branch
