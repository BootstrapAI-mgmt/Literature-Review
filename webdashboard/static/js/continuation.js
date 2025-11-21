/**
 * Dashboard Continuation Mode Logic
 * 
 * Handles incremental review workflow:
 * - Mode switching (baseline vs continuation)
 * - Base job selection
 * - Gap summary display
 * - Relevance preview and filtering
 * - Job creation and submission
 */

let selectedBaseJob = null;
let uploadedPapers = [];
let gapData = null;
let relevanceScores = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initModeSwitcher();
    initRelevancePreview();
});

/**
 * Initialize mode switcher functionality
 */
function initModeSwitcher() {
    const baselineRadio = document.getElementById('modeBaseline');
    const continuationRadio = document.getElementById('modeContinuation');
    const baseJobSelector = document.getElementById('baseJobSelector');
    
    if (!baselineRadio || !continuationRadio || !baseJobSelector) {
        console.warn('Continuation mode elements not found - feature may not be enabled');
        return;
    }
    
    baselineRadio.addEventListener('change', () => {
        baseJobSelector.style.display = 'none';
        selectedBaseJob = null;
        gapData = null;
        
        // Hide relevance preview
        const relevancePreview = document.getElementById('relevancePreview');
        if (relevancePreview) {
            relevancePreview.style.display = 'none';
        }
    });
    
    continuationRadio.addEventListener('change', () => {
        baseJobSelector.style.display = 'block';
        loadAvailableJobs();
    });
}

/**
 * Load available completed jobs for continuation
 */
async function loadAvailableJobs() {
    try {
        const apiKey = document.getElementById('apiKeyInput')?.value || 'dev-key-change-in-production';
        const response = await fetch('/api/jobs?status=completed', {
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        const jobs = data.jobs || [];
        
        const dropdown = document.getElementById('baseJobDropdown');
        if (!dropdown) return;
        
        dropdown.innerHTML = '<option value="">-- Select a job --</option>';
        
        // Filter for completed jobs only
        const completedJobs = jobs.filter(job => 
            job.status === 'completed' || job.status === 'imported'
        );
        
        if (completedJobs.length === 0) {
            dropdown.innerHTML = '<option value="">No completed jobs available</option>';
            return;
        }
        
        completedJobs.forEach(job => {
            const option = document.createElement('option');
            option.value = job.id;
            const date = new Date(job.created_at).toLocaleDateString();
            const name = job.filename || job.id.substring(0, 12);
            option.textContent = `${name} (${date})`;
            dropdown.appendChild(option);
        });
        
        // Add change listener
        dropdown.removeEventListener('change', handleBaseJobSelection); // Remove old listener
        dropdown.addEventListener('change', handleBaseJobSelection);
        
    } catch (error) {
        console.error('Failed to load jobs:', error);
        alert('Error loading available jobs: ' + error.message);
    }
}

/**
 * Handle base job selection
 */
async function handleBaseJobSelection(event) {
    selectedBaseJob = event.target.value;
    
    const gapSummaryPanel = document.getElementById('gapSummaryPanel');
    if (!gapSummaryPanel) return;
    
    if (!selectedBaseJob) {
        gapSummaryPanel.style.display = 'none';
        gapData = null;
        return;
    }
    
    // Load gaps for selected job
    try {
        const apiKey = document.getElementById('apiKeyInput')?.value || 'dev-key-change-in-production';
        const response = await fetch(`/api/jobs/${selectedBaseJob}/gaps`, {
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        gapData = await response.json();
        displayGapSummary(gapData);
        
        // If we have uploaded papers, trigger relevance preview
        if (uploadedPapers.length > 0) {
            updateRelevancePreview();
        }
        
    } catch (error) {
        console.error('Failed to load gaps:', error);
        alert('Error loading gap data: ' + error.message);
        gapSummaryPanel.style.display = 'none';
    }
}

/**
 * Display gap summary from loaded gap data
 */
function displayGapSummary(gaps) {
    const panel = document.getElementById('gapSummaryPanel');
    if (!panel) return;
    
    // Load gap summary template
    fetch('/static/partials/gap_summary_panel.html')
        .then(response => response.text())
        .then(html => {
            panel.innerHTML = html;
            panel.style.display = 'block';
            
            // Populate data
            const totalGapsElement = document.getElementById('totalGaps');
            const pillarListElement = document.getElementById('gapsByPillar');
            
            if (totalGapsElement) {
                totalGapsElement.textContent = gaps.total_gaps || 0;
            }
            
            if (pillarListElement && gaps.gaps_by_pillar) {
                pillarListElement.innerHTML = '';
                for (const [pillarId, count] of Object.entries(gaps.gaps_by_pillar)) {
                    const li = document.createElement('li');
                    li.innerHTML = `<strong>${pillarId}:</strong> ${count} gaps`;
                    pillarListElement.appendChild(li);
                }
            }
            
            // Add event listener for view details button
            const viewDetailsBtn = document.getElementById('viewGapDetailsBtn');
            if (viewDetailsBtn) {
                viewDetailsBtn.addEventListener('click', () => {
                    viewGapDetails(selectedBaseJob);
                });
            }
        })
        .catch(error => {
            console.error('Failed to load gap summary template:', error);
            // Fallback to inline display
            panel.innerHTML = `
                <div class="gap-summary">
                    <h6>📊 Gap Summary</h6>
                    <div class="alert alert-info">
                        <strong>${gaps.total_gaps || 0}</strong> open gaps found in base review
                    </div>
                </div>
            `;
            panel.style.display = 'block';
        });
}

/**
 * View detailed gap information
 */
function viewGapDetails(jobId) {
    // Open job details modal
    if (typeof showJobDetail === 'function') {
        showJobDetail(jobId);
    } else {
        console.warn('showJobDetail function not found');
        alert('Gap details viewer not available');
    }
}

/**
 * Initialize relevance preview functionality
 */
function initRelevancePreview() {
    const threshold = document.getElementById('relevanceThreshold');
    const thresholdValue = document.getElementById('thresholdValue');
    
    if (!threshold || !thresholdValue) {
        return; // Elements not loaded yet
    }
    
    threshold.addEventListener('input', (e) => {
        thresholdValue.textContent = `${e.target.value}%`;
        updateRelevancePreview();
    });
}

/**
 * Update relevance preview based on current selections
 */
async function updateRelevancePreview() {
    if (!selectedBaseJob || uploadedPapers.length === 0) {
        return;
    }
    
    const threshold = parseInt(document.getElementById('relevanceThreshold')?.value || 50) / 100;
    
    try {
        const apiKey = document.getElementById('apiKeyInput')?.value || 'dev-key-change-in-production';
        const response = await fetch(`/api/jobs/${selectedBaseJob}/relevance`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-API-KEY': apiKey
            },
            body: JSON.stringify({
                papers: uploadedPapers,
                threshold: threshold
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        relevanceScores = result;
        
        // Update UI
        const papersToAnalyze = document.getElementById('papersToAnalyze');
        const papersSkipped = document.getElementById('papersSkipped');
        const estimatedCost = document.getElementById('estimatedCost');
        const estimatedTime = document.getElementById('estimatedTime');
        
        if (papersToAnalyze) papersToAnalyze.textContent = result.papers_above_threshold || 0;
        if (papersSkipped) papersSkipped.textContent = result.papers_below_threshold || 0;
        if (estimatedCost) estimatedCost.textContent = `$${((result.papers_above_threshold || 0) * 0.25).toFixed(2)}`;
        if (estimatedTime) estimatedTime.textContent = `~${Math.ceil((result.papers_above_threshold || 0) * 1.5)} minutes`;
        
        // Display paper list with scores
        displayPaperRelevanceList(result.scores || [], threshold);
        
    } catch (error) {
        console.error('Failed to get relevance scores:', error);
        alert('Error calculating relevance: ' + error.message);
    }
}

/**
 * Display paper list with relevance scores
 */
function displayPaperRelevanceList(scores, threshold) {
    const list = document.getElementById('paperRelevanceList');
    if (!list) return;
    
    list.innerHTML = '';
    
    if (scores.length === 0) {
        list.innerHTML = '<p class="text-muted">No papers to display</p>';
        return;
    }
    
    scores.forEach(score => {
        const div = document.createElement('div');
        const isRelevant = score.relevance_score >= threshold;
        div.className = `paper-item ${isRelevant ? 'relevant' : 'irrelevant'}`;
        
        const icon = isRelevant ? '✓' : '⚠';
        const label = isRelevant ? 'Relevant' : 'Low relevance';
        const percentage = Math.round(score.relevance_score * 100);
        
        div.innerHTML = `
            <span class="icon">${icon}</span>
            <span class="title">${escapeHtml(score.title || 'Untitled')}</span>
            <span class="score">${label} - ${percentage}%</span>
        `;
        
        list.appendChild(div);
    });
}

/**
 * Handle file upload for continuation mode
 */
function handleContinuationFileUpload(files) {
    // Extract paper metadata from uploaded PDFs
    uploadedPapers = Array.from(files).map(file => ({
        filename: file.name,
        title: file.name.replace('.pdf', '').replace(/_/g, ' ').replace(/-/g, ' ')
        // Additional metadata extraction would happen server-side
    }));
    
    const relevancePreview = document.getElementById('relevancePreview');
    if (relevancePreview) {
        relevancePreview.style.display = 'block';
    }
    
    // Trigger relevance preview if base job is selected
    if (selectedBaseJob) {
        updateRelevancePreview();
    }
}

/**
 * Start continuation analysis
 */
async function startContinuationAnalysis() {
    if (!selectedBaseJob) {
        alert('Please select a base job to continue from');
        return;
    }
    
    if (uploadedPapers.length === 0) {
        alert('Please upload at least one paper');
        return;
    }
    
    const threshold = parseInt(document.getElementById('relevanceThreshold')?.value || 50) / 100;
    
    try {
        const apiKey = document.getElementById('apiKeyInput')?.value || 'dev-key-change-in-production';
        const response = await fetch(`/api/jobs/${selectedBaseJob}/continue`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': apiKey
            },
            body: JSON.stringify({
                papers: uploadedPapers,
                relevance_threshold: threshold,
                prefilter_enabled: true
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Show success message
        alert('Continuation job created successfully!');
        
        // Redirect to job status page or refresh jobs list
        if (result.job_id) {
            // If showJobDetail function exists, use it
            if (typeof showJobDetail === 'function') {
                showJobDetail(result.job_id);
            } else {
                window.location.reload();
            }
        }
        
    } catch (error) {
        console.error('Failed to start continuation:', error);
        alert('Error starting incremental analysis: ' + error.message);
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get current analysis mode
 */
function getCurrentAnalysisMode() {
    const continuationRadio = document.getElementById('modeContinuation');
    return continuationRadio && continuationRadio.checked ? 'continuation' : 'baseline';
}

/**
 * Reset continuation mode state
 */
function resetContinuationMode() {
    selectedBaseJob = null;
    uploadedPapers = [];
    gapData = null;
    relevanceScores = null;
    
    const baseJobSelector = document.getElementById('baseJobSelector');
    const relevancePreview = document.getElementById('relevancePreview');
    
    if (baseJobSelector) baseJobSelector.style.display = 'none';
    if (relevancePreview) relevancePreview.style.display = 'none';
}

// Export functions for use in main dashboard
window.continuationMode = {
    handleFileUpload: handleContinuationFileUpload,
    startAnalysis: startContinuationAnalysis,
    getCurrentMode: getCurrentAnalysisMode,
    reset: resetContinuationMode,
    isSelected: () => selectedBaseJob !== null
};
