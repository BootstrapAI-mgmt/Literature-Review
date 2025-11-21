/**
 * Bulk Job Operations Manager
 * 
 * Provides functionality for:
 * - Multi-select jobs with checkboxes
 * - Bulk delete with confirmation
 * - Bulk export as ZIP
 * - Side-by-side job comparison
 */

class BulkJobManager {
    constructor() {
        this.selectedJobs = new Set();
        this.apiKey = 'dev-key-change-in-production'; // Should match API key
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Select all checkbox
        const selectAllBtn = document.getElementById('selectAllJobs');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => this.selectAll());
        }
        
        const deselectAllBtn = document.getElementById('deselectAllJobs');
        if (deselectAllBtn) {
            deselectAllBtn.addEventListener('click', () => this.deselectAll());
        }
        
        // Individual checkboxes (delegated to handle dynamic job list)
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('job-checkbox')) {
                this.handleJobSelect(e.target);
            }
        });
        
        // Bulk action buttons
        const bulkDeleteBtn = document.getElementById('bulkDelete');
        if (bulkDeleteBtn) {
            bulkDeleteBtn.addEventListener('click', () => this.bulkDelete());
        }
        
        const bulkExportBtn = document.getElementById('bulkExport');
        if (bulkExportBtn) {
            bulkExportBtn.addEventListener('click', () => this.bulkExport());
        }
        
        const bulkCompareBtn = document.getElementById('bulkCompare');
        if (bulkCompareBtn) {
            bulkCompareBtn.addEventListener('click', () => this.compareJobs());
        }
    }
    
    selectAll() {
        const checkboxes = document.querySelectorAll('.job-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = true;
            const jobId = cb.dataset.jobId;
            if (jobId) {
                this.selectedJobs.add(jobId);
            }
        });
        this.updateSelectionUI();
    }
    
    deselectAll() {
        const checkboxes = document.querySelectorAll('.job-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = false;
        });
        this.selectedJobs.clear();
        this.updateSelectionUI();
    }
    
    handleJobSelect(checkbox) {
        const jobId = checkbox.dataset.jobId;
        
        if (!jobId) return;
        
        if (checkbox.checked) {
            this.selectedJobs.add(jobId);
        } else {
            this.selectedJobs.delete(jobId);
        }
        
        this.updateSelectionUI();
    }
    
    updateSelectionUI() {
        const count = this.selectedJobs.size;
        const selectedCountEl = document.getElementById('selectedCount');
        
        if (selectedCountEl) {
            selectedCountEl.textContent = `${count} job${count !== 1 ? 's' : ''} selected`;
        }
        
        // Enable/disable bulk action buttons
        const bulkButtons = document.querySelectorAll('.bulk-action-btn');
        bulkButtons.forEach(btn => {
            btn.disabled = count === 0;
        });
        
        // Show/hide bulk actions container
        const bulkActionsContainer = document.getElementById('bulkActionsContainer');
        if (bulkActionsContainer) {
            if (count > 0) {
                bulkActionsContainer.style.display = 'block';
            } else {
                bulkActionsContainer.style.display = 'none';
            }
        }
    }
    
    async bulkDelete() {
        if (this.selectedJobs.size === 0) return;
        
        // Show confirmation modal
        const confirmed = await this.showDeleteConfirmation();
        
        if (!confirmed) return;
        
        try {
            const response = await fetch('/api/jobs/bulk-delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': this.apiKey
                },
                body: JSON.stringify({
                    job_ids: Array.from(this.selectedJobs)
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Show success message
            alert(`Successfully deleted ${result.deleted_count} job${result.deleted_count !== 1 ? 's' : ''}`);
            
            if (result.errors.length > 0) {
                console.error('Deletion errors:', result.errors);
                alert(`Warning: ${result.error_count} job${result.error_count !== 1 ? 's' : ''} could not be deleted. Check console for details.`);
            }
            
            // Clear selection
            this.selectedJobs.clear();
            this.updateSelectionUI();
            
            // Refresh page to show updated job list
            window.location.reload();
            
        } catch (error) {
            console.error('Bulk delete failed:', error);
            alert('Error deleting jobs. Please try again.');
        }
    }
    
    async bulkExport() {
        if (this.selectedJobs.size === 0) return;
        
        try {
            const response = await fetch('/api/jobs/bulk-export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': this.apiKey
                },
                body: JSON.stringify({
                    job_ids: Array.from(this.selectedJobs)
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Download ZIP file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'jobs_export.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // Show success message
            alert(`Successfully exported ${this.selectedJobs.size} job${this.selectedJobs.size !== 1 ? 's' : ''}`);
            
        } catch (error) {
            console.error('Bulk export failed:', error);
            alert('Error exporting jobs. Please try again.');
        }
    }
    
    async compareJobs() {
        if (this.selectedJobs.size < 2) {
            alert('Please select at least 2 jobs to compare');
            return;
        }
        
        if (this.selectedJobs.size > 5) {
            alert('Cannot compare more than 5 jobs at once');
            return;
        }
        
        try {
            const response = await fetch('/api/jobs/compare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': this.apiKey
                },
                body: JSON.stringify({
                    job_ids: Array.from(this.selectedJobs)
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const comparison = await response.json();
            
            // Show comparison modal
            this.showComparisonModal(comparison);
            
        } catch (error) {
            console.error('Comparison failed:', error);
            alert('Error comparing jobs. Please try again.');
        }
    }
    
    showDeleteConfirmation() {
        return new Promise((resolve) => {
            const modal = document.getElementById('deleteConfirmModal');
            if (!modal) {
                console.error('Delete confirmation modal not found');
                resolve(false);
                return;
            }
            
            const jobList = document.getElementById('deleteJobList');
            
            // Get job names for display
            const jobNames = [];
            this.selectedJobs.forEach(jobId => {
                const checkbox = document.querySelector(`.job-checkbox[data-job-id="${jobId}"]`);
                if (checkbox) {
                    const row = checkbox.closest('tr');
                    if (row) {
                        const nameCell = row.querySelector('td:nth-child(2)'); // Assuming name is in 2nd column
                        jobNames.push(nameCell ? nameCell.textContent.trim() : jobId);
                    } else {
                        jobNames.push(jobId);
                    }
                } else {
                    jobNames.push(jobId);
                }
            });
            
            // Populate job list
            if (jobList) {
                jobList.innerHTML = jobNames
                    .map(name => `<li class="list-group-item">${name}</li>`)
                    .join('');
            }
            
            // Show count
            const countEl = document.getElementById('deleteJobCount');
            if (countEl) {
                countEl.textContent = this.selectedJobs.size;
            }
            
            // Show modal
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
            
            // Handle confirmation
            const confirmBtn = document.getElementById('confirmDelete');
            const cancelBtn = document.getElementById('cancelDelete');
            
            const confirmHandler = () => {
                modalInstance.hide();
                resolve(true);
                cleanup();
            };
            
            const cancelHandler = () => {
                modalInstance.hide();
                resolve(false);
                cleanup();
            };
            
            const cleanup = () => {
                confirmBtn.removeEventListener('click', confirmHandler);
                cancelBtn.removeEventListener('click', cancelHandler);
            };
            
            confirmBtn.addEventListener('click', confirmHandler);
            cancelBtn.addEventListener('click', cancelHandler);
        });
    }
    
    showComparisonModal(comparison) {
        const modal = document.getElementById('bulkComparisonModal');
        if (!modal) {
            console.error('Comparison modal not found');
            return;
        }
        
        const tableBody = document.getElementById('comparisonTableBody');
        
        if (!tableBody) {
            console.error('Comparison table body not found');
            return;
        }
        
        // Build comparison table rows
        const metrics = [
            { label: 'Job Name', key: 'name' },
            { label: 'Created', key: 'created_at', format: (val) => val ? new Date(val).toLocaleDateString() : 'N/A' },
            { label: 'Status', key: 'status' },
            { label: 'Papers Analyzed', key: 'papers_analyzed' },
            { label: 'Overall Coverage', key: 'overall_coverage', format: (val) => `${val}%` }
        ];
        
        let html = '';
        metrics.forEach(metric => {
            html += '<tr>';
            html += `<td><strong>${metric.label}</strong></td>`;
            comparison.jobs.forEach(job => {
                const value = job[metric.key];
                const displayValue = metric.format ? metric.format(value) : value;
                html += `<td>${displayValue}</td>`;
            });
            html += '</tr>';
        });
        
        tableBody.innerHTML = html;
        
        // Update aggregate metrics
        const avgCoverageEl = document.getElementById('avgCoverage');
        if (avgCoverageEl) {
            avgCoverageEl.textContent = `${comparison.metrics.avg_coverage}%`;
        }
        
        const totalPapersEl = document.getElementById('totalPapers');
        if (totalPapersEl) {
            totalPapersEl.textContent = comparison.metrics.total_papers;
        }
        
        const coverageRangeEl = document.getElementById('coverageRange');
        if (coverageRangeEl) {
            coverageRangeEl.textContent = `${comparison.metrics.coverage_range.min}% - ${comparison.metrics.coverage_range.max}%`;
        }
        
        // Show modal
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.bulkJobManager = new BulkJobManager();
});
