# ENHANCE-W3-2B: Cost-Aware Search Ordering for ROI Optimizer

**Status:** NO COST CONSIDERATION  
**Priority:** 🟢 Low  
**Effort Estimate:** 2 hours  
**Category:** Enhancement Wave 3 - ROI Search Optimizer  
**Created:** November 17, 2025  
**Related PR:** #43 (ROI-based Search Optimization)

---

## 📋 Overview

Enhance ROI calculation to consider API costs, prioritizing high-ROI, low-cost searches first for budget-constrained research.

**Current Limitation:**
- ROI = (gap_severity × expected_papers) / search_cost
- `search_cost` is placeholder (always 1.0)
- Doesn't account for actual API costs
- No budget planning or cost estimates

**Proposed Enhancement:**
- Calculate real API costs (calls × rate per call)
- Factor cost into ROI prioritization
- Show cost estimates before starting job
- Budget-constrained search planning

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Calculate API cost per search (based on API pricing)
- [ ] Factor cost into ROI formula (cost-adjusted ROI)
- [ ] Show total estimated cost before job starts
- [ ] Sort searches by cost-efficiency (value per dollar)

### Should Have
- [ ] Budget limit configuration (e.g., "max $50")
- [ ] Auto-skip searches that exceed budget
- [ ] Cost breakdown by search (in results)
- [ ] Compare estimated vs actual cost

### Nice to Have
- [ ] Multi-tier pricing support (different APIs have different rates)
- [ ] Cost optimization mode ("minimize cost" vs "maximize coverage")
- [ ] Real-time cost tracking during job
- [ ] Alert when approaching budget limit

---

## 🛠️ Technical Implementation

### 1. API Cost Model

**New Module:** `literature_review/api_costs.py`

```python
from typing import Dict

API_PRICING = {
    'semantic_scholar': {
        'cost_per_call': 0.0,  # Free
        'rate_limit': 100,  # calls per 5 min
        'rate_limit_period': 300  # seconds
    },
    'arxiv': {
        'cost_per_call': 0.0,  # Free
        'rate_limit': 3,  # calls per second
        'rate_limit_period': 1
    },
    'crossref': {
        'cost_per_call': 0.0,  # Free
        'rate_limit': 50,
        'rate_limit_period': 1
    },
    'openai_embedding': {
        'cost_per_call': 0.0001,  # $0.0001 per 1K tokens (~1 call)
        'avg_tokens_per_call': 1000
    },
    'anthropic_claude': {
        'cost_per_1k_input_tokens': 0.003,  # $3 per 1M input tokens
        'cost_per_1k_output_tokens': 0.015,  # $15 per 1M output tokens
        'avg_input_tokens': 5000,
        'avg_output_tokens': 2000
    }
}

class CostEstimator:
    """Estimate API costs for searches"""
    
    def __init__(self, pricing=API_PRICING):
        self.pricing = pricing
    
    def estimate_search_cost(self, search_config: Dict) -> Dict:
        """Estimate cost for a single search"""
        api = search_config.get('api', 'semantic_scholar')
        num_calls = search_config.get('max_results', 10) // 10  # Assume 10 results per call
        
        if api not in self.pricing:
            return {'total_cost': 0.0, 'cost_per_call': 0.0, 'num_calls': num_calls}
        
        pricing = self.pricing[api]
        
        if 'cost_per_call' in pricing:
            # Simple per-call pricing
            cost_per_call = pricing['cost_per_call']
            total_cost = cost_per_call * num_calls
        
        elif 'cost_per_1k_input_tokens' in pricing:
            # Token-based pricing (LLM APIs)
            input_cost = (pricing['avg_input_tokens'] / 1000) * pricing['cost_per_1k_input_tokens']
            output_cost = (pricing['avg_output_tokens'] / 1000) * pricing['cost_per_1k_output_tokens']
            cost_per_call = input_cost + output_cost
            total_cost = cost_per_call * num_calls
        
        else:
            total_cost = 0.0
            cost_per_call = 0.0
        
        return {
            'total_cost': round(total_cost, 4),
            'cost_per_call': round(cost_per_call, 4),
            'num_calls': num_calls,
            'api': api
        }
    
    def estimate_job_cost(self, searches: list) -> Dict:
        """Estimate total cost for all searches in a job"""
        search_costs = []
        total_cost = 0.0
        
        for search in searches:
            cost_info = self.estimate_search_cost(search)
            search_costs.append({
                'query': search.get('query', ''),
                'cost': cost_info['total_cost'],
                'api': cost_info['api']
            })
            total_cost += cost_info['total_cost']
        
        return {
            'total_cost': round(total_cost, 2),
            'search_costs': search_costs,
            'num_searches': len(searches),
            'avg_cost_per_search': round(total_cost / len(searches), 4) if searches else 0
        }
```

### 2. Enhanced ROI Calculator

**Modified:** `literature_review/search_optimizer.py`

```python
from literature_review.api_costs import CostEstimator

class CostAwareSearchOptimizer(SearchOptimizer):
    """Search optimizer with cost-aware prioritization"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.cost_estimator = CostEstimator()
        self.budget_limit = config.get('roi_optimizer', {}).get('budget_limit', None)  # USD
        self.optimization_mode = config.get('roi_optimizer', {}).get('mode', 'balanced')  # 'coverage', 'cost', or 'balanced'
    
    def prioritize_searches(self, gaps, searches):
        """Prioritize searches with cost-aware ROI"""
        prioritized = []
        
        for search in searches:
            # Calculate traditional ROI
            gap_ids = search.get('target_gap_ids', [])
            target_gaps = [g for g in gaps if g['id'] in gap_ids]
            
            max_severity = max([g.get('severity', 5) for g in target_gaps]) if target_gaps else 5
            expected_papers = search.get('expected_papers', 5)
            
            # Calculate cost
            cost_info = self.cost_estimator.estimate_search_cost(search)
            api_cost = cost_info['total_cost']
            
            # Cost-adjusted ROI
            if self.optimization_mode == 'coverage':
                # Maximize coverage, ignore cost
                roi = (max_severity * expected_papers) / 1.0
                cost_weight = 0.0
            
            elif self.optimization_mode == 'cost':
                # Minimize cost, still consider value
                roi = (max_severity * expected_papers) / max(api_cost + 0.01, 0.01)  # +0.01 to avoid div by zero
                cost_weight = 1.0
            
            else:  # 'balanced'
                # Balance coverage and cost
                base_roi = max_severity * expected_papers
                cost_penalty = 1.0 / (1.0 + api_cost)  # Higher cost → lower penalty multiplier
                roi = base_roi * cost_penalty
                cost_weight = 0.5
            
            prioritized.append({
                **search,
                'roi': roi,
                'cost': api_cost,
                'cost_weight': cost_weight,
                'value_per_dollar': (max_severity * expected_papers) / max(api_cost, 0.01) if api_cost > 0 else float('inf')
            })
        
        # Sort by ROI
        prioritized.sort(key=lambda x: x['roi'], reverse=True)
        
        # Apply budget constraint if set
        if self.budget_limit:
            prioritized = self._apply_budget_constraint(prioritized, self.budget_limit)
        
        return prioritized
    
    def _apply_budget_constraint(self, searches, budget_limit):
        """Filter searches to fit within budget"""
        cumulative_cost = 0.0
        constrained_searches = []
        
        for search in searches:
            search_cost = search.get('cost', 0.0)
            
            if cumulative_cost + search_cost <= budget_limit:
                constrained_searches.append(search)
                cumulative_cost += search_cost
            else:
                # Mark as skipped due to budget
                search['skipped'] = True
                search['skip_reason'] = f'Budget exceeded (${cumulative_cost + search_cost:.2f} > ${budget_limit})'
        
        print(f"Budget constraint: {len(constrained_searches)}/{len(searches)} searches fit within ${budget_limit}")
        
        return constrained_searches
```

### 3. Configuration

**Enhanced:** `pipeline_config.json`

```json
{
  "roi_optimizer": {
    "enabled": true,
    "mode": "balanced",  // NEW: "coverage", "cost", or "balanced"
    "budget_limit": null,  // NEW: Max USD to spend (null = unlimited)
    "show_cost_estimates": true,  // NEW: Show cost breakdown before job
    "cost_tracking": {
      "enabled": true,
      "alert_threshold": 0.8  // Alert when 80% of budget used
    }
  }
}
```

### 4. Frontend: Cost Estimate Display

**New Component:** Pre-job cost estimate

```html
<!-- Cost Estimate Modal -->
<div class="modal" id="costEstimateModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5>Estimated Job Cost</h5>
            </div>
            <div class="modal-body">
                <div class="alert alert-info">
                    <strong>Total Estimated Cost:</strong> $<span id="total-cost">0.00</span>
                </div>
                
                <h6>Cost Breakdown</h6>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Search</th>
                            <th>API</th>
                            <th>Cost</th>
                        </tr>
                    </thead>
                    <tbody id="cost-breakdown">
                        <!-- Populated dynamically -->
                    </tbody>
                </table>
                
                {% if budget_limit %}
                <div class="alert alert-warning">
                    <strong>Budget Limit:</strong> ${{ budget_limit }}<br>
                    <span id="searches-skipped"></span> searches skipped due to budget.
                </div>
                {% endif %}
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button class="btn btn-primary" onclick="confirmAndStartJob()">
                    Start Job (Estimated $<span id="confirm-cost">0.00</span>)
                </button>
            </div>
        </div>
    </div>
</div>
```

**JavaScript:**
```javascript
async function showCostEstimate(jobConfig) {
    const response = await fetch('/api/estimate-cost', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(jobConfig)
    });
    
    const data = await response.json();
    
    // Display total cost
    document.getElementById('total-cost').textContent = data.total_cost.toFixed(2);
    document.getElementById('confirm-cost').textContent = data.total_cost.toFixed(2);
    
    // Populate breakdown table
    const tbody = document.getElementById('cost-breakdown');
    tbody.innerHTML = '';
    for (let search of data.search_costs) {
        tbody.innerHTML += `
            <tr>
                <td>${search.query}</td>
                <td>${search.api}</td>
                <td>$${search.cost.toFixed(4)}</td>
            </tr>
        `;
    }
    
    // Show budget warnings
    if (data.searches_skipped) {
        document.getElementById('searches-skipped').textContent = 
            `${data.searches_skipped} searches`;
    }
    
    // Show modal
    new bootstrap.Modal(document.getElementById('costEstimateModal')).show();
}
```

### 5. Backend API

**New Endpoint:** `POST /api/estimate-cost`

```python
@app.route('/api/estimate-cost', methods=['POST'])
def estimate_cost():
    """Estimate cost for a job configuration"""
    job_config = request.json
    searches = job_config.get('searches', [])
    
    estimator = CostEstimator()
    estimate = estimator.estimate_job_cost(searches)
    
    # Check budget constraint
    budget_limit = job_config.get('budget_limit')
    if budget_limit:
        searches_in_budget = [s for s in estimate['search_costs'] if s['cost'] <= budget_limit]
        estimate['searches_skipped'] = len(searches) - len(searches_in_budget)
    
    return jsonify(estimate)
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_cost_aware_roi.py`

```python
def test_estimate_search_cost():
    """Test cost estimation for single search"""
    estimator = CostEstimator()
    
    search = {'api': 'semantic_scholar', 'max_results': 100}
    cost = estimator.estimate_search_cost(search)
    
    assert cost['total_cost'] == 0.0  # Semantic Scholar is free

def test_estimate_llm_cost():
    """Test token-based cost estimation"""
    estimator = CostEstimator()
    
    search = {'api': 'anthropic_claude', 'max_results': 10}
    cost = estimator.estimate_search_cost(search)
    
    assert cost['total_cost'] > 0  # Claude has cost

def test_cost_aware_prioritization():
    """Test searches prioritized by cost-efficiency"""
    gaps = [{'id': 'gap1', 'severity': 8}]
    searches = [
        {'query': 'expensive', 'target_gap_ids': ['gap1'], 'expected_papers': 5, 'api': 'anthropic_claude'},
        {'query': 'free', 'target_gap_ids': ['gap1'], 'expected_papers': 5, 'api': 'semantic_scholar'}
    ]
    
    config = {'roi_optimizer': {'mode': 'cost'}}
    optimizer = CostAwareSearchOptimizer(config=config)
    prioritized = optimizer.prioritize_searches(gaps, searches)
    
    # Free search should be first
    assert prioritized[0]['query'] == 'free'

def test_budget_constraint():
    """Test budget limit enforcement"""
    searches = [
        {'query': 'search1', 'cost': 5.0},
        {'query': 'search2', 'cost': 3.0},
        {'query': 'search3', 'cost': 4.0}
    ]
    
    optimizer = CostAwareSearchOptimizer()
    constrained = optimizer._apply_budget_constraint(searches, budget_limit=8.0)
    
    # Only first two searches fit in $8 budget
    assert len(constrained) == 2
    assert constrained[0]['query'] == 'search1'
    assert constrained[1]['query'] == 'search2'
```

---

## 📚 Documentation Updates

**File:** `docs/SEARCH_OPTIMIZATION_GUIDE.md`

**New Section:**
```markdown
## Cost-Aware Search Optimization

### Optimization Modes

**Coverage Mode** (`mode: "coverage"`):
- Maximize gap coverage
- Ignore API costs
- Use when budget not a concern

**Cost Mode** (`mode: "cost"`):
- Minimize API costs
- Still prioritize high-value gaps
- Use for tight budgets

**Balanced Mode** (`mode: "balanced"`):
- Balance coverage and cost
- Default recommendation

### Setting a Budget

```json
{
  "roi_optimizer": {
    "mode": "balanced",
    "budget_limit": 50.0  // Max $50
  }
}
```

**What Happens:**
1. System estimates cost for all searches
2. Sorts by ROI (cost-adjusted)
3. Selects searches until budget reached
4. Skips remaining searches

### Cost Estimates

Before starting a job, view estimated costs:

```
Estimated Job Cost: $12.45
=========================================
Search 1: "machine learning papers" - $0.00 (Semantic Scholar)
Search 2: "deep learning survey" - $0.00 (arXiv)
Search 3: "LLM analysis" - $12.45 (Claude API)

Total: $12.45
```

### API Pricing

**Free APIs:**
- Semantic Scholar: $0
- arXiv: $0
- CrossRef: $0

**Paid APIs:**
- OpenAI Embeddings: ~$0.0001 per search
- Claude (LLM): ~$0.02-$0.10 per search
```

---

## ✅ Definition of Done

- [ ] `CostEstimator` class implemented
- [ ] API pricing model defined
- [ ] Cost-aware ROI calculation
- [ ] Budget constraint enforcement
- [ ] Frontend cost estimate modal
- [ ] `/api/estimate-cost` endpoint
- [ ] Unit tests (≥90% coverage)
- [ ] Documentation updated
- [ ] Code review approved
- [ ] Merged to main branch
