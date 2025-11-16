# Phase 4: Results Visualization

**Priority**: 🟡 MEDIUM  
**Timeline**: Week 2-3  
**Dependencies**: Phase 1 Complete  
**Status**: 📋 Ready After Phase 1

## Overview

Implement comprehensive results visualization and download capabilities, allowing users to view all 15 pipeline outputs directly in the dashboard without needing to access the file system.

## Success Criteria

- [ ] All 15 output files are accessible via dashboard
- [ ] HTML visualizations (waterfalls, radar, trends) render in browser
- [ ] JSON/Markdown files are viewable with syntax highlighting
- [ ] Results can be downloaded individually or as ZIP archive
- [ ] Results gallery provides easy navigation
- [ ] Comparison views for before/after analysis

## Task Cards

### Task 4.1: Results Retrieval API

**File**: `webdashboard/app.py` (MODIFY)  
**Estimated Time**: 4 hours  
**Complexity**: Medium

#### Description
Create API endpoints to list, retrieve, and download job output files.

#### Implementation Steps

1. **Add results listing endpoint**
   ```python
   from pathlib import Path
   from typing import List, Dict
   import mimetypes
   
   @app.get("/api/jobs/{job_id}/results")
   async def get_job_results(
       job_id: str,
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """
       Get list of all output files for a job
       
       Returns:
           List of output files with metadata
       """
       verify_api_key(api_key)
       
       job_data = load_job(job_id)
       if not job_data:
           raise HTTPException(status_code=404, detail="Job not found")
       
       if job_data.get("status") != "completed":
           raise HTTPException(
               status_code=400,
               detail=f"Job has not completed (status: {job_data['status']})"
           )
       
       # Get output directory
       output_dir = Path(f"workspace/jobs/{job_id}/gap_analysis_output")
       
       if not output_dir.exists():
           return {
               "job_id": job_id,
               "output_count": 0,
               "outputs": []
           }
       
       # Collect all output files
       outputs = []
       for file_path in output_dir.rglob("*"):
           if file_path.is_file():
               # Determine file category
               category = categorize_output_file(file_path.name)
               
               outputs.append({
                   "filename": file_path.name,
                   "path": str(file_path.relative_to(output_dir)),
                   "size": file_path.stat().st_size,
                   "category": category,
                   "mime_type": mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
                   "modified": file_path.stat().st_mtime
               })
       
       # Sort by category then name
       outputs.sort(key=lambda x: (x["category"], x["filename"]))
       
       return {
           "job_id": job_id,
           "output_count": len(outputs),
           "outputs": outputs,
           "output_dir": str(output_dir)
       }
   
   def categorize_output_file(filename: str) -> str:
       """Categorize output file by name pattern"""
       if filename.startswith("waterfall_"):
           return "pillar_waterfalls"
       elif filename.startswith("_OVERALL_"):
           return "visualizations"
       elif filename.endswith(".json"):
           return "data"
       elif filename.endswith(".md"):
           return "reports"
       elif filename.endswith(".html"):
           return "visualizations"
       else:
           return "other"
   ```

2. **Add individual file retrieval endpoint**
   ```python
   @app.get("/api/jobs/{job_id}/results/{file_path:path}")
   async def get_job_result_file(
       job_id: str,
       file_path: str,
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """
       Get a specific output file
       
       Args:
           job_id: Job identifier
           file_path: Relative path to file within output directory
       
       Returns:
           File content
       """
       verify_api_key(api_key)
       
       # Validate job exists and completed
       job_data = load_job(job_id)
       if not job_data:
           raise HTTPException(status_code=404, detail="Job not found")
       
       if job_data.get("status") != "completed":
           raise HTTPException(status_code=400, detail="Job not completed")
       
       # Build full file path (prevent directory traversal)
       output_dir = Path(f"workspace/jobs/{job_id}/gap_analysis_output")
       full_path = (output_dir / file_path).resolve()
       
       # Security check: ensure path is within output directory
       if not str(full_path).startswith(str(output_dir.resolve())):
           raise HTTPException(status_code=403, detail="Access denied")
       
       if not full_path.exists() or not full_path.is_file():
           raise HTTPException(status_code=404, detail="File not found")
       
       # Return file
       return FileResponse(
           path=full_path,
           media_type=mimetypes.guess_type(full_path.name)[0] or "application/octet-stream",
           filename=full_path.name
       )
   ```

3. **Add ZIP download endpoint**
   ```python
   import zipfile
   import io
   from fastapi.responses import StreamingResponse
   
   @app.get("/api/jobs/{job_id}/results/download/all")
   async def download_all_results(
       job_id: str,
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """
       Download all job results as a ZIP file
       
       Returns:
           ZIP archive of all output files
       """
       verify_api_key(api_key)
       
       job_data = load_job(job_id)
       if not job_data:
           raise HTTPException(status_code=404, detail="Job not found")
       
       if job_data.get("status") != "completed":
           raise HTTPException(status_code=400, detail="Job not completed")
       
       output_dir = Path(f"workspace/jobs/{job_id}/gap_analysis_output")
       
       if not output_dir.exists():
           raise HTTPException(status_code=404, detail="No results found")
       
       # Create ZIP in memory
       zip_buffer = io.BytesIO()
       
       with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
           for file_path in output_dir.rglob("*"):
               if file_path.is_file():
                   # Add file to ZIP with relative path
                   arcname = file_path.relative_to(output_dir)
                   zip_file.write(file_path, arcname=arcname)
       
       zip_buffer.seek(0)
       
       return StreamingResponse(
           io.BytesIO(zip_buffer.read()),
           media_type="application/zip",
           headers={
               "Content-Disposition": f"attachment; filename=job_{job_id}_results.zip"
           }
       )
   ```

#### Acceptance Criteria
- [ ] Results listing returns all output files
- [ ] Individual files can be retrieved
- [ ] ZIP download includes all outputs
- [ ] Path traversal attacks are prevented
- [ ] MIME types are correctly identified

---

### Task 4.2: Results Viewer UI

**File**: `webdashboard/templates/index.html` (MODIFY)  
**Estimated Time**: 6 hours  
**Complexity**: High

#### Description
Create interactive UI for browsing and viewing job results.

#### Implementation Steps

1. **Add results viewer modal**
   ```html
   <!-- Results Viewer Modal -->
   <div class="modal fade" id="resultsModal" tabindex="-1">
       <div class="modal-dialog modal-xl">
           <div class="modal-content">
               <div class="modal-header">
                   <h5 class="modal-title">
                       📊 Analysis Results - <span id="resultsJobId"></span>
                   </h5>
                   <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
               </div>
               <div class="modal-body">
                   <div class="row">
                       <!-- Sidebar: File browser -->
                       <div class="col-md-3">
                           <h6>Output Files</h6>
                           <div class="list-group" id="resultsFileList">
                               <div class="text-center text-muted p-3">
                                   Loading...
                               </div>
                           </div>
                           
                           <div class="mt-3">
                               <button class="btn btn-sm btn-outline-primary w-100" onclick="downloadAllResults()">
                                   📦 Download All (ZIP)
                               </button>
                           </div>
                       </div>
                       
                       <!-- Main area: File viewer -->
                       <div class="col-md-9">
                           <div id="resultsViewer">
                               <div class="text-center text-muted p-5">
                                   <h5>Select a file to view</h5>
                                   <p>Choose a file from the list on the left</p>
                               </div>
                           </div>
                       </div>
                   </div>
               </div>
               <div class="modal-footer">
                   <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                       Close
                   </button>
               </div>
           </div>
       </div>
   </div>
   ```

2. **Add file viewer components**
   ```javascript
   async function showJobResults(jobId) {
       // Set modal title
       document.getElementById('resultsJobId').textContent = jobId;
       currentJobId = jobId;
       
       // Fetch results list
       const apiKey = document.getElementById('apiKeyInput').value;
       const response = await fetch(`/api/jobs/${jobId}/results`, {
           headers: { 'X-API-KEY': apiKey }
       });
       
       if (!response.ok) {
           alert('Failed to load results');
           return;
       }
       
       const data = await response.json();
       
       // Render file list grouped by category
       renderFileList(data.outputs);
       
       // Show modal
       const modal = new bootstrap.Modal(document.getElementById('resultsModal'));
       modal.show();
   }
   
   function renderFileList(outputs) {
       const fileList = document.getElementById('resultsFileList');
       fileList.innerHTML = '';
       
       // Group by category
       const grouped = {};
       outputs.forEach(file => {
           if (!grouped[file.category]) {
               grouped[file.category] = [];
           }
           grouped[file.category].push(file);
       });
       
       // Render each category
       const categoryTitles = {
           'pillar_waterfalls': '📊 Pillar Waterfalls',
           'visualizations': '📈 Visualizations',
           'reports': '📄 Reports',
           'data': '💾 Data Files',
           'other': '📦 Other'
       };
       
       for (const [category, files] of Object.entries(grouped)) {
           // Category header
           const header = document.createElement('div');
           header.className = 'list-group-item bg-light fw-bold';
           header.textContent = categoryTitles[category] || category;
           fileList.appendChild(header);
           
           // Files in category
           files.forEach(file => {
               const item = document.createElement('a');
               item.href = '#';
               item.className = 'list-group-item list-group-item-action';
               item.innerHTML = `
                   <div class="d-flex justify-content-between align-items-center">
                       <span class="text-truncate">${file.filename}</span>
                       <span class="badge bg-secondary">${formatFileSize(file.size)}</span>
                   </div>
               `;
               item.onclick = (e) => {
                   e.preventDefault();
                   viewFile(file);
               };
               fileList.appendChild(item);
           });
       }
   }
   
   async function viewFile(file) {
       const viewer = document.getElementById('resultsViewer');
       
       // Show loading
       viewer.innerHTML = '<div class="text-center p-5"><div class="spinner-border"></div></div>';
       
       const apiKey = document.getElementById('apiKeyInput').value;
       const fileUrl = `/api/jobs/${currentJobId}/results/${file.path}`;
       
       try {
           if (file.mime_type === 'text/html' || file.filename.endsWith('.html')) {
               // Render HTML in iframe
               viewer.innerHTML = `
                   <div class="d-flex justify-content-between mb-2">
                       <h6>${file.filename}</h6>
                       <a href="${fileUrl}?X-API-KEY=${apiKey}" download class="btn btn-sm btn-outline-primary">
                           💾 Download
                       </a>
                   </div>
                   <iframe 
                       src="${fileUrl}?X-API-KEY=${apiKey}" 
                       style="width: 100%; height: 600px; border: 1px solid #dee2e6; border-radius: 5px;">
                   </iframe>
               `;
           } else if (file.mime_type === 'application/json' || file.filename.endsWith('.json')) {
               // Fetch and pretty-print JSON
               const response = await fetch(fileUrl, {
                   headers: { 'X-API-KEY': apiKey }
               });
               const jsonData = await response.json();
               
               viewer.innerHTML = `
                   <div class="d-flex justify-content-between mb-2">
                       <h6>${file.filename}</h6>
                       <a href="${fileUrl}?X-API-KEY=${apiKey}" download class="btn btn-sm btn-outline-primary">
                           💾 Download
                       </a>
                   </div>
                   <pre class="bg-dark text-light p-3" style="max-height: 600px; overflow-y: auto; border-radius: 5px;"><code>${JSON.stringify(jsonData, null, 2)}</code></pre>
               `;
           } else if (file.mime_type?.startsWith('text/') || file.filename.endsWith('.md')) {
               // Fetch and display text/markdown
               const response = await fetch(fileUrl, {
                   headers: { 'X-API-KEY': apiKey }
               });
               const textData = await response.text();
               
               viewer.innerHTML = `
                   <div class="d-flex justify-content-between mb-2">
                       <h6>${file.filename}</h6>
                       <a href="${fileUrl}?X-API-KEY=${apiKey}" download class="btn btn-sm btn-outline-primary">
                           💾 Download
                       </a>
                   </div>
                   <pre class="bg-light p-3" style="max-height: 600px; overflow-y: auto; border-radius: 5px;"><code>${escapeHtml(textData)}</code></pre>
               `;
           } else {
               // Download-only for binary files
               viewer.innerHTML = `
                   <div class="text-center p-5">
                       <h5>${file.filename}</h5>
                       <p class="text-muted">Preview not available for this file type</p>
                       <a href="${fileUrl}?X-API-KEY=${apiKey}" download class="btn btn-primary">
                           💾 Download File
                       </a>
                   </div>
               `;
           }
       } catch (error) {
           viewer.innerHTML = `
               <div class="alert alert-danger">
                   Failed to load file: ${error.message}
               </div>
           `;
       }
   }
   
   function formatFileSize(bytes) {
       if (bytes < 1024) return bytes + ' B';
       if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
       return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
   }
   
   function escapeHtml(text) {
       const div = document.createElement('div');
       div.textContent = text;
       return div.innerHTML;
   }
   
   async function downloadAllResults() {
       const apiKey = document.getElementById('apiKeyInput').value;
       window.open(`/api/jobs/${currentJobId}/results/download/all?X-API-KEY=${apiKey}`, '_blank');
   }
   ```

3. **Add "View Results" button to jobs table**
   ```javascript
   // Modify updateJobsTable to add results button
   function updateJobsTable() {
       // ... existing code ...
       
       tbody.innerHTML = jobs.map(job => `
           <tr class="job-row">
               <td><code>${job.id.substring(0, 8)}</code></td>
               <td>${job.filename || 'Multiple files'}</td>
               <td>${getStatusBadge(job.status)}</td>
               <td>${formatDateTime(job.created_at)}</td>
               <td>${calculateDuration(job.started_at || job.created_at, job.completed_at)}</td>
               <td>
                   <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); showJobDetail('${job.id}')">
                       📋 Details
                   </button>
                   ${job.status === 'completed' ? `
                       <button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation(); showJobResults('${job.id}')">
                           📊 Results
                       </button>
                   ` : ''}
               </td>
           </tr>
       `).join('');
   }
   ```

#### Acceptance Criteria
- [ ] File browser shows categorized output files
- [ ] HTML files render in iframe
- [ ] JSON files are pretty-printed
- [ ] Markdown/text files are displayed
- [ ] Download buttons work for all files
- [ ] ZIP download works
- [ ] UI is responsive and user-friendly

---

### Task 4.3: Results Comparison View

**File**: `webdashboard/templates/index.html` (MODIFY)  
**Estimated Time**: 5 hours  
**Complexity**: High

#### Description
Add ability to compare results from multiple job runs side-by-side.

#### Implementation Steps

1. **Add comparison selection UI**
   ```html
   <!-- In results modal -->
   <div class="modal-header">
       <div class="d-flex align-items-center">
           <h5 class="modal-title mb-0">📊 Analysis Results</h5>
           <button 
               class="btn btn-sm btn-outline-secondary ms-3" 
               onclick="toggleComparisonMode()">
               🔀 Compare with...
           </button>
       </div>
       <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
   </div>
   
   <!-- Comparison selector (hidden by default) -->
   <div id="comparisonSelector" style="display: none;" class="alert alert-info m-3">
       <strong>Select job to compare with:</strong>
       <select class="form-select mt-2" id="comparisonJobSelect">
           <option value="">-- Select a job --</option>
       </select>
       <button class="btn btn-primary btn-sm mt-2" onclick="loadComparison()">
           Compare
       </button>
       <button class="btn btn-secondary btn-sm mt-2" onclick="cancelComparison()">
           Cancel
       </button>
   </div>
   ```

2. **Add comparison view**
   ```javascript
   let comparisonMode = false;
   let comparisonJobId = null;
   
   function toggleComparisonMode() {
       comparisonMode = !comparisonMode;
       
       if (comparisonMode) {
           // Show comparison selector
           document.getElementById('comparisonSelector').style.display = 'block';
           
           // Populate with completed jobs (except current)
           populateComparisonSelector();
       } else {
           // Hide comparison selector
           document.getElementById('comparisonSelector').style.display = 'none';
       }
   }
   
   async function populateComparisonSelector() {
       const apiKey = document.getElementById('apiKeyInput').value;
       const response = await fetch('/api/jobs', {
           headers: { 'X-API-KEY': apiKey }
       });
       
       const data = await response.json();
       const completedJobs = data.jobs.filter(
           j => j.status === 'completed' && j.id !== currentJobId
       );
       
       const select = document.getElementById('comparisonJobSelect');
       select.innerHTML = '<option value="">-- Select a job --</option>' +
           completedJobs.map(job => `
               <option value="${job.id}">
                   ${job.id.substring(0, 8)} - ${formatDateTime(job.created_at)}
               </option>
           `).join('');
   }
   
   async function loadComparison() {
       const selectedJobId = document.getElementById('comparisonJobSelect').value;
       
       if (!selectedJobId) {
           alert('Please select a job to compare with');
           return;
       }
       
       comparisonJobId = selectedJobId;
       
       // Switch to split view
       renderSplitView();
       
       // Load results for both jobs
       await loadSplitViewResults(currentJobId, comparisonJobId);
   }
   
   function renderSplitView() {
       const modalBody = document.querySelector('#resultsModal .modal-body');
       modalBody.innerHTML = `
           <div class="row">
               <!-- Left: Current job -->
               <div class="col-md-6 border-end">
                   <h6 class="text-center">
                       Current Job: ${currentJobId.substring(0, 8)}
                   </h6>
                   <div id="leftResults"></div>
               </div>
               
               <!-- Right: Comparison job -->
               <div class="col-md-6">
                   <h6 class="text-center">
                       Comparison: ${comparisonJobId.substring(0, 8)}
                   </h6>
                   <div id="rightResults"></div>
               </div>
           </div>
           
           <div class="text-center mt-3">
               <button class="btn btn-secondary" onclick="exitComparisonMode()">
                   Exit Comparison Mode
               </button>
           </div>
       `;
   }
   
   async function loadSplitViewResults(leftJobId, rightJobId) {
       const apiKey = document.getElementById('apiKeyInput').value;
       
       // Load results for both jobs
       const [leftResponse, rightResponse] = await Promise.all([
           fetch(`/api/jobs/${leftJobId}/results`, {
               headers: { 'X-API-KEY': apiKey }
           }),
           fetch(`/api/jobs/${rightJobId}/results`, {
               headers: { 'X-API-KEY': apiKey }
           })
       ]);
       
       const leftData = await leftResponse.json();
       const rightData = await rightResponse.json();
       
       // Focus on gap_analysis_report.json for comparison
       const leftReport = leftData.outputs.find(f => f.filename === 'gap_analysis_report.json');
       const rightReport = rightData.outputs.find(f => f.filename === 'gap_analysis_report.json');
       
       if (leftReport && rightReport) {
           await renderComparisonReport(leftJobId, rightJobId, leftReport, rightReport);
       } else {
           document.getElementById('leftResults').innerHTML = '<p class="text-muted">No comparison data available</p>';
           document.getElementById('rightResults').innerHTML = '<p class="text-muted">No comparison data available</p>';
       }
   }
   
   async function renderComparisonReport(leftJobId, rightJobId, leftReport, rightReport) {
       const apiKey = document.getElementById('apiKeyInput').value;
       
       // Fetch both reports
       const [leftJson, rightJson] = await Promise.all([
           fetch(`/api/jobs/${leftJobId}/results/${leftReport.path}`, {
               headers: { 'X-API-KEY': apiKey }
           }).then(r => r.json()),
           fetch(`/api/jobs/${rightJobId}/results/${rightReport.path}`, {
               headers: { 'X-API-KEY': apiKey }
           }).then(r => r.json())
       ]);
       
       // Extract completeness scores
       const leftScores = extractCompletenessScores(leftJson);
       const rightScores = extractCompletenessScores(rightJson);
       
       // Render comparison table
       const comparisonHtml = `
           <table class="table table-sm">
               <thead>
                   <tr>
                       <th>Pillar</th>
                       <th>Completeness</th>
                       <th>Change</th>
                   </tr>
               </thead>
               <tbody>
                   ${Object.keys(leftScores).map(pillar => {
                       const leftScore = leftScores[pillar] || 0;
                       const rightScore = rightScores[pillar] || 0;
                       const diff = rightScore - leftScore;
                       const diffClass = diff > 0 ? 'text-success' : diff < 0 ? 'text-danger' : 'text-muted';
                       
                       return `
                           <tr>
                               <td>${pillar}</td>
                               <td>${rightScore.toFixed(1)}%</td>
                               <td class="${diffClass}">
                                   ${diff > 0 ? '+' : ''}${diff.toFixed(1)}%
                               </td>
                           </tr>
                       `;
                   }).join('')}
               </tbody>
           </table>
       `;
       
       document.getElementById('leftResults').innerHTML = `
           <h6>Completeness Scores</h6>
           <table class="table table-sm">
               <tbody>
                   ${Object.entries(leftScores).map(([pillar, score]) => `
                       <tr>
                           <td>${pillar}</td>
                           <td>${score.toFixed(1)}%</td>
                       </tr>
                   `).join('')}
               </tbody>
           </table>
       `;
       
       document.getElementById('rightResults').innerHTML = comparisonHtml;
   }
   
   function extractCompletenessScores(reportJson) {
       const scores = {};
       // Assuming report has pillar_results structure
       if (reportJson.pillar_results) {
           for (const [pillar, data] of Object.entries(reportJson.pillar_results)) {
               scores[pillar] = data.completeness || 0;
           }
       }
       return scores;
   }
   
   function exitComparisonMode() {
       comparisonMode = false;
       comparisonJobId = null;
       
       // Reload normal view
       showJobResults(currentJobId);
   }
   ```

#### Acceptance Criteria
- [ ] Users can select a job to compare with
- [ ] Split view shows both jobs side-by-side
- [ ] Completeness scores are compared
- [ ] Differences are highlighted
- [ ] Comparison mode can be exited
- [ ] UI remains responsive

---

### Task 4.4: Results Summary Cards

**File**: `webdashboard/templates/index.html` (MODIFY)  
**Estimated Time**: 3 hours  
**Complexity**: Low

#### Description
Add summary cards showing key metrics from completed jobs.

#### Implementation Steps

1. **Add summary cards to results modal**
   ```javascript
   async function showJobResults(jobId) {
       // ... existing code ...
       
       // Fetch gap_analysis_report.json for summary
       const apiKey = document.getElementById('apiKeyInput').value;
       const resultsResponse = await fetch(`/api/jobs/${jobId}/results`, {
           headers: { 'X-API-KEY': apiKey }
       });
       
       const resultsData = await resultsResponse.json();
       const reportFile = resultsData.outputs.find(f => f.filename === 'gap_analysis_report.json');
       
       if (reportFile) {
           const reportResponse = await fetch(`/api/jobs/${jobId}/results/${reportFile.path}`, {
               headers: { 'X-API-KEY': apiKey }
           });
           const reportJson = await reportResponse.json();
           
           // Render summary cards
           renderSummaryCards(reportJson);
       }
       
       // ... rest of existing code ...
   }
   
   function renderSummaryCards(reportData) {
       const summaryContainer = document.createElement('div');
       summaryContainer.className = 'row mb-4';
       summaryContainer.id = 'summaryCards';
       
       // Calculate metrics
       const avgCompleteness = calculateAverageCompleteness(reportData);
       const totalGaps = countTotalGaps(reportData);
       const topRecommendations = getTopRecommendations(reportData);
       
       summaryContainer.innerHTML = `
           <div class="col-md-4">
               <div class="card bg-primary text-white">
                   <div class="card-body text-center">
                       <h6 class="card-title">Average Completeness</h6>
                       <h2 class="display-4">${avgCompleteness.toFixed(1)}%</h2>
                   </div>
               </div>
           </div>
           <div class="col-md-4">
               <div class="card bg-warning text-dark">
                   <div class="card-body text-center">
                       <h6 class="card-title">Total Gaps Identified</h6>
                       <h2 class="display-4">${totalGaps}</h2>
                   </div>
               </div>
           </div>
           <div class="col-md-4">
               <div class="card bg-success text-white">
                   <div class="card-body text-center">
                       <h6 class="card-title">Recommendations</h6>
                       <h2 class="display-4">${topRecommendations}</h2>
                   </div>
               </div>
           </div>
       `;
       
       // Insert at top of modal body
       const modalBody = document.querySelector('#resultsModal .modal-body');
       modalBody.insertBefore(summaryContainer, modalBody.firstChild);
   }
   
   function calculateAverageCompleteness(reportData) {
       if (!reportData.pillar_results) return 0;
       
       const scores = Object.values(reportData.pillar_results).map(p => p.completeness || 0);
       return scores.reduce((a, b) => a + b, 0) / scores.length;
   }
   
   function countTotalGaps(reportData) {
       if (!reportData.pillar_results) return 0;
       
       return Object.values(reportData.pillar_results).reduce((total, pillar) => {
           return total + (pillar.gaps_count || 0);
       }, 0);
   }
   
   function getTopRecommendations(reportData) {
       if (!reportData.recommendations) return 0;
       return reportData.recommendations.length;
   }
   ```

#### Acceptance Criteria
- [ ] Summary cards show key metrics
- [ ] Metrics are calculated from gap_analysis_report.json
- [ ] Cards are visually distinct and informative
- [ ] Cards appear at top of results modal

---

### Task 4.5: Test Results Visualization

**File**: `tests/integration/test_results_visualization.py` (NEW)  
**Estimated Time**: 3 hours  
**Complexity**: Medium

#### Implementation Steps

```python
def test_results_listing():
    """Test results listing endpoint"""
    job_id = create_completed_test_job()
    
    response = client.get(
        f"/api/jobs/{job_id}/results",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["output_count"] > 0
    assert len(data["outputs"]) > 0
    assert all("filename" in f for f in data["outputs"])

def test_file_retrieval():
    """Test retrieving individual result file"""
    job_id = create_completed_test_job()
    
    # Get file list
    results = get_job_results(job_id)
    test_file = results["outputs"][0]
    
    # Retrieve file
    response = client.get(
        f"/api/jobs/{job_id}/results/{test_file['path']}",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == test_file["mime_type"]

def test_zip_download():
    """Test ZIP download of all results"""
    job_id = create_completed_test_job()
    
    response = client.get(
        f"/api/jobs/{job_id}/results/download/all",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    
    # Verify ZIP is valid
    import zipfile
    import io
    
    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data) as zf:
        assert len(zf.namelist()) > 0
```

#### Acceptance Criteria
- [ ] All tests pass
- [ ] Results API works correctly
- [ ] File download works
- [ ] ZIP creation works

---

## Phase 4 Deliverables

- [ ] Modified `webdashboard/app.py` - Results endpoints
- [ ] Modified `webdashboard/templates/index.html` - Results viewer UI
- [ ] `tests/integration/test_results_visualization.py` - Tests
- [ ] Documentation of results visualization features

## Success Metrics

1. **Accessibility**: All 15 output files viewable via dashboard
2. **Usability**: Users can navigate results intuitively
3. **Performance**: Large files load within 5 seconds
4. **Functionality**: Comparison view provides useful insights

## Next Phase

After Phase 4 completion, proceed to **Phase 5: Interactive Prompts** for full 1:1 parity with terminal experience.
