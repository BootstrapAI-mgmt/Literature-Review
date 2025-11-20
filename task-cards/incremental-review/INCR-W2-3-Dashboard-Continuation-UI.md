# INCR-W2-3: Dashboard Continuation UI

**Wave:** 2 (Integration)  
**Priority:** 🟠 High  
**Effort:** 6-8 hours  
**Status:** 🟡 Blocked (requires INCR-W2-2)  
**Assignable:** Frontend Developer

---

## Overview

Implement user interface for continuing previous reviews in the web dashboard. Users can select a base job, view its gaps, upload new papers, and trigger incremental analysis - all through an intuitive UI.

---

## Dependencies

**Prerequisites:**
- ✅ INCR-W2-2 (Dashboard Job Continuation API)

**Blocks:**
- INCR-W3-1 (Dashboard Job Genealogy Visualization)

---

## Scope

### Included
- [x] "Continue Review" mode toggle on upload page
- [x] Base job selector dropdown
- [x] Gap summary display (gap count, pillar breakdown)
- [x] New paper upload form
- [x] Relevance preview (before starting job)
- [x] Progress tracking for continuation jobs
- [x] Responsive design

### Excluded
- ❌ Drag-and-drop job reordering
- ❌ Real-time collaboration
- ❌ Gap editing UI (future enhancement)

---

## Technical Specification

### UI Mockup

```
┌─────────────────────────────────────────────────────────────┐
│  Literature Review Dashboard                    [User Menu] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 New Gap Analysis                                         │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Analysis Mode:                                       │   │
│  │  ○ New Review (baseline)                            │   │
│  │  ● Continue Existing Review (incremental)           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Select Base Job:                                     │   │
│  │  [Review - Jan 2025 (job_20250115_103000)    ▼]    │   │
│  │                                                       │   │
│  │  📊 Gap Summary:                                     │   │
│  │  ├─ Total Gaps: 28                                   │   │
│  │  ├─ Pillar 1: 5 gaps                                │   │
│  │  ├─ Pillar 2: 8 gaps                                │   │
│  │  └─ Pillar 3: 15 gaps                               │   │
│  │                                                       │   │
│  │  [View Gap Details →]                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Upload New Papers:                                   │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │ Drop PDF files here or click to browse       │  │   │
│  │  │                                                 │  │   │
│  │  │          [Browse Files]                        │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  📄 Uploaded: 25 papers                              │   │
│  │     - paper1.pdf (✓ Relevant - 72%)                 │   │
│  │     - paper2.pdf (✓ Relevant - 68%)                 │   │
│  │     - paper3.pdf (⚠ Low relevance - 35%)            │   │
│  │     ...                                               │   │
│  │                                                       │   │
│  │  [Preview Relevance Scores]                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Analysis Settings:                                   │   │
│  │  Relevance Threshold: [50%    ═══════○────]        │   │
│  │  Papers to analyze: 12 / 25 (48% filtered)          │   │
│  │  Estimated cost: $3.50                               │   │
│  │  Estimated time: ~15 minutes                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  [Cancel]                    [Start Incremental Analysis →] │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation

### File Structure

```
webdashboard/
├── templates/
│   ├── upload.html (update existing)
│   ├── partials/
│   │   ├── continuation_mode_selector.html (NEW)
│   │   ├── base_job_selector.html (NEW)
│   │   ├── gap_summary_panel.html (NEW)
│   │   └── relevance_preview.html (NEW)
├── static/
│   ├── js/
│   │   ├── continuation.js (NEW)
│   │   └── relevance_preview.js (NEW)
│   └── css/
│       └── continuation.css (NEW)
```

### HTML Templates

#### templates/partials/continuation_mode_selector.html

```html
<div class="mode-selector card mb-4">
    <div class="card-body">
        <h5 class="card-title">Analysis Mode</h5>
        <div class="form-check">
            <input class="form-check-input" type="radio" name="analysisMode" 
                   id="modeBaseline" value="baseline" checked>
            <label class="form-check-label" for="modeBaseline">
                <strong>New Review</strong> (baseline)
                <small class="text-muted d-block">
                    Analyze all papers from scratch
                </small>
            </label>
        </div>
        <div class="form-check mt-2">
            <input class="form-check-input" type="radio" name="analysisMode" 
                   id="modeContinuation" value="continuation">
            <label class="form-check-label" for="modeContinuation">
                <strong>Continue Existing Review</strong> (incremental)
                <small class="text-muted d-block">
                    Add new papers to previous analysis
                </small>
            </label>
        </div>
    </div>
</div>
```

#### templates/partials/base_job_selector.html

```html
<div id="baseJobSelector" class="card mb-4" style="display: none;">
    <div class="card-body">
        <h5 class="card-title">Select Base Job</h5>
        
        <div class="mb-3">
            <label for="baseJobDropdown" class="form-label">
                Choose a completed review to continue:
            </label>
            <select class="form-select" id="baseJobDropdown">
                <option value="">-- Select a job --</option>
                <!-- Populated dynamically via JS -->
            </select>
        </div>
        
        <div id="gapSummaryPanel" style="display: none;">
            <!-- Gap summary loaded here -->
        </div>
    </div>
</div>
```

#### templates/partials/gap_summary_panel.html

```html
<div class="gap-summary">
    <h6>📊 Gap Summary</h6>
    <div class="alert alert-info">
        <strong id="totalGaps">--</strong> open gaps found in base review
    </div>
    
    <div class="gap-breakdown">
        <h6>Gaps by Pillar:</h6>
        <ul id="gapsByPillar" class="list-unstyled">
            <!-- Populated dynamically -->
        </ul>
    </div>
    
    <button class="btn btn-sm btn-outline-primary" 
            id="viewGapDetailsBtn">
        View Gap Details →
    </button>
</div>
```

#### templates/partials/relevance_preview.html

```html
<div id="relevancePreview" class="card mb-4" style="display: none;">
    <div class="card-body">
        <h5 class="card-title">Relevance Preview</h5>
        
        <div class="mb-3">
            <label for="relevanceThreshold" class="form-label">
                Relevance Threshold: <strong id="thresholdValue">50%</strong>
            </label>
            <input type="range" class="form-range" id="relevanceThreshold" 
                   min="0" max="100" value="50">
        </div>
        
        <div class="alert alert-secondary">
            <strong id="papersToAnalyze">--</strong> papers will be analyzed
            (<strong id="papersSkipped">--</strong> filtered out)
        </div>
        
        <div class="paper-list" id="paperRelevanceList">
            <!-- Populated with uploaded papers + scores -->
        </div>
        
        <div class="estimates mt-3">
            <small class="text-muted">
                Estimated cost: <strong id="estimatedCost">--</strong><br>
                Estimated time: <strong id="estimatedTime">--</strong>
            </small>
        </div>
    </div>
</div>
```

### JavaScript

#### static/js/continuation.js

```javascript
/**
 * Dashboard Continuation Mode Logic
 */

let selectedBaseJob = null;
let uploadedPapers = [];
let gapData = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initModeSwitcher();
    initBaseJobSelector();
    initRelevancePreview();
});

function initModeSwitcher() {
    const baselineRadio = document.getElementById('modeBaseline');
    const continuationRadio = document.getElementById('modeContinuation');
    const baseJobSelector = document.getElementById('baseJobSelector');
    
    baselineRadio.addEventListener('change', () => {
        baseJobSelector.style.display = 'none';
        selectedBaseJob = null;
    });
    
    continuationRadio.addEventListener('change', () => {
        baseJobSelector.style.display = 'block';
        loadAvailableJobs();
    });
}

async function loadAvailableJobs() {
    try {
        const response = await fetch('/api/jobs?status=completed');
        const jobs = await response.json();
        
        const dropdown = document.getElementById('baseJobDropdown');
        dropdown.innerHTML = '<option value="">-- Select a job --</option>';
        
        jobs.forEach(job => {
            const option = document.createElement('option');
            option.value = job.job_id;
            option.textContent = `${job.name || job.job_id} (${new Date(job.created_at).toLocaleDateString()})`;
            dropdown.appendChild(option);
        });
        
        dropdown.addEventListener('change', handleBaseJobSelection);
    } catch (error) {
        console.error('Failed to load jobs:', error);
        alert('Error loading available jobs');
    }
}

async function handleBaseJobSelection(event) {
    selectedBaseJob = event.target.value;
    
    if (!selectedBaseJob) {
        document.getElementById('gapSummaryPanel').style.display = 'none';
        return;
    }
    
    // Load gaps for selected job
    try {
        const response = await fetch(`/api/jobs/${selectedBaseJob}/gaps`);
        gapData = await response.json();
        
        displayGapSummary(gapData);
    } catch (error) {
        console.error('Failed to load gaps:', error);
        alert('Error loading gap data');
    }
}

function displayGapSummary(gaps) {
    const panel = document.getElementById('gapSummaryPanel');
    panel.style.display = 'block';
    
    document.getElementById('totalGaps').textContent = gaps.total_gaps;
    
    const pillarList = document.getElementById('gapsByPillar');
    pillarList.innerHTML = '';
    
    for (const [pillarId, count] of Object.entries(gaps.gaps_by_pillar)) {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${pillarId}:</strong> ${count} gaps`;
        pillarList.appendChild(li);
    }
}

function initRelevancePreview() {
    const threshold = document.getElementById('relevanceThreshold');
    const thresholdValue = document.getElementById('thresholdValue');
    
    threshold.addEventListener('input', (e) => {
        thresholdValue.textContent = `${e.target.value}%`;
        updateRelevancePreview();
    });
}

async function updateRelevancePreview() {
    if (!selectedBaseJob || uploadedPapers.length === 0) return;
    
    const threshold = document.getElementById('relevanceThreshold').value / 100;
    
    try {
        const response = await fetch(`/api/jobs/${selectedBaseJob}/relevance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                papers: uploadedPapers,
                threshold: threshold
            })
        });
        
        const result = await response.json();
        
        // Update UI
        document.getElementById('papersToAnalyze').textContent = result.papers_above_threshold;
        document.getElementById('papersSkipped').textContent = result.papers_below_threshold;
        document.getElementById('estimatedCost').textContent = `$${(result.papers_above_threshold * 0.25).toFixed(2)}`;
        document.getElementById('estimatedTime').textContent = `~${Math.ceil(result.papers_above_threshold * 1.5)} minutes`;
        
        // Display paper list with scores
        displayPaperRelevanceList(result.scores, threshold);
    } catch (error) {
        console.error('Failed to get relevance scores:', error);
    }
}

function displayPaperRelevanceList(scores, threshold) {
    const list = document.getElementById('paperRelevanceList');
    list.innerHTML = '';
    
    scores.forEach(score => {
        const div = document.createElement('div');
        div.className = `paper-item ${score.relevance_score >= threshold ? 'relevant' : 'irrelevant'}`;
        
        const icon = score.relevance_score >= threshold ? '✓' : '⚠';
        const label = score.relevance_score >= threshold ? 'Relevant' : 'Low relevance';
        
        div.innerHTML = `
            <span class="icon">${icon}</span>
            <span class="title">${score.title}</span>
            <span class="score">${label} - ${Math.round(score.relevance_score * 100)}%</span>
        `;
        
        list.appendChild(div);
    });
}

// File upload handler
function handleFileUpload(files) {
    // Extract paper metadata from uploaded PDFs
    uploadedPapers = Array.from(files).map(file => ({
        filename: file.name,
        // Additional metadata extraction would happen here
    }));
    
    document.getElementById('relevancePreview').style.display = 'block';
    updateRelevancePreview();
}

// Start analysis
async function startContinuationAnalysis() {
    if (!selectedBaseJob) {
        alert('Please select a base job');
        return;
    }
    
    const threshold = document.getElementById('relevanceThreshold').value / 100;
    
    try {
        const response = await fetch(`/api/jobs/${selectedBaseJob}/continue`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                papers: uploadedPapers,
                relevance_threshold: threshold,
                prefilter_enabled: true
            })
        });
        
        const result = await response.json();
        
        // Redirect to job status page
        window.location.href = `/jobs/${result.job_id}`;
    } catch (error) {
        console.error('Failed to start continuation:', error);
        alert('Error starting incremental analysis');
    }
}
```

### CSS

#### static/css/continuation.css

```css
/* Continuation Mode Styles */

.mode-selector .form-check {
    padding: 1rem;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    transition: all 0.2s;
}

.mode-selector .form-check:hover {
    background-color: #f8f9fa;
    border-color: #007bff;
}

.mode-selector .form-check-input:checked + .form-check-label {
    font-weight: bold;
    color: #007bff;
}

.gap-summary {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
}

.gap-breakdown ul {
    margin: 0.5rem 0;
}

.gap-breakdown li {
    padding: 0.25rem 0;
}

.paper-item {
    display: flex;
    align-items: center;
    padding: 0.5rem;
    margin: 0.25rem 0;
    border-radius: 4px;
}

.paper-item.relevant {
    background: #d4edda;
    border-left: 4px solid #28a745;
}

.paper-item.irrelevant {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
}

.paper-item .icon {
    margin-right: 0.5rem;
    font-size: 1.2rem;
}

.paper-item .title {
    flex: 1;
    font-weight: 500;
}

.paper-item .score {
    color: #6c757d;
    font-size: 0.875rem;
}

.estimates {
    border-top: 1px solid #dee2e6;
    padding-top: 1rem;
}
```

---

## Testing Strategy

### Manual Testing Checklist

- [ ] Mode toggle switches between baseline/continuation
- [ ] Base job dropdown loads completed jobs
- [ ] Gap summary displays correctly
- [ ] File upload triggers relevance preview
- [ ] Threshold slider updates preview in real-time
- [ ] Paper list shows relevant/irrelevant papers
- [ ] Start button creates continuation job
- [ ] Redirects to job status page

### Automated Tests

```javascript
// tests/webui/test_continuation_ui.js

describe('Continuation Mode UI', () => {
    test('Mode switcher shows/hides base job selector', async () => {
        const page = await browser.newPage();
        await page.goto('http://localhost:5000/upload');
        
        // Initially hidden
        const selector = await page.$('#baseJobSelector');
        expect(await selector.isVisible()).toBe(false);
        
        // Click continuation mode
        await page.click('#modeContinuation');
        
        // Now visible
        expect(await selector.isVisible()).toBe(true);
    });
    
    test('Base job selection loads gap summary', async () => {
        const page = await browser.newPage();
        await page.goto('http://localhost:5000/upload');
        
        await page.click('#modeContinuation');
        await page.selectOption('#baseJobDropdown', 'test_job_001');
        
        // Wait for gap summary
        await page.waitForSelector('#gapSummaryPanel');
        
        const gapCount = await page.textContent('#totalGaps');
        expect(parseInt(gapCount)).toBeGreaterThan(0);
    });
});
```

---

## Deliverables

- [ ] HTML templates for continuation mode
- [ ] JavaScript logic (continuation.js)
- [ ] CSS styling (continuation.css)
- [ ] Integration with existing upload page
- [ ] Manual testing completed
- [ ] Automated UI tests (Playwright/Selenium)
- [ ] User documentation

---

## Success Criteria

✅ **Functional:**
- Can toggle between baseline/continuation modes
- Base job selector works
- Gap summary loads correctly
- Relevance preview accurate
- Continuation job starts successfully

✅ **UX:**
- Intuitive workflow (< 3 clicks to start)
- Clear visual feedback
- Responsive design (mobile-friendly)
- No confusing error messages

✅ **Performance:**
- Gap summary loads < 1s
- Relevance preview updates < 2s
- No UI blocking during API calls

---

**Status:** 🟡 Blocked (requires INCR-W2-2)  
**Assignee:** TBD  
**Estimated Start:** Week 2, Day 2  
**Estimated Completion:** Week 2, Day 4
