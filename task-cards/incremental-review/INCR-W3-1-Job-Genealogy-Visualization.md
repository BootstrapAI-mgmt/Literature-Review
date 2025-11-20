# INCR-W3-1: Dashboard Job Genealogy Visualization

**Wave:** 3 (User Experience)  
**Priority:** 🟡 Medium  
**Effort:** 6-8 hours  
**Status:** 🟡 Blocked (requires Wave 2)  
**Assignable:** Frontend Developer

---

## Overview

Create interactive job lineage tree visualization showing parent-child relationships, gap reduction over time, and cumulative progress across incremental reviews.

---

## Dependencies

**Prerequisites:**
- ✅ INCR-W2-2 (Dashboard Job Continuation API - lineage endpoint)
- ✅ INCR-W2-3 (Dashboard Continuation UI)

---

## Scope

### Included
- [x] Tree visualization (D3.js or similar)
- [x] Interactive nodes (click to view job)
- [x] Gap reduction metrics over time
- [x] Timeline view (linear progression)
- [x] Export genealogy as PNG/SVG
- [x] Responsive design

### Excluded
- ❌ Real-time updates (refresh-based only)
- ❌ 3D visualization
- ❌ Collaborative annotations

---

## UI Mockup

```
┌──────────────────────────────────────────────────────────────┐
│  Job Genealogy: Review - Neuromorphic 2025                   │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  View: [Tree ▼] [Timeline] [Table]     [Export PNG ▼]        │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │        ┌─────────────────┐                              │ │
│  │        │  Baseline       │                              │ │
│  │        │  Jan 1, 2025    │                              │ │
│  │        │  150 papers     │                              │ │
│  │        │  28 gaps        │                              │ │
│  │        │  72% coverage   │                              │ │
│  │        └────────┬────────┘                              │ │
│  │                 │                                        │ │
│  │                 ├────────┬────────┬────────┐            │ │
│  │                 │        │        │        │            │ │
│  │        ┌────────▼──┐ ┌──▼────┐  ┌▼──────┐ ▼            │ │
│  │        │ Update 1  │ │Update2│  │Update3│ ...          │ │
│  │        │ Jan 15    │ │Jan 30 │  │Feb 15 │              │ │
│  │        │ +12 papers│ │+8 ppr │  │+15 ppr│              │ │
│  │        │ 23 gaps ✓ │ │20 gaps│  │15 gaps│              │ │
│  │        │ 78% cov   │ │82% cov│  │88% cov│              │ │
│  │        └───────────┘ └───────┘  └───────┘              │ │
│  │                                                           │ │
│  │  Hover to see details | Click to view job                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  📊 Gap Reduction Chart:                                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Gaps                                                      │ │
│  │  30 ┤                                                     │ │
│  │  25 ┤●                                                    │ │
│  │  20 ┤  ●─────●                                           │ │
│  │  15 ┤           ●─────●                                  │ │
│  │  10 ┤                    ●                               │ │
│  │   0 └─────────────────────────────────────────────────── │ │
│  │     Jan 1  Jan 15  Jan 30  Feb 15  Mar 1                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  📈 Coverage Progress:                                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Coverage %                                                │ │
│  │ 100 ┤                                        ●            │ │
│  │  90 ┤                                   ●                 │ │
│  │  80 ┤                              ●                      │ │
│  │  70 ┤●────●                                               │ │
│  │  60 ┤                                                     │ │
│  │   0 └─────────────────────────────────────────────────── │ │
│  │     Jan 1  Jan 15  Jan 30  Feb 15  Mar 1                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation

### File Structure

```
webdashboard/
├── templates/
│   └── job_genealogy.html (NEW)
├── static/
│   ├── js/
│   │   └── genealogy_viz.js (NEW)
│   └── css/
│       └── genealogy.css (NEW)
```

### D3.js Tree Visualization

```javascript
// static/js/genealogy_viz.js

import * as d3 from 'd3';

class JobGenealogyViz {
    constructor(containerId, data) {
        this.container = d3.select(`#${containerId}`);
        this.data = data;
        this.width = 1000;
        this.height = 600;
        
        this.svg = this.container
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        this.render();
    }
    
    render() {
        // Create tree layout
        const treeLayout = d3.tree()
            .size([this.width - 100, this.height - 100]);
        
        // Build hierarchy
        const root = d3.hierarchy(this.data);
        treeLayout(root);
        
        // Draw links (parent-child connections)
        this.svg.selectAll('.link')
            .data(root.links())
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('d', d3.linkVertical()
                .x(d => d.x)
                .y(d => d.y)
            )
            .attr('fill', 'none')
            .attr('stroke', '#999')
            .attr('stroke-width', 2);
        
        // Draw nodes (jobs)
        const nodes = this.svg.selectAll('.node')
            .data(root.descendants())
            .enter()
            .append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${d.x},${d.y})`)
            .on('click', (event, d) => this.handleNodeClick(d))
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());
        
        // Node circles
        nodes.append('circle')
            .attr('r', 30)
            .attr('fill', d => this.getNodeColor(d.data))
            .attr('stroke', '#333')
            .attr('stroke-width', 2);
        
        // Node labels
        nodes.append('text')
            .attr('dy', -35)
            .attr('text-anchor', 'middle')
            .text(d => d.data.name)
            .attr('font-size', '12px')
            .attr('font-weight', 'bold');
        
        // Gap count
        nodes.append('text')
            .attr('dy', 5)
            .attr('text-anchor', 'middle')
            .text(d => `${d.data.gaps} gaps`)
            .attr('font-size', '10px');
        
        // Coverage
        nodes.append('text')
            .attr('dy', 18)
            .attr('text-anchor', 'middle')
            .text(d => `${d.data.coverage}%`)
            .attr('font-size', '10px')
            .attr('fill', '#666');
    }
    
    getNodeColor(nodeData) {
        // Color by coverage
        if (nodeData.coverage >= 90) return '#28a745'; // Green
        if (nodeData.coverage >= 70) return '#ffc107'; // Yellow
        return '#dc3545'; // Red
    }
    
    handleNodeClick(node) {
        // Navigate to job details
        window.location.href = `/jobs/${node.data.job_id}`;
    }
    
    showTooltip(event, node) {
        const tooltip = d3.select('#tooltip');
        tooltip.style('display', 'block')
            .style('left', `${event.pageX + 10}px`)
            .style('top', `${event.pageY + 10}px`)
            .html(`
                <strong>${node.data.name}</strong><br>
                Job ID: ${node.data.job_id}<br>
                Date: ${new Date(node.data.created_at).toLocaleDateString()}<br>
                Papers: ${node.data.papers}<br>
                Gaps: ${node.data.gaps}<br>
                Coverage: ${node.data.coverage}%
            `);
    }
    
    hideTooltip() {
        d3.select('#tooltip').style('display', 'none');
    }
}

// Load genealogy data and render
async function loadGenealogyViz(jobId) {
    const response = await fetch(`/api/jobs/${jobId}/lineage`);
    const data = await response.json();
    
    // Transform to tree structure
    const treeData = transformLineageToTree(data);
    
    // Render visualization
    new JobGenealogyViz('genealogy-container', treeData);
    
    // Render charts
    renderGapReductionChart(data);
    renderCoverageProgressChart(data);
}

function transformLineageToTree(lineageData) {
    // Convert flat lineage to hierarchical tree
    // Root = oldest ancestor
    const root = {
        name: 'Baseline',
        job_id: lineageData.root_job_id,
        children: []
    };
    
    // Build tree recursively
    // (Implementation depends on API response structure)
    
    return root;
}

function renderGapReductionChart(data) {
    // Use Chart.js or D3 line chart
    const ctx = document.getElementById('gapReductionChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.ancestors.map(a => new Date(a.created_at).toLocaleDateString()),
            datasets: [{
                label: 'Gaps Over Time',
                data: data.ancestors.map(a => a.gap_metrics.total_gaps),
                borderColor: '#007bff',
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderCoverageProgressChart(data) {
    const ctx = document.getElementById('coverageProgressChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.ancestors.map(a => new Date(a.created_at).toLocaleDateString()),
            datasets: [{
                label: 'Coverage %',
                data: data.ancestors.map(a => a.overall_coverage),
                borderColor: '#28a745',
                fill: true,
                backgroundColor: 'rgba(40, 167, 69, 0.1)'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    min: 0,
                    max: 100
                }
            }
        }
    });
}
```

---

## Backend API Enhancement

Update `/api/jobs/{job_id}/lineage` to include metrics:

```python
@incremental_bp.route('/<job_id>/lineage', methods=['GET'])
def get_job_lineage(job_id: str):
    """Enhanced lineage with gap metrics."""
    # ... existing code ...
    
    # Add gap metrics for each ancestor
    for ancestor in ancestors:
        ancestor_state = load_state(ancestor['job_id'])
        ancestor['gap_metrics'] = {
            'total_gaps': ancestor_state.gap_metrics.total_gaps,
            'gaps_by_pillar': ancestor_state.gap_metrics.gaps_by_pillar
        }
        ancestor['overall_coverage'] = ancestor_state.overall_coverage
        ancestor['papers'] = ancestor_state.total_papers
    
    return jsonify({
        'job_id': job_id,
        'ancestors': ancestors,
        'root_job_id': root_job_id,
        'metrics_timeline': ancestors  # For charting
    })
```

---

## Deliverables

- [ ] D3.js tree visualization
- [ ] Gap reduction chart (Chart.js)
- [ ] Coverage progress chart
- [ ] Interactive tooltips
- [ ] Export to PNG/SVG
- [ ] Timeline view (alternative layout)
- [ ] Responsive design
- [ ] Unit tests (Jest for JS)

---

## Success Criteria

✅ **Functional:**
- Tree renders correctly
- Click navigates to job
- Charts show accurate data
- Export works

✅ **UX:**
- Intuitive layout
- Smooth interactions
- Clear visual hierarchy
- Mobile-friendly

✅ **Performance:**
- Renders < 1s for 20+ jobs
- No lag on interactions

---

**Status:** 🟡 Blocked (requires Wave 2)  
**Assignee:** TBD  
**Estimated Start:** Week 3, Day 1  
**Estimated Completion:** Week 3, Day 3
