# INCR-W4-1: ML-Based Gap Prioritization

**Wave:** 4 (Advanced Features - Optional)  
**Priority:** 🟢 Low (Optional)  
**Effort:** 6-8 hours  
**Status:** 🟡 Blocked (requires Waves 1-3 validated)  
**Assignable:** ML Engineer

---

## Overview

Train a machine learning model to rank gaps by closure difficulty, helping users prioritize which gaps to address first. Uses features like gap completeness, keyword density, topic similarity, and historical closure rates.

---

## Dependencies

**Prerequisites:**
- ✅ Waves 1-3 complete and validated in production
- ✅ INCR-W2-1 (CLI Incremental Mode - for gap extraction)

---

## Scope

### Included
- [x] Feature extraction from gaps
- [x] Gap difficulty ranking algorithm
- [x] Model training pipeline
- [x] API endpoint for prioritization
- [x] UI integration (sorted gap list)
- [x] Model evaluation metrics

### Excluded
- ❌ Deep learning models (use traditional ML)
- ❌ Continuous retraining (manual retraining only)
- ❌ Multi-objective optimization

---

## Technical Approach

### Features for Gap Ranking

```python
"""Gap prioritization feature extraction."""

from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class GapFeatures:
    """Features for predicting gap closure difficulty."""
    
    # Basic metrics
    current_coverage: float  # 0.0-1.0
    target_coverage: float   # 0.0-1.0
    gap_size: float          # target - current
    
    # Keyword analysis
    keyword_count: int
    keyword_specificity: float  # Avg IDF of keywords
    keyword_overlap_with_papers: float  # How many papers mention keywords
    
    # Topic analysis
    topic_entropy: float  # Higher = broader topic
    semantic_coherence: float  # How related keywords are
    
    # Historical data
    similar_gaps_closure_rate: float  # % of similar gaps closed
    avg_papers_needed: float  # Avg papers needed to close similar gaps
    
    # Pillar context
    pillar_completion: float  # Overall pillar coverage
    requirement_priority: int  # 1-5 (manual priority)

def extract_features(gap: Dict) -> GapFeatures:
    """Extract features from a gap for ranking."""
    
    # Basic metrics
    current = gap['current_coverage']
    target = gap['target_coverage']
    gap_size = target - current
    
    # Keyword analysis
    keywords = gap['keywords']
    keyword_count = len(keywords)
    
    # Calculate keyword specificity (IDF-like)
    # Higher IDF = more specific keywords
    keyword_specificity = calculate_keyword_idf(keywords)
    
    # Topic analysis
    topic_entropy = calculate_topic_entropy(keywords)
    semantic_coherence = calculate_semantic_coherence(keywords)
    
    # Historical data (from previous reviews)
    similar_gaps_closure_rate = get_historical_closure_rate(gap)
    avg_papers_needed = get_avg_papers_needed(gap)
    
    # Pillar context
    pillar_completion = gap.get('pillar_coverage', 0.5)
    requirement_priority = gap.get('priority', 3)
    
    return GapFeatures(
        current_coverage=current,
        target_coverage=target,
        gap_size=gap_size,
        keyword_count=keyword_count,
        keyword_specificity=keyword_specificity,
        keyword_overlap_with_papers=0.0,  # TODO: Implement
        topic_entropy=topic_entropy,
        semantic_coherence=semantic_coherence,
        similar_gaps_closure_rate=similar_gaps_closure_rate,
        avg_papers_needed=avg_papers_needed,
        pillar_completion=pillar_completion,
        requirement_priority=requirement_priority
    )
```

### Ranking Algorithm

```python
"""Gap difficulty ranking using Random Forest."""

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

class GapPrioritizer:
    """ML-based gap prioritization."""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
    
    def train(self, training_data: List[Tuple[GapFeatures, float]]):
        """
        Train gap difficulty model.
        
        Args:
            training_data: List of (features, difficulty_score) tuples
                          difficulty_score = 1-10 (10 = hardest to close)
        """
        X = []
        y = []
        
        for features, score in training_data:
            feature_vector = [
                features.current_coverage,
                features.gap_size,
                features.keyword_count,
                features.keyword_specificity,
                features.topic_entropy,
                features.semantic_coherence,
                features.similar_gaps_closure_rate,
                features.avg_papers_needed,
                features.pillar_completion,
                features.requirement_priority
            ]
            X.append(feature_vector)
            y.append(score)
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Random Forest
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.model.fit(X_scaled, y)
        
        print(f"Model trained on {len(X)} samples")
        print(f"Feature importances: {self.model.feature_importances_}")
    
    def rank_gaps(self, gaps: List[Dict]) -> List[Tuple[Dict, float]]:
        """
        Rank gaps by closure difficulty.
        
        Returns:
            List of (gap, difficulty_score) sorted by difficulty (easiest first)
        """
        if self.model is None:
            raise ValueError("Model not trained")
        
        gap_scores = []
        
        for gap in gaps:
            features = extract_features(gap)
            feature_vector = [[
                features.current_coverage,
                features.gap_size,
                features.keyword_count,
                features.keyword_specificity,
                features.topic_entropy,
                features.semantic_coherence,
                features.similar_gaps_closure_rate,
                features.avg_papers_needed,
                features.pillar_completion,
                features.requirement_priority
            ]]
            
            feature_scaled = self.scaler.transform(feature_vector)
            difficulty = self.model.predict(feature_scaled)[0]
            
            gap_scores.append((gap, difficulty))
        
        # Sort by difficulty (ascending = easiest first)
        gap_scores.sort(key=lambda x: x[1])
        
        return gap_scores
    
    def save_model(self, path: str):
        """Save trained model to disk."""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler
        }, path)
    
    def load_model(self, path: str):
        """Load trained model from disk."""
        data = joblib.load(path)
        self.model = data['model']
        self.scaler = data['scaler']
```

### Training Data Collection

```python
"""Collect training data from historical reviews."""

def collect_training_data() -> List[Tuple[GapFeatures, float]]:
    """
    Collect training data from previous reviews.
    
    Difficulty scoring heuristic:
    - 1-3: Easy (closed in 1-2 papers)
    - 4-6: Medium (closed in 3-5 papers)
    - 7-9: Hard (closed in 6+ papers or never closed)
    - 10: Extremely hard (never closed after 10+ papers)
    """
    training_data = []
    
    # Load historical job lineages
    historical_jobs = load_all_job_lineages()
    
    for job_chain in historical_jobs:
        for i, job in enumerate(job_chain):
            gaps = extract_gaps_from_job(job)
            
            for gap in gaps:
                features = extract_features(gap)
                
                # Calculate difficulty based on closure outcome
                if i < len(job_chain) - 1:
                    # Gap exists in job i, check if closed in i+1
                    next_job = job_chain[i + 1]
                    next_gaps = extract_gaps_from_job(next_job)
                    
                    gap_closed = gap['sub_requirement_id'] not in [
                        g['sub_requirement_id'] for g in next_gaps
                    ]
                    
                    if gap_closed:
                        # Easy to close
                        difficulty = 1 + np.random.uniform(0, 2)
                    else:
                        # Check subsequent jobs
                        papers_needed = count_papers_until_closure(gap, job_chain[i:])
                        
                        if papers_needed <= 2:
                            difficulty = 2
                        elif papers_needed <= 5:
                            difficulty = 5
                        elif papers_needed <= 10:
                            difficulty = 8
                        else:
                            difficulty = 10
                else:
                    # Last job, gap still open
                    difficulty = 9
                
                training_data.append((features, difficulty))
    
    return training_data
```

---

## API Endpoint

```python
# webdashboard/api/gap_prioritization.py

from flask import Blueprint, request, jsonify
from literature_review.utils.gap_prioritizer import GapPrioritizer

prioritize_bp = Blueprint('prioritize', __name__, url_prefix='/api/gaps')

# Load pre-trained model
prioritizer = GapPrioritizer()
prioritizer.load_model('models/gap_prioritizer.pkl')

@prioritize_bp.route('/prioritize', methods=['POST'])
def prioritize_gaps():
    """
    Rank gaps by closure difficulty.
    
    POST /api/gaps/prioritize
    Body: {"gaps": [...]}
    """
    data = request.get_json()
    gaps = data.get('gaps', [])
    
    if not gaps:
        return jsonify({'error': 'No gaps provided'}), 400
    
    # Rank gaps
    ranked_gaps = prioritizer.rank_gaps(gaps)
    
    # Format response
    result = [
        {
            'gap': gap,
            'difficulty_score': float(score),
            'difficulty_label': get_difficulty_label(score),
            'recommended_priority': get_priority_recommendation(score)
        }
        for gap, score in ranked_gaps
    ]
    
    return jsonify({
        'ranked_gaps': result,
        'easiest_gap': result[0],
        'hardest_gap': result[-1]
    }), 200

def get_difficulty_label(score: float) -> str:
    """Convert difficulty score to label."""
    if score < 3:
        return 'Easy'
    elif score < 6:
        return 'Medium'
    elif score < 9:
        return 'Hard'
    else:
        return 'Very Hard'

def get_priority_recommendation(score: float) -> str:
    """Recommend priority based on difficulty."""
    if score < 4:
        return 'High (quick wins)'
    elif score < 7:
        return 'Medium'
    else:
        return 'Low (requires significant effort)'
```

---

## UI Integration

Add to gap summary page:

```html
<div class="gap-priority-panel">
    <h5>Recommended Priority Order</h5>
    <button id="sortByPriority">Sort by ML Recommendation</button>
    
    <ul id="prioritizedGaps">
        <!-- Populated via JS -->
    </ul>
</div>
```

```javascript
async function loadPrioritizedGaps(jobId) {
    // Get gaps
    const gapsResponse = await fetch(`/api/jobs/${jobId}/gaps`);
    const gapsData = await gapsResponse.json();
    
    // Prioritize
    const priorityResponse = await fetch('/api/gaps/prioritize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gaps: gapsData.gaps })
    });
    
    const prioritized = await priorityResponse.json();
    
    // Display
    const list = document.getElementById('prioritizedGaps');
    list.innerHTML = prioritized.ranked_gaps.map((item, index) => `
        <li class="gap-item difficulty-${item.difficulty_label.toLowerCase()}">
            <span class="rank">#${index + 1}</span>
            <span class="gap-name">${item.gap.sub_requirement_id}</span>
            <span class="difficulty">${item.difficulty_label}</span>
            <span class="priority">${item.recommended_priority}</span>
        </li>
    `).join('');
}
```

---

## Deliverables

- [ ] Feature extraction pipeline
- [ ] Gap prioritizer model (Random Forest)
- [ ] Training script (`scripts/train_gap_prioritizer.py`)
- [ ] API endpoint (`/api/gaps/prioritize`)
- [ ] UI integration (sorted gap list)
- [ ] Model evaluation report
- [ ] Unit tests

---

## Success Criteria

✅ **Model Performance:**
- 70%+ accuracy on test set
- Feature importance interpretable
- <5s ranking time for 50 gaps

✅ **Functional:**
- API endpoint works
- UI displays prioritized gaps
- Recommendations align with expert judgment

✅ **UX:**
- Clear difficulty labels (Easy/Medium/Hard)
- Helpful priority recommendations

---

**Status:** 🟡 Blocked (requires Waves 1-3 validated)  
**Assignee:** TBD  
**Estimated Start:** Week 4, Day 1 (if approved)  
**Estimated Completion:** Week 4, Day 3
