# INCR-W3-3: Dashboard Bulk Job Management

**Wave:** 3 (User Experience)  
**Priority:** 🟡 Medium (from parity roadmap)  
**Effort:** 4-6 hours  
**Status:** 🟢 Ready  
**Assignable:** Full-Stack Developer

---

## Overview

Add bulk operations for managing multiple jobs: multi-select, bulk delete, bulk export, and job comparison. Improves UX for users managing many review iterations.

---

## Dependencies

**Prerequisites:** None (independent UX enhancement)

---

## Scope

### Included
- [x] Multi-select checkboxes on job list
- [x] Bulk delete (with confirmation)
- [x] Bulk export (zip archive)
- [x] Side-by-side job comparison
- [x] Job filtering and search
- [x] Select all / deselect all

### Excluded
- ❌ Bulk re-run (future enhancement)
- ❌ Bulk tag/categorization
- ❌ Advanced filtering (date ranges, custom fields)

---

## UI Mockup

```
┌──────────────────────────────────────────────────────────────┐
│  My Jobs                                    [+ New Job]       │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  [Select All] [Deselect All]                                  │
│                                                                │
│  Selected: 3 jobs                                             │
│  Actions: [Delete] [Export] [Compare]                         │
│                                                                │
│  Filter: [All ▼] [Status ▼] [Date ▼]   🔍 Search...          │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐│
│  │☑ Baseline Review       | Jan 1, 2025  | ✓ Complete | ... ││
│  │☑ Update Feb            | Feb 1, 2025  | ✓ Complete | ... ││
│  │☑ Update Mar            | Mar 1, 2025  | ⚙ Running  | ... ││
│  │☐ Comparative Study     | Mar 15, 2025 | ✓ Complete | ... ││
│  │☐ Pilot Study          | Dec 1, 2024  | ❌ Failed  | ... ││
│  └──────────────────────────────────────────────────────────┘│
│                                                                │
│  Showing 1-5 of 12 jobs                        [← 1 2 3 →]   │
│                                                                │
└──────────────────────────────────────────────────────────────┘

Bulk Delete Confirmation:
┌──────────────────────────────────────────┐
│  Delete 3 Jobs?                          │
│                                          │
│  This will permanently delete:           │
│  • Baseline Review                       │
│  • Update Feb                            │
│  • Update Mar                            │
│                                          │
│  This action cannot be undone.           │
│                                          │
│  [Cancel]  [Delete Permanently]          │
└──────────────────────────────────────────┘
```

---

## Implementation

### Backend API

Create `webdashboard/api/bulk_operations.py`:

```python
"""Bulk job operations API."""

from flask import Blueprint, request, jsonify, send_file
import shutil
import zipfile
from pathlib import Path

bulk_bp = Blueprint('bulk', __name__, url_prefix='/api/jobs')

@bulk_bp.route('/bulk-delete', methods=['POST'])
def bulk_delete_jobs():
    """
    Delete multiple jobs.
    
    POST /api/jobs/bulk-delete
    Body: {"job_ids": ["job1", "job2", ...]}
    """
    data = request.get_json()
    job_ids = data.get('job_ids', [])
    
    if not job_ids:
        return jsonify({'error': 'No job IDs provided'}), 400
    
    deleted = []
    errors = []
    
    for job_id in job_ids:
        try:
            job_dir = Path(f'/workspaces/jobs/{job_id}')
            if job_dir.exists():
                shutil.rmtree(job_dir)
                deleted.append(job_id)
            else:
                errors.append(f"{job_id}: Not found")
        except Exception as e:
            errors.append(f"{job_id}: {str(e)}")
    
    return jsonify({
        'deleted': deleted,
        'errors': errors,
        'deleted_count': len(deleted),
        'error_count': len(errors)
    }), 200

@bulk_bp.route('/bulk-export', methods=['POST'])
def bulk_export_jobs():
    """
    Export multiple jobs as zip archive.
    
    POST /api/jobs/bulk-export
    Body: {"job_ids": ["job1", "job2", ...]}
    """
    data = request.get_json()
    job_ids = data.get('job_ids', [])
    
    if not job_ids:
        return jsonify({'error': 'No job IDs provided'}), 400
    
    # Create temp zip file
    zip_path = Path('/tmp/jobs_export.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for job_id in job_ids:
            job_dir = Path(f'/workspaces/jobs/{job_id}')
            
            if not job_dir.exists():
                continue
            
            # Add all files in job directory
            for file_path in job_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to('/workspaces/jobs')
                    zipf.write(file_path, arcname)
    
    return send_file(
        str(zip_path),
        mimetype='application/zip',
        as_attachment=True,
        download_name='jobs_export.zip'
    )

@bulk_bp.route('/compare', methods=['POST'])
def compare_jobs():
    """
    Compare multiple jobs side-by-side.
    
    POST /api/jobs/compare
    Body: {"job_ids": ["job1", "job2"]}
    """
    data = request.get_json()
    job_ids = data.get('job_ids', [])
    
    if len(job_ids) < 2:
        return jsonify({'error': 'Need at least 2 jobs to compare'}), 400
    
    comparison = []
    
    for job_id in job_ids:
        job_dir = Path(f'/workspaces/jobs/{job_id}')
        state_file = job_dir / 'orchestrator_state.json'
        
        if not state_file.exists():
            continue
        
        state = load_json(state_file)
        
        comparison.append({
            'job_id': job_id,
            'name': state.get('job_name', job_id),
            'created_at': state.get('created_at'),
            'papers_analyzed': state.get('papers_analyzed'),
            'total_gaps': state.get('gap_metrics', {}).get('total_gaps'),
            'overall_coverage': state.get('overall_coverage')
        })
    
    return jsonify({
        'jobs': comparison,
        'metrics': {
            'avg_coverage': sum(j['overall_coverage'] for j in comparison) / len(comparison),
            'total_papers': sum(j['papers_analyzed'] for j in comparison),
            'coverage_improvement': comparison[-1]['overall_coverage'] - comparison[0]['overall_coverage']
        }
    }), 200
```

### Frontend Component

```javascript
// static/js/bulk_operations.js

class BulkJobManager {
    constructor() {
        this.selectedJobs = new Set();
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Select all checkbox
        document.getElementById('selectAll').addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.job-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
                this.handleJobSelect(cb);
            });
        });
        
        // Individual checkboxes
        document.querySelectorAll('.job-checkbox').forEach(cb => {
            cb.addEventListener('change', () => this.handleJobSelect(cb));
        });
        
        // Bulk actions
        document.getElementById('bulkDelete').addEventListener('click', () => this.bulkDelete());
        document.getElementById('bulkExport').addEventListener('click', () => this.bulkExport());
        document.getElementById('bulkCompare').addEventListener('click', () => this.compareJobs());
    }
    
    handleJobSelect(checkbox) {
        const jobId = checkbox.dataset.jobId;
        
        if (checkbox.checked) {
            this.selectedJobs.add(jobId);
        } else {
            this.selectedJobs.delete(jobId);
        }
        
        this.updateSelectionUI();
    }
    
    updateSelectionUI() {
        const count = this.selectedJobs.size;
        document.getElementById('selectedCount').textContent = `Selected: ${count} jobs`;
        
        // Enable/disable bulk action buttons
        const bulkButtons = document.querySelectorAll('.bulk-action-btn');
        bulkButtons.forEach(btn => {
            btn.disabled = count === 0;
        });
    }
    
    async bulkDelete() {
        if (this.selectedJobs.size === 0) return;
        
        // Show confirmation modal
        const confirmed = await this.showDeleteConfirmation();
        
        if (!confirmed) return;
        
        try {
            const response = await fetch('/api/jobs/bulk-delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_ids: Array.from(this.selectedJobs)
                })
            });
            
            const result = await response.json();
            
            alert(`Deleted ${result.deleted_count} jobs successfully`);
            
            // Refresh page
            window.location.reload();
        } catch (error) {
            console.error('Bulk delete failed:', error);
            alert('Error deleting jobs');
        }
    }
    
    async bulkExport() {
        if (this.selectedJobs.size === 0) return;
        
        try {
            const response = await fetch('/api/jobs/bulk-export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_ids: Array.from(this.selectedJobs)
                })
            });
            
            // Download zip file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'jobs_export.zip';
            a.click();
        } catch (error) {
            console.error('Bulk export failed:', error);
            alert('Error exporting jobs');
        }
    }
    
    async compareJobs() {
        if (this.selectedJobs.size < 2) {
            alert('Please select at least 2 jobs to compare');
            return;
        }
        
        try {
            const response = await fetch('/api/jobs/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_ids: Array.from(this.selectedJobs)
                })
            });
            
            const comparison = await response.json();
            
            // Show comparison modal
            this.showComparisonModal(comparison);
        } catch (error) {
            console.error('Comparison failed:', error);
            alert('Error comparing jobs');
        }
    }
    
    showDeleteConfirmation() {
        return new Promise((resolve) => {
            const modal = document.getElementById('deleteConfirmModal');
            const jobList = document.getElementById('deleteJobList');
            
            // Populate job list
            jobList.innerHTML = Array.from(this.selectedJobs)
                .map(jobId => `<li>${jobId}</li>`)
                .join('');
            
            // Show modal
            modal.style.display = 'block';
            
            document.getElementById('confirmDelete').onclick = () => {
                modal.style.display = 'none';
                resolve(true);
            };
            
            document.getElementById('cancelDelete').onclick = () => {
                modal.style.display = 'none';
                resolve(false);
            };
        });
    }
    
    showComparisonModal(comparison) {
        const modal = document.getElementById('comparisonModal');
        const table = document.getElementById('comparisonTable');
        
        // Build comparison table
        let html = `
            <table class="table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        ${comparison.jobs.map(j => `<th>${j.name}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Papers Analyzed</td>
                        ${comparison.jobs.map(j => `<td>${j.papers_analyzed}</td>`).join('')}
                    </tr>
                    <tr>
                        <td>Total Gaps</td>
                        ${comparison.jobs.map(j => `<td>${j.total_gaps}</td>`).join('')}
                    </tr>
                    <tr>
                        <td>Coverage</td>
                        ${comparison.jobs.map(j => `<td>${j.overall_coverage}%</td>`).join('')}
                    </tr>
                </tbody>
            </table>
        `;
        
        table.innerHTML = html;
        modal.style.display = 'block';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    new BulkJobManager();
});
```

---

## Deliverables

- [ ] Multi-select UI with checkboxes
- [ ] Bulk delete endpoint + confirmation modal
- [ ] Bulk export endpoint (zip generation)
- [ ] Job comparison endpoint + modal
- [ ] Job filtering and search
- [ ] Unit tests (backend + frontend)
- [ ] Integration tests

---

## Success Criteria

✅ **Functional:**
- Can select multiple jobs
- Bulk delete works (with confirmation)
- Bulk export creates zip
- Comparison shows side-by-side metrics

✅ **UX:**
- Intuitive multi-select
- Clear confirmation dialogs
- Fast operations (<3s for 10 jobs)

✅ **Safety:**
- Delete confirmation prevents accidents
- Export doesn't timeout on large jobs

---

**Status:** 🟢 Ready  
**Assignee:** TBD  
**Estimated Start:** Week 3, Day 4  
**Estimated Completion:** Week 3, Day 5
