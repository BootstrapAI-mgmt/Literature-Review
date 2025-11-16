# Phase 2: Input Handling

**Priority**: 🟠 HIGH  
**Timeline**: Week 1-2  
**Dependencies**: Phase 1 Complete  
**Status**: 📋 Ready After Phase 1

## Overview

Enable the dashboard to accept proper input formats matching the terminal orchestrator's expectations: batch uploads of multiple PDFs, directory-based processing, and comprehensive job configuration before execution.

## Success Criteria

- [ ] Dashboard accepts multiple PDF uploads in a single job
- [ ] Research database is built automatically from uploaded files
- [ ] UI provides pillar selection (individual or ALL)
- [ ] UI provides run mode selection (ONCE vs DEEP_LOOP)
- [ ] Configuration is validated before job execution
- [ ] Jobs can be saved as drafts before execution

## Task Cards

### Task 2.1: Implement Batch File Upload

**File**: `webdashboard/app.py` (MODIFY)  
**Estimated Time**: 4 hours  
**Complexity**: Medium

#### Description
Add endpoint and UI for uploading multiple PDF files as a batch for a single analysis job.

#### Implementation Steps

1. **Create batch upload API endpoint**
   ```python
   from typing import List
   from fastapi import File, UploadFile
   
   @app.post("/api/upload/batch")
   async def upload_batch(
       files: List[UploadFile] = File(...),
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """
       Upload multiple PDF files for a single analysis job
       
       Args:
           files: List of PDF files to upload
       
       Returns:
           Job ID and file count
       """
       verify_api_key(api_key)
       
       # Validate all files are PDFs
       for file in files:
           if not file.filename.endswith('.pdf'):
               raise HTTPException(
                   status_code=400,
                   detail=f"Invalid file type: {file.filename}. Only PDFs allowed."
               )
       
       # Generate job ID
       job_id = str(uuid.uuid4())
       
       # Create job directory
       job_dir = UPLOADS_DIR / job_id
       job_dir.mkdir(exist_ok=True)
       
       # Save all uploaded files
       uploaded_files = []
       for file in files:
           # Sanitize filename
           safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
           target_path = job_dir / safe_filename
           
           try:
               with open(target_path, 'wb') as out:
                   shutil.copyfileobj(file.file, out)
               uploaded_files.append({
                   "original_name": file.filename,
                   "path": str(target_path),
                   "size": target_path.stat().st_size
               })
           except Exception as e:
               # Cleanup on error
               shutil.rmtree(job_dir, ignore_errors=True)
               raise HTTPException(
                   status_code=500,
                   detail=f"Failed to save {file.filename}: {str(e)}"
               )
       
       # Create job record
       job_data = {
           "id": job_id,
           "status": "draft",  # Not queued until configured
           "files": uploaded_files,
           "file_count": len(uploaded_files),
           "created_at": datetime.utcnow().isoformat(),
           "config": None  # Will be set when user configures job
       }
       
       save_job(job_id, job_data)
       
       # Broadcast update
       await manager.broadcast({
           "type": "job_created",
           "job": job_data
       })
       
       return {
           "job_id": job_id,
           "status": "draft",
           "file_count": len(uploaded_files),
           "files": uploaded_files
       }
   ```

2. **Update single upload endpoint to support draft status**
   ```python
   @app.post("/api/upload")
   async def upload_file(
       file: UploadFile = File(...),
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """Upload a single PDF file (legacy endpoint)"""
       # Redirect to batch upload with single file
       return await upload_batch(files=[file], api_key=api_key)
   ```

#### Acceptance Criteria
- [ ] `/api/upload/batch` endpoint accepts multiple files
- [ ] All files are saved to job-specific directory
- [ ] Job status is "draft" until configured
- [ ] File metadata is stored in job record
- [ ] Invalid file types are rejected
- [ ] Errors cleanup uploaded files

#### Testing
```python
def test_batch_upload():
    with open("test1.pdf", "rb") as f1, open("test2.pdf", "rb") as f2:
        response = client.post(
            "/api/upload/batch",
            files=[
                ("files", ("test1.pdf", f1, "application/pdf")),
                ("files", ("test2.pdf", f2, "application/pdf"))
            ],
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["file_count"] == 2
    assert data["status"] == "draft"
```

---

### Task 2.2: Build Research Database from Uploaded Files

**File**: `webdashboard/database_builder.py` (NEW)  
**Estimated Time**: 6 hours  
**Complexity**: High

#### Description
Create a service that extracts metadata from uploaded PDFs and builds a research database CSV matching the format expected by the orchestrator.

#### Implementation Steps

1. **Create database builder class**
   ```python
   import PyPDF2
   import csv
   from pathlib import Path
   from typing import List, Dict
   import re
   from datetime import datetime
   
   class ResearchDatabaseBuilder:
       """Builds research database CSV from uploaded PDFs"""
       
       def __init__(self, job_id: str, pdf_files: List[Path]):
           self.job_id = job_id
           self.pdf_files = pdf_files
           self.output_dir = Path(f"workspace/jobs/{job_id}")
           self.output_dir.mkdir(parents=True, exist_ok=True)
       
       def build_database(self) -> Path:
           """
           Extract metadata from PDFs and create research database CSV
           
           Returns:
               Path to created CSV file
           """
           records = []
           
           for pdf_path in self.pdf_files:
               try:
                   metadata = self._extract_pdf_metadata(pdf_path)
                   records.append(metadata)
               except Exception as e:
                   logger.error(f"Failed to process {pdf_path}: {e}")
                   # Add placeholder record
                   records.append(self._create_placeholder_record(pdf_path))
           
           # Write to CSV
           csv_path = self.output_dir / "research_database.csv"
           self._write_csv(records, csv_path)
           
           return csv_path
   ```

2. **Implement PDF metadata extraction**
   ```python
   def _extract_pdf_metadata(self, pdf_path: Path) -> Dict:
       """Extract metadata from a single PDF"""
       with open(pdf_path, 'rb') as f:
           reader = PyPDF2.PdfReader(f)
           
           # Extract PDF metadata
           info = reader.metadata or {}
           
           # Extract first page text for title extraction
           first_page_text = ""
           if len(reader.pages) > 0:
               first_page_text = reader.pages[0].extract_text()
           
           # Try to extract title
           title = (
               info.get('/Title') or
               self._extract_title_from_text(first_page_text) or
               pdf_path.stem
           )
           
           # Try to extract authors
           authors = (
               info.get('/Author') or
               self._extract_authors_from_text(first_page_text) or
               "Unknown"
           )
           
           # Try to extract year
           year = (
               self._extract_year_from_metadata(info) or
               self._extract_year_from_text(first_page_text) or
               datetime.now().year
           )
           
           return {
               "Title": title,
               "Authors": authors,
               "Year": year,
               "File": str(pdf_path),
               "Abstract": self._extract_abstract(first_page_text),
               "Requirement(s)": "[]",  # Empty initially, filled by Judge
               "Score": "",
               "Keywords": self._extract_keywords(first_page_text)
           }
   ```

3. **Add helper extraction methods**
   ```python
   def _extract_title_from_text(self, text: str) -> str:
       """Attempt to extract title from PDF text"""
       if not text:
           return ""
       
       # Get first few lines
       lines = [line.strip() for line in text.split('\n') if line.strip()]
       
       # Title is usually in first 5 lines, longest line
       candidates = lines[:5]
       if candidates:
           return max(candidates, key=len)[:200]  # Limit length
       
       return ""
   
   def _extract_authors_from_text(self, text: str) -> str:
       """Attempt to extract authors from PDF text"""
       # Look for common author patterns
       # This is heuristic and may need improvement
       lines = text.split('\n')[:10]  # Check first 10 lines
       
       for line in lines:
           # Look for lines with names (capital letters followed by lowercase)
           if re.match(r'^[A-Z][a-z]+\s+[A-Z]', line):
               return line.strip()[:200]
       
       return "Unknown"
   
   def _extract_year_from_text(self, text: str) -> Optional[int]:
       """Attempt to extract publication year from text"""
       # Look for 4-digit years between 1900-2099
       matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
       
       if matches:
           # Return most recent plausible year
           years = [int(y) for y in matches if 1900 <= int(y) <= datetime.now().year]
           if years:
               return max(years)
       
       return None
   
   def _extract_abstract(self, text: str) -> str:
       """Attempt to extract abstract"""
       # Look for "Abstract" section
       abstract_match = re.search(
           r'abstract[:\s]+(.*?)(?:\n\n|introduction|keywords)',
           text,
           re.IGNORECASE | re.DOTALL
       )
       
       if abstract_match:
           return abstract_match.group(1).strip()[:500]  # Limit length
       
       return ""
   
   def _extract_keywords(self, text: str) -> str:
       """Attempt to extract keywords"""
       keywords_match = re.search(
           r'keywords[:\s]+(.*?)(?:\n\n|\d+\s+introduction)',
           text,
           re.IGNORECASE | re.DOTALL
       )
       
       if keywords_match:
           return keywords_match.group(1).strip()[:200]
       
       return ""
   ```

4. **Write CSV output**
   ```python
   def _write_csv(self, records: List[Dict], output_path: Path):
       """Write records to CSV file"""
       if not records:
           raise ValueError("No records to write")
       
       fieldnames = [
           "Title", "Authors", "Year", "File", "Abstract",
           "Requirement(s)", "Score", "Keywords"
       ]
       
       with open(output_path, 'w', newline='', encoding='utf-8') as f:
           writer = csv.DictWriter(f, fieldnames=fieldnames)
           writer.writeheader()
           writer.writerows(records)
       
       logger.info(f"Created research database: {output_path} ({len(records)} records)")
   ```

#### Acceptance Criteria
- [ ] CSV database is created from uploaded PDFs
- [ ] Metadata extraction works for common PDF formats
- [ ] CSV format matches orchestrator expectations
- [ ] Errors in individual PDFs don't fail entire build
- [ ] Database is saved to job-specific directory

#### Testing
```python
def test_database_builder():
    pdf_files = [
        Path("tests/fixtures/paper1.pdf"),
        Path("tests/fixtures/paper2.pdf")
    ]
    
    builder = ResearchDatabaseBuilder("test-job", pdf_files)
    csv_path = builder.build_database()
    
    assert csv_path.exists()
    
    # Verify CSV content
    import pandas as pd
    df = pd.read_csv(csv_path)
    assert len(df) == 2
    assert "Title" in df.columns
    assert "Authors" in df.columns
```

---

### Task 2.3: Create Job Configuration UI

**File**: `webdashboard/templates/index.html` (MODIFY)  
**Estimated Time**: 5 hours  
**Complexity**: Medium

#### Description
Add UI components for configuring job parameters: pillar selection, run mode, and execution triggers.

#### Implementation Steps

1. **Add batch upload UI**
   ```html
   <!-- Replace single file input with batch upload -->
   <div class="card">
       <div class="card-header bg-primary text-white">
           <h5 class="mb-0">📤 Upload Research Papers</h5>
       </div>
       <div class="card-body">
           <form id="batchUploadForm">
               <div class="mb-3">
                   <label for="batchFileInput" class="form-label">
                       Select PDF files (multiple allowed)
                   </label>
                   <input 
                       class="form-control" 
                       type="file" 
                       id="batchFileInput" 
                       accept=".pdf" 
                       multiple
                       required>
                   <div class="form-text">
                       Select one or more research papers (PDF format only)
                   </div>
               </div>
               
               <div class="mb-3">
                   <label for="apiKeyInput" class="form-label">API Key</label>
                   <input 
                       type="password" 
                       class="form-control" 
                       id="apiKeyInput" 
                       value="dev-key-change-in-production">
               </div>
               
               <button type="submit" class="btn btn-primary">
                   📤 Upload Papers
               </button>
           </form>
           
           <div class="progress mt-3" id="uploadProgress" style="display: none;">
               <div class="progress-bar progress-bar-striped progress-bar-animated" 
                    role="progressbar" style="width: 100%">
                   Uploading...
               </div>
           </div>
       </div>
   </div>
   ```

2. **Add job configuration modal**
   ```html
   <!-- Job Configuration Modal -->
   <div class="modal fade" id="configModal" tabindex="-1">
       <div class="modal-dialog modal-lg">
           <div class="modal-content">
               <div class="modal-header">
                   <h5 class="modal-title">Configure Analysis</h5>
                   <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
               </div>
               <div class="modal-body">
                   <form id="configForm">
                       <!-- Job Info -->
                       <div class="alert alert-info">
                           <strong>Job ID:</strong> <span id="configJobId"></span><br>
                           <strong>Files:</strong> <span id="configFileCount"></span> PDFs uploaded
                       </div>
                       
                       <!-- Pillar Selection -->
                       <div class="mb-4">
                           <h6>Select Pillars to Analyze</h6>
                           <div class="form-check">
                               <input 
                                   class="form-check-input pillar-checkbox" 
                                   type="checkbox" 
                                   value="ALL" 
                                   id="pillar_all"
                                   onchange="toggleAllPillars(this)">
                               <label class="form-check-label" for="pillar_all">
                                   <strong>All Pillars</strong> (Comprehensive Analysis)
                               </label>
                           </div>
                           <hr>
                           <div id="pillarCheckboxes">
                               <!-- Populated dynamically from pillar_definitions.json -->
                           </div>
                       </div>
                       
                       <!-- Run Mode Selection -->
                       <div class="mb-4">
                           <h6>Analysis Mode</h6>
                           <div class="form-check">
                               <input 
                                   class="form-check-input" 
                                   type="radio" 
                                   name="runMode" 
                                   value="ONCE" 
                                   id="mode_once"
                                   checked>
                               <label class="form-check-label" for="mode_once">
                                   <strong>Single Pass</strong> - Quick analysis (faster)
                               </label>
                               <div class="form-text ms-4">
                                   Runs analysis once without iterative refinement.
                                   Recommended for initial exploration.
                               </div>
                           </div>
                           <div class="form-check mt-2">
                               <input 
                                   class="form-check-input" 
                                   type="radio" 
                                   name="runMode" 
                                   value="DEEP_LOOP" 
                                   id="mode_deep">
                               <label class="form-check-label" for="mode_deep">
                                   <strong>Deep Iterative Loop</strong> - Comprehensive (slower)
                               </label>
                               <div class="form-text ms-4">
                                   Runs Deep Reviewer iteratively until convergence (±5%).
                                   Provides most thorough gap analysis.
                               </div>
                           </div>
                       </div>
                       
                       <!-- Advanced Options (Optional) -->
                       <div class="mb-3">
                           <button 
                               class="btn btn-sm btn-outline-secondary" 
                               type="button" 
                               data-bs-toggle="collapse" 
                               data-bs-target="#advancedOptions">
                               ⚙️ Advanced Options
                           </button>
                           <div class="collapse mt-2" id="advancedOptions">
                               <div class="card card-body">
                                   <div class="mb-2">
                                       <label class="form-label">Convergence Threshold (%)</label>
                                       <input 
                                           type="number" 
                                           class="form-control" 
                                           id="convergenceThreshold"
                                           value="5.0"
                                           min="0.1"
                                           max="20"
                                           step="0.1">
                                       <div class="form-text">
                                           Stop iterating when changes are below this threshold
                                       </div>
                                   </div>
                               </div>
                           </div>
                       </div>
                   </form>
               </div>
               <div class="modal-footer">
                   <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                       Cancel
                   </button>
                   <button type="button" class="btn btn-success" onclick="saveConfigAndStart()">
                       🚀 Save & Start Analysis
                   </button>
               </div>
           </div>
       </div>
   </div>
   ```

3. **Add JavaScript for configuration**
   ```javascript
   // Load pillar definitions and populate checkboxes
   async function loadPillarDefinitions() {
       try {
           const response = await fetch('/static/pillar_definitions.json');
           const definitions = await response.json();
           
           const container = document.getElementById('pillarCheckboxes');
           container.innerHTML = '';
           
           // Filter out metadata sections
           const metadata = ['Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'];
           
           for (const [key, value] of Object.entries(definitions)) {
               if (metadata.includes(key)) continue;
               
               const checkbox = document.createElement('div');
               checkbox.className = 'form-check';
               checkbox.innerHTML = `
                   <input 
                       class="form-check-input pillar-checkbox-individual" 
                       type="checkbox" 
                       value="${key}" 
                       id="pillar_${key}">
                   <label class="form-check-label" for="pillar_${key}">
                       ${key.replace(/_/g, ' ')}
                   </label>
               `;
               container.appendChild(checkbox);
           }
       } catch (error) {
           console.error('Failed to load pillar definitions:', error);
       }
   }
   
   // Toggle all pillars
   function toggleAllPillars(checkbox) {
       const individual = document.querySelectorAll('.pillar-checkbox-individual');
       individual.forEach(cb => {
           cb.checked = checkbox.checked;
           cb.disabled = checkbox.checked;
       });
   }
   
   // Handle batch upload
   document.getElementById('batchUploadForm').addEventListener('submit', async (e) => {
       e.preventDefault();
       
       const fileInput = document.getElementById('batchFileInput');
       const files = fileInput.files;
       
       if (files.length === 0) {
           alert('Please select at least one PDF file');
           return;
       }
       
       document.getElementById('uploadProgress').style.display = 'block';
       
       try {
           const formData = new FormData();
           for (let file of files) {
               formData.append('files', file);
           }
           
           const apiKey = document.getElementById('apiKeyInput').value;
           const response = await fetch('/api/upload/batch', {
               method: 'POST',
               headers: { 'X-API-KEY': apiKey },
               body: formData
           });
           
           if (!response.ok) throw new Error('Upload failed');
           
           const result = await response.json();
           
           // Show configuration modal
           currentJobId = result.job_id;
           document.getElementById('configJobId').textContent = result.job_id;
           document.getElementById('configFileCount').textContent = result.file_count;
           
           const modal = new bootstrap.Modal(document.getElementById('configModal'));
           modal.show();
           
           // Reset form
           fileInput.value = '';
           
       } catch (error) {
           alert('Upload failed: ' + error.message);
       } finally {
           document.getElementById('uploadProgress').style.display = 'none';
       }
   });
   
   // Save configuration and start job
   async function saveConfigAndStart() {
       const apiKey = document.getElementById('apiKeyInput').value;
       
       // Collect selected pillars
       let pillar_selections = [];
       if (document.getElementById('pillar_all').checked) {
           pillar_selections = ['ALL'];
       } else {
           document.querySelectorAll('.pillar-checkbox-individual:checked').forEach(cb => {
               pillar_selections.push(cb.value);
           });
       }
       
       if (pillar_selections.length === 0) {
           alert('Please select at least one pillar');
           return;
       }
       
       // Get run mode
       const run_mode = document.querySelector('input[name="runMode"]:checked').value;
       
       // Get advanced options
       const convergence_threshold = parseFloat(
           document.getElementById('convergenceThreshold').value
       );
       
       const config = {
           pillar_selections,
           run_mode,
           convergence_threshold
       };
       
       try {
           // Save configuration
           const configResponse = await fetch(`/api/jobs/${currentJobId}/configure`, {
               method: 'POST',
               headers: {
                   'Content-Type': 'application/json',
                   'X-API-KEY': apiKey
               },
               body: JSON.stringify(config)
           });
           
           if (!configResponse.ok) throw new Error('Configuration failed');
           
           // Start job execution
           const startResponse = await fetch(`/api/jobs/${currentJobId}/start`, {
               method: 'POST',
               headers: { 'X-API-KEY': apiKey }
           });
           
           if (!startResponse.ok) throw new Error('Failed to start job');
           
           // Close modal
           bootstrap.Modal.getInstance(document.getElementById('configModal')).hide();
           
           alert(`Job ${currentJobId} started successfully!`);
           
       } catch (error) {
           alert('Error: ' + error.message);
       }
   }
   
   // Initialize on page load
   loadPillarDefinitions();
   ```

#### Acceptance Criteria
- [ ] Batch upload UI accepts multiple PDF files
- [ ] Configuration modal shows pillar selection checkboxes
- [ ] Run mode selection (ONCE vs DEEP_LOOP) works
- [ ] "ALL" checkbox toggles all individual pillars
- [ ] Advanced options are collapsible
- [ ] Configuration is saved before job starts
- [ ] UI updates reflect job status

---

### Task 2.4: Add Job Start Endpoint

**File**: `webdashboard/app.py` (MODIFY)  
**Estimated Time**: 2 hours  
**Complexity**: Low

#### Description
Create API endpoint to start a configured job and build its research database.

#### Implementation Steps

1. **Create job start endpoint**
   ```python
   @app.post("/api/jobs/{job_id}/start")
   async def start_job(
       job_id: str,
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """
       Start execution of a configured job
       
       Args:
           job_id: Job identifier
       
       Returns:
           Confirmation with job status
       """
       verify_api_key(api_key)
       
       job_data = load_job(job_id)
       if not job_data:
           raise HTTPException(status_code=404, detail="Job not found")
       
       if job_data.get("status") not in ["draft", "failed"]:
           raise HTTPException(
               status_code=400,
               detail=f"Job cannot be started (current status: {job_data['status']})"
           )
       
       if not job_data.get("config"):
           raise HTTPException(
               status_code=400,
               detail="Job must be configured before starting"
           )
       
       # Build research database from uploaded files
       try:
           from webdashboard.database_builder import ResearchDatabaseBuilder
           
           job_dir = UPLOADS_DIR / job_id
           pdf_files = list(job_dir.glob("*.pdf"))
           
           if not pdf_files:
               raise HTTPException(
                   status_code=400,
                   detail="No PDF files found for this job"
               )
           
           builder = ResearchDatabaseBuilder(job_id, pdf_files)
           csv_path = builder.build_database()
           
           # Update job data with database path
           job_data["research_database"] = str(csv_path)
           
       except Exception as e:
           logger.error(f"Failed to build database for job {job_id}: {e}")
           raise HTTPException(
               status_code=500,
               detail=f"Failed to build research database: {str(e)}"
           )
       
       # Update job status to queued
       job_data["status"] = "queued"
       job_data["queued_at"] = datetime.utcnow().isoformat()
       save_job(job_id, job_data)
       
       # Enqueue for processing
       await job_runner.enqueue_job(job_id, job_data)
       
       # Broadcast update
       await manager.broadcast({
           "type": "job_started",
           "job": job_data
       })
       
       return {
           "job_id": job_id,
           "status": "queued",
           "message": "Job queued for execution"
       }
   ```

#### Acceptance Criteria
- [ ] Endpoint validates job exists and is in correct status
- [ ] Research database is built before queuing
- [ ] Job status transitions to "queued"
- [ ] Job is enqueued in background runner
- [ ] WebSocket broadcast notifies clients

---

### Task 2.5: Test Complete Input Pipeline

**File**: `tests/integration/test_dashboard_input_pipeline.py` (NEW)  
**Estimated Time**: 3 hours  
**Complexity**: Medium

#### Description
Create comprehensive tests for the batch upload and configuration workflow.

#### Implementation Steps

1. **Test batch upload**
   ```python
   def test_batch_upload_creates_draft_job():
       """Test that batch upload creates a draft job"""
       with open("test1.pdf", "rb") as f1, open("test2.pdf", "rb") as f2:
           response = client.post(
               "/api/upload/batch",
               files=[
                   ("files", ("paper1.pdf", f1, "application/pdf")),
                   ("files", ("paper2.pdf", f2, "application/pdf"))
               ],
               headers={"X-API-KEY": "dev-key-change-in-production"}
           )
       
       assert response.status_code == 200
       data = response.json()
       
       assert data["status"] == "draft"
       assert data["file_count"] == 2
       assert len(data["files"]) == 2
       
       # Verify files were saved
       job_id = data["job_id"]
       job_dir = Path(f"workspace/uploads/{job_id}")
       assert job_dir.exists()
       assert len(list(job_dir.glob("*.pdf"))) == 2
   ```

2. **Test job configuration**
   ```python
   def test_configure_job():
       """Test job configuration endpoint"""
       # First create a draft job
       job_id = create_test_job_with_files()
       
       # Configure it
       config = {
           "pillar_selections": ["Pillar_1", "Pillar_2"],
           "run_mode": "ONCE",
           "convergence_threshold": 5.0
       }
       
       response = client.post(
           f"/api/jobs/{job_id}/configure",
           json=config,
           headers={"X-API-KEY": "dev-key-change-in-production"}
       )
       
       assert response.status_code == 200
       
       # Verify configuration was saved
       job_data = load_job(job_id)
       assert job_data["config"]["pillar_selections"] == ["Pillar_1", "Pillar_2"]
       assert job_data["config"]["run_mode"] == "ONCE"
   ```

3. **Test database building and job start**
   ```python
   def test_start_configured_job():
       """Test starting a configured job builds database and queues it"""
       # Create and configure job
       job_id = create_test_job_with_files()
       configure_test_job(job_id)
       
       # Start job
       response = client.post(
           f"/api/jobs/{job_id}/start",
           headers={"X-API-KEY": "dev-key-change-in-production"}
       )
       
       assert response.status_code == 200
       assert response.json()["status"] == "queued"
       
       # Verify database was created
       db_path = Path(f"workspace/jobs/{job_id}/research_database.csv")
       assert db_path.exists()
       
       # Verify CSV has correct structure
       import pandas as pd
       df = pd.read_csv(db_path)
       assert "Title" in df.columns
       assert "Authors" in df.columns
       assert len(df) > 0
   ```

#### Acceptance Criteria
- [ ] Tests cover upload → configure → start workflow
- [ ] Database building is verified
- [ ] Job status transitions are correct
- [ ] File handling works correctly
- [ ] All tests pass consistently

---

## Phase 2 Deliverables

- [ ] `webdashboard/app.py` - Batch upload and start endpoints
- [ ] `webdashboard/database_builder.py` - Research database builder
- [ ] `webdashboard/templates/index.html` - Configuration UI
- [ ] `tests/integration/test_dashboard_input_pipeline.py` - Tests
- [ ] Documentation of input handling workflow

## Success Metrics

1. **Usability**: Users can upload and configure jobs via UI
2. **Accuracy**: Database extraction achieves 80%+ metadata accuracy
3. **Validation**: Invalid configurations are rejected
4. **Performance**: Database builds in <10 seconds per 10 papers

## Known Limitations (Phase 2)

- PDF metadata extraction is heuristic (may miss some fields)
- No OCR for scanned PDFs (text extraction only)
- Limited to PDF format (no Word, HTML, etc.)
- No duplicate detection across uploads

## Next Phase

After Phase 2 completion, proceed to **Phase 3: Progress Monitoring** to implement real-time progress tracking and visualization.
