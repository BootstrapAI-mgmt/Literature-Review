# Task Card: Phase 4 Enhanced UI Integration

**Task ID:** INTEGRATE-SYNC1-UI  
**Wave:** Integration  
**Priority:** HIGH  
**Estimated Effort:** 3-4 hours  
**Status:** Not Started  
**Dependencies:** 
- Enhanced output API endpoints (✅ Complete)
- Wave 1 enhancements merged (✅ Complete)
- Wave 2.1 Sufficiency Matrix merged (✅ Complete)

---

## Objective

Add frontend UI components to display enhanced analytical outputs (Proof Scorecard, Cost Summary, Sufficiency Matrix) in the dashboard's job results view.

## Background

The backend API endpoints for enhanced outputs have been implemented and tested. This task adds the frontend Vue.js components and HTML templates to display these outputs in an attractive, user-friendly manner.

**Current State:**
- ✅ API endpoints exist at `/api/jobs/{job_id}/proof-scorecard`, `/cost-summary`, `/sufficiency-summary`
- ✅ All endpoints return structured JSON with `available` flag
- ✅ 10 integration tests passing
- ❌ UI doesn't fetch or display enhanced outputs yet

**Target State:**
- ✅ Job details page shows 3 enhanced output cards (when available)
- ✅ Cards display summary data with visual indicators
- ✅ Links to full HTML reports work
- ✅ Graceful handling when outputs not yet generated

---

## Success Criteria

- [ ] Proof Scorecard card displays overall score, verdict, and headline
- [ ] Cost Summary card shows total cost, budget usage, and per-paper cost
- [ ] Sufficiency Matrix card shows quadrant distribution
- [ ] All cards have "View Full Report" links that open HTML visualizations
- [ ] Cards only appear when data is available (no broken placeholders)
- [ ] Visual indicators use color coding (score ranges, budget thresholds)
- [ ] Responsive design works on desktop and mobile

---

## Implementation

### File: `webdashboard/templates/index.html`

**Location:** After job details section, before job list

**Add Enhanced Outputs Section:**

```html
<!-- Enhanced Analytical Outputs Section -->
<div v-if="selectedJob && selectedJob.status === 'completed'" class="enhanced-outputs-section">
    <h3 class="section-title">📊 Enhanced Analysis</h3>
    
    <div class="enhanced-cards-grid">
        
        <!-- Proof Scorecard Card -->
        <div v-if="selectedJob.proofScorecard && selectedJob.proofScorecard.available" 
             class="enhanced-card proof-scorecard-card">
            <div class="card-header">
                <span class="card-icon">🎯</span>
                <h4>Proof Completeness Scorecard</h4>
            </div>
            <div class="card-body">
                <div class="score-circle" :class="getScoreClass(selectedJob.proofScorecard.overall_score)">
                    <div class="score-value">{{ selectedJob.proofScorecard.overall_score }}%</div>
                    <div class="score-label">Ready</div>
                </div>
                <div class="verdict-badge" :class="getVerdictClass(selectedJob.proofScorecard.verdict)">
                    {{ selectedJob.proofScorecard.verdict }}
                </div>
                <p class="headline">{{ selectedJob.proofScorecard.headline }}</p>
                
                <div class="next-steps" v-if="selectedJob.proofScorecard.next_steps">
                    <strong>Top Priorities:</strong>
                    <ul>
                        <li v-for="step in selectedJob.proofScorecard.next_steps.slice(0, 3)" :key="step">
                            {{ step }}
                        </li>
                    </ul>
                </div>
                
                <a :href="selectedJob.proofScorecard.html_path" 
                   target="_blank" 
                   class="btn btn-primary btn-full-report">
                    📄 View Full Report
                </a>
            </div>
        </div>
        
        <!-- Cost Summary Card -->
        <div v-if="selectedJob.costSummary && selectedJob.costSummary.available" 
             class="enhanced-card cost-summary-card">
            <div class="card-header">
                <span class="card-icon">💰</span>
                <h4>API Cost Summary</h4>
            </div>
            <div class="card-body">
                <div class="cost-metrics">
                    <div class="metric-row">
                        <span class="metric-label">Total Cost:</span>
                        <span class="metric-value cost-total">
                            ${{ selectedJob.costSummary.total_cost.toFixed(2) }}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Per Paper:</span>
                        <span class="metric-value">
                            ${{ selectedJob.costSummary.per_paper_cost.toFixed(2) }}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Budget Used:</span>
                        <span class="metric-value">
                            <div class="progress-bar-container">
                                <div class="progress-bar" 
                                     :style="{width: selectedJob.costSummary.budget_percent + '%'}"
                                     :class="getBudgetClass(selectedJob.costSummary.budget_percent)">
                                </div>
                                <span class="progress-text">
                                    {{ selectedJob.costSummary.budget_percent.toFixed(1) }}%
                                </span>
                            </div>
                        </span>
                    </div>
                    <div class="metric-row" v-if="selectedJob.costSummary.cache_savings > 0">
                        <span class="metric-label">Cache Savings:</span>
                        <span class="metric-value savings">
                            -${{ selectedJob.costSummary.cache_savings.toFixed(2) }}
                        </span>
                    </div>
                </div>
                
                <a :href="selectedJob.costSummary.html_path" 
                   target="_blank" 
                   class="btn btn-primary btn-full-report">
                    📊 View Breakdown
                </a>
            </div>
        </div>
        
        <!-- Sufficiency Matrix Card -->
        <div v-if="selectedJob.sufficiencySummary && selectedJob.sufficiencySummary.available" 
             class="enhanced-card sufficiency-card">
            <div class="card-header">
                <span class="card-icon">📈</span>
                <h4>Evidence Sufficiency Matrix</h4>
            </div>
            <div class="card-body">
                <div class="quadrant-grid">
                    <div class="quadrant q1" 
                         v-if="selectedJob.sufficiencySummary.quadrants['Q1-Strong-Foundation']">
                        <div class="quadrant-name">Strong Foundation</div>
                        <div class="quadrant-count">
                            {{ selectedJob.sufficiencySummary.quadrants['Q1-Strong-Foundation'] }}
                        </div>
                    </div>
                    <div class="quadrant q2" 
                         v-if="selectedJob.sufficiencySummary.quadrants['Q2-Promising-Seeds']">
                        <div class="quadrant-name">Promising Seeds</div>
                        <div class="quadrant-count">
                            {{ selectedJob.sufficiencySummary.quadrants['Q2-Promising-Seeds'] }}
                        </div>
                    </div>
                    <div class="quadrant q3" 
                         v-if="selectedJob.sufficiencySummary.quadrants['Q3-Hollow-Coverage']">
                        <div class="quadrant-name">Hollow Coverage</div>
                        <div class="quadrant-count">
                            {{ selectedJob.sufficiencySummary.quadrants['Q3-Hollow-Coverage'] }}
                        </div>
                    </div>
                    <div class="quadrant q4" 
                         v-if="selectedJob.sufficiencySummary.quadrants['Q4-Critical-Gaps']">
                        <div class="quadrant-name">Critical Gaps</div>
                        <div class="quadrant-count">
                            {{ selectedJob.sufficiencySummary.quadrants['Q4-Critical-Gaps'] }}
                        </div>
                    </div>
                </div>
                
                <div class="recommendations" v-if="selectedJob.sufficiencySummary.recommendations">
                    <strong>Top Recommendations:</strong>
                    <ul>
                        <li v-for="rec in selectedJob.sufficiencySummary.recommendations.slice(0, 2)" :key="rec">
                            {{ rec }}
                        </li>
                    </ul>
                </div>
                
                <a :href="selectedJob.sufficiencySummary.html_path" 
                   target="_blank" 
                   class="btn btn-primary btn-full-report">
                    🔍 View Interactive Matrix
                </a>
            </div>
        </div>
        
    </div>
</div>
```

**Add Vue.js Methods:**

```javascript
// In the Vue app methods section

async fetchEnhancedOutputs(jobId) {
    // Fetch all enhanced outputs in parallel
    try {
        const [proofRes, costRes, sufficiencyRes] = await Promise.all([
            fetch(`/api/jobs/${jobId}/proof-scorecard`, {
                headers: {'X-API-KEY': this.apiKey}
            }),
            fetch(`/api/jobs/${jobId}/cost-summary`, {
                headers: {'X-API-KEY': this.apiKey}
            }),
            fetch(`/api/jobs/${jobId}/sufficiency-summary`, {
                headers: {'X-API-KEY': this.apiKey}
            })
        ]);
        
        if (proofRes.ok) {
            this.selectedJob.proofScorecard = await proofRes.json();
        }
        if (costRes.ok) {
            this.selectedJob.costSummary = await costRes.json();
        }
        if (sufficiencyRes.ok) {
            this.selectedJob.sufficiencySummary = await sufficiencyRes.json();
        }
    } catch (error) {
        console.error('Failed to fetch enhanced outputs:', error);
    }
},

getScoreClass(score) {
    if (score >= 60) return 'score-high';
    if (score >= 40) return 'score-medium';
    return 'score-low';
},

getVerdictClass(verdict) {
    const verdictMap = {
        'STRONG': 'verdict-strong',
        'MODERATE': 'verdict-moderate',
        'WEAK': 'verdict-weak',
        'INSUFFICIENT': 'verdict-insufficient'
    };
    return verdictMap[verdict] || 'verdict-unknown';
},

getBudgetClass(percent) {
    if (percent > 80) return 'budget-high';
    if (percent > 50) return 'budget-medium';
    return 'budget-low';
}
```

**Update `selectJob` method to fetch enhanced outputs:**

```javascript
async selectJob(job) {
    this.selectedJob = job;
    
    // Fetch logs if completed
    if (job.status === 'completed' || job.status === 'failed') {
        await this.fetchLogs(job.id);
    }
    
    // Fetch enhanced outputs if completed
    if (job.status === 'completed') {
        await this.fetchEnhancedOutputs(job.id);
    }
}
```

**Add CSS Styles:**

```css
/* Enhanced Outputs Section */
.enhanced-outputs-section {
    margin-top: 30px;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
}

.section-title {
    font-size: 1.5em;
    margin-bottom: 20px;
    color: #333;
}

.enhanced-cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
}

.enhanced-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    overflow: hidden;
}

.enhanced-card .card-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.enhanced-card .card-icon {
    font-size: 1.5em;
}

.enhanced-card h4 {
    margin: 0;
    font-size: 1.1em;
}

.enhanced-card .card-body {
    padding: 20px;
}

/* Proof Scorecard Styles */
.score-circle {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin: 20px auto;
    border: 8px solid;
}

.score-circle.score-high {
    border-color: #28a745;
    color: #28a745;
}

.score-circle.score-medium {
    border-color: #ffc107;
    color: #ffc107;
}

.score-circle.score-low {
    border-color: #dc3545;
    color: #dc3545;
}

.score-value {
    font-size: 2em;
    font-weight: bold;
}

.score-label {
    font-size: 0.9em;
    text-transform: uppercase;
}

.verdict-badge {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: bold;
    margin: 10px 0;
}

.verdict-strong { background: #d4edda; color: #155724; }
.verdict-moderate { background: #fff3cd; color: #856404; }
.verdict-weak { background: #f8d7da; color: #721c24; }
.verdict-insufficient { background: #f8d7da; color: #721c24; }

.headline {
    font-style: italic;
    color: #666;
    margin: 15px 0;
}

.next-steps {
    margin-top: 15px;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 4px;
}

.next-steps ul {
    margin: 5px 0 0 0;
    padding-left: 20px;
}

.next-steps li {
    margin: 5px 0;
    font-size: 0.9em;
}

/* Cost Summary Styles */
.cost-metrics {
    margin: 20px 0;
}

.metric-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #eee;
}

.metric-row:last-child {
    border-bottom: none;
}

.metric-label {
    font-weight: 500;
    color: #666;
}

.metric-value {
    font-weight: bold;
    font-size: 1.1em;
}

.metric-value.cost-total {
    color: #667eea;
    font-size: 1.5em;
}

.metric-value.savings {
    color: #28a745;
}

.progress-bar-container {
    position: relative;
    width: 150px;
    height: 24px;
    background: #e9ecef;
    border-radius: 12px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    transition: width 0.3s ease;
    border-radius: 12px;
}

.progress-bar.budget-low {
    background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
}

.progress-bar.budget-medium {
    background: linear-gradient(90deg, #ffc107 0%, #fd7e14 100%);
}

.progress-bar.budget-high {
    background: linear-gradient(90deg, #dc3545 0%, #c82333 100%);
}

.progress-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 0.85em;
    font-weight: bold;
    color: #333;
}

/* Sufficiency Matrix Styles */
.quadrant-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 20px 0;
}

.quadrant {
    padding: 15px;
    border-radius: 8px;
    text-align: center;
}

.quadrant.q1 {
    background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    border: 2px solid #28a745;
}

.quadrant.q2 {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
    border: 2px solid #ffc107;
}

.quadrant.q3 {
    background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    border: 2px solid #dc3545;
}

.quadrant.q4 {
    background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
    border: 2px solid #17a2b8;
}

.quadrant-name {
    font-weight: 600;
    font-size: 0.85em;
    margin-bottom: 8px;
}

.quadrant-count {
    font-size: 2em;
    font-weight: bold;
}

.recommendations {
    margin-top: 15px;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 4px;
}

.recommendations ul {
    margin: 5px 0 0 0;
    padding-left: 20px;
}

.recommendations li {
    margin: 5px 0;
    font-size: 0.9em;
}

/* Button Styles */
.btn-full-report {
    display: block;
    width: 100%;
    margin-top: 20px;
    padding: 12px;
    text-align: center;
    text-decoration: none;
    border-radius: 6px;
    font-weight: 600;
    transition: all 0.3s ease;
}

.btn-full-report:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

/* Responsive Design */
@media (max-width: 768px) {
    .enhanced-cards-grid {
        grid-template-columns: 1fr;
    }
    
    .quadrant-grid {
        grid-template-columns: 1fr;
    }
}
```

---

## Testing Plan

### Manual Testing

1. **Complete Pipeline Run**
   ```bash
   # Upload papers via dashboard
   # Configure and start job
   # Wait for completion
   # Verify all 3 enhanced cards appear
   ```

2. **Individual Card Verification**
   - Proof Scorecard: Check score color, verdict badge, next steps
   - Cost Summary: Verify budget bar color changes with percentage
   - Sufficiency Matrix: Confirm quadrant colors and counts
   - All: Click "View Full Report" links → HTML opens in new tab

3. **Edge Cases**
   - Job not yet completed → cards don't appear
   - Job failed → cards don't appear
   - Missing output files → card doesn't appear (graceful)

### Automated Testing

Add Selenium/Playwright tests:

```python
def test_enhanced_outputs_display(browser, completed_job_id):
    """Test that enhanced output cards display correctly."""
    browser.get(f"http://localhost:8000")
    
    # Select completed job
    job_row = browser.find_element_by_css_selector(f"[data-job-id='{completed_job_id}']")
    job_row.click()
    
    # Wait for enhanced outputs to load
    time.sleep(2)
    
    # Verify cards are present
    assert browser.find_element_by_css_selector(".proof-scorecard-card")
    assert browser.find_element_by_css_selector(".cost-summary-card")
    assert browser.find_element_by_css_selector(".sufficiency-card")
    
    # Verify score is displayed
    score = browser.find_element_by_css_selector(".score-value").text
    assert score.endswith("%")
    
    # Verify cost is displayed
    cost = browser.find_element_by_css_selector(".cost-total").text
    assert cost.startswith("$")
```

---

## Acceptance Criteria

- [ ] All 3 enhanced output cards display when job is completed
- [ ] Cards show correct data from API responses
- [ ] Score/verdict/budget use correct color coding
- [ ] "View Full Report" links open HTML in new tab
- [ ] Cards don't appear when data unavailable (no errors)
- [ ] Responsive design works on mobile
- [ ] Loading states prevent flickering
- [ ] No console errors

---

## Effort Breakdown

- **HTML Template Updates**: 1.5 hours
  - Add card HTML structure
  - Add Vue.js methods
  - Update selectJob method
  
- **CSS Styling**: 1 hour
  - Card layouts
  - Color schemes
  - Responsive breakpoints
  
- **Testing**: 1 hour
  - Manual testing on completed job
  - Edge case verification
  - Cross-browser testing
  
- **Documentation**: 0.5 hours
  - Update USER_MANUAL.md
  - Screenshot capture

**Total**: 4 hours

---

## Dependencies

**Completed:**
- ✅ Backend API endpoints implemented
- ✅ Integration tests passing
- ✅ Enhanced outputs generating correctly

**Required:**
- Dashboard running on localhost:8000
- At least one completed job with outputs

---

## Risks & Mitigation

**Risk**: Vue.js state management complexity  
**Mitigation**: Use simple reactive properties, avoid Vuex for now  
**Contingency**: Fall back to vanilla JavaScript fetch/DOM manipulation

**Risk**: CSS conflicts with existing styles  
**Mitigation**: Use scoped class names (`.enhanced-card`, `.enhanced-*`)  
**Contingency**: Use more specific selectors or !important (sparingly)

**Risk**: API responses not matching expected format  
**Mitigation**: Always check `available` flag before accessing data  
**Contingency**: Add defensive null checks throughout

---

## Success Metrics

- [ ] Cards appear within 2 seconds of job selection
- [ ] All visual indicators use correct colors
- [ ] Links open successfully in 100% of cases
- [ ] Zero JavaScript console errors
- [ ] Mobile view works on screens ≥320px wide

---

**Document Status**: ✅ Ready for Implementation  
**Next Action**: Assign to dashboard developer  
**Owner**: Dashboard developer  
**Created**: November 17, 2025  
**Related**: SYNC_POINT_1_WEEK3.md Task 5
