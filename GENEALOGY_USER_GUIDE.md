# Job Genealogy Visualization - User Guide

## Overview

The Job Genealogy Visualization feature provides an interactive way to explore the lineage of incremental literature review jobs. It shows the parent-child relationships between jobs, tracks gap reduction over time, and visualizes coverage progress.

## Access

To view a job's genealogy:

1. **From Dashboard**: 
   - Click on any job to open the Job Detail modal
   - Click the "🌳 View Genealogy" button
   - The genealogy page opens in a new tab

2. **Direct URL**:
   - Navigate to `/genealogy?job_id=<JOB_ID>`
   - Example: `http://localhost:5001/genealogy?job_id=job_20250120_143000`

## Features

### 1. Tree View (Default)
- **Visualization**: D3.js-based tree showing job hierarchy
- **Node Colors**: 
  - 🟢 Green (90%+ coverage): Excellent coverage
  - 🟡 Yellow (70-89% coverage): Good coverage
  - 🟠 Orange (50-69% coverage): Fair coverage
  - 🔴 Red (<50% coverage): Low coverage
- **Node Information**:
  - Date (top)
  - Gap count (center)
  - Coverage percentage (center)
  - Papers analyzed (bottom)
- **Interactions**:
  - **Hover**: Shows detailed tooltip with job metrics
  - **Click**: Navigates to job details page

### 2. Timeline View
- **Visualization**: Horizontal timeline showing chronological progression
- **Same Color Coding**: As tree view
- **Better For**: Visualizing linear progression of incremental reviews

### 3. Table View
- **Tabular Display**: All jobs listed in a table
- **Columns**:
  - Job ID (truncated)
  - Creation Date
  - Job Type (baseline/incremental)
  - Papers Analyzed
  - Total Gaps
  - Coverage (with colored progress bar)
  - Actions (View button)
- **Better For**: Comparing specific metrics across jobs

### 4. Gap Reduction Chart
- **Type**: Line chart (Chart.js)
- **X-axis**: Date
- **Y-axis**: Number of gaps
- **Shows**: How gaps decrease (or increase) over time
- **Use Case**: Track progress in addressing research gaps

### 5. Coverage Progress Chart
- **Type**: Line chart (Chart.js)
- **X-axis**: Date
- **Y-axis**: Coverage percentage (0-100%)
- **Shows**: How coverage improves over incremental reviews
- **Use Case**: Visualize overall improvement in literature coverage

### 6. Export Options
- **PNG Export**: Download tree visualization as PNG image
  - Includes white background for printing
  - Resolution: 1000x600 pixels
- **SVG Export**: Download tree visualization as SVG
  - Vector format for scaling
  - Can be edited in vector graphics editors

## API Endpoint

The genealogy visualization consumes the `/api/jobs/{job_id}/lineage` endpoint:

### Request
```bash
curl -H "X-API-KEY: your-api-key" \
  http://localhost:5001/api/jobs/job_20250120_143000/lineage
```

### Response
```json
{
  "job_id": "job_20250120_143000",
  "job_type": "incremental",
  "parent_job_id": "job_20250115_103000",
  "child_job_ids": ["job_20250125_120000"],
  "ancestors": [
    {
      "job_id": "job_20250101_100000",
      "created_at": "2025-01-01T10:00:00",
      "job_type": "baseline",
      "gap_metrics": {
        "total_gaps": 28,
        "gaps_by_pillar": {
          "pillar_1": 5,
          "pillar_2": 8
        }
      },
      "overall_coverage": 72.5,
      "papers_analyzed": 150
    },
    {
      "job_id": "job_20250115_103000",
      "created_at": "2025-01-15T10:30:00",
      "job_type": "incremental",
      "gap_metrics": {
        "total_gaps": 23,
        "gaps_by_pillar": {
          "pillar_1": 4,
          "pillar_2": 7
        }
      },
      "overall_coverage": 78.2,
      "papers_analyzed": 162
    }
  ],
  "lineage_depth": 2,
  "root_job_id": "job_20250101_100000",
  "metrics_timeline": [...],
  "current_metrics": {
    "job_id": "job_20250120_143000",
    "gap_metrics": {
      "total_gaps": 15,
      "gaps_by_pillar": {
        "pillar_1": 2,
        "pillar_2": 5
      }
    },
    "overall_coverage": 88.5,
    "papers_analyzed": 177
  }
}
```

## Use Cases

### 1. Track Incremental Progress
- Visualize how each incremental review improves coverage
- See gap reduction over time
- Identify which increments had the most impact

### 2. Quality Control
- Verify that coverage is consistently improving
- Identify reviews that didn't improve metrics (red flags)
- Compare paper counts to understand effort

### 3. Reporting
- Export visualizations for presentations
- Show stakeholders the progress over time
- Document the review methodology

### 4. Planning Next Steps
- See current gap count to plan next increment
- Identify which pillars still need attention
- Understand coverage trajectory

## Technical Details

### Files
- **Template**: `webdashboard/templates/job_genealogy.html`
- **JavaScript**: `webdashboard/static/js/genealogy_viz.js`
- **CSS**: `webdashboard/static/css/genealogy.css`
- **API**: `webdashboard/api/incremental.py` (enhanced lineage endpoint)

### Dependencies
- **D3.js v7**: Tree and timeline visualizations
- **Chart.js v4**: Line charts for metrics
- **Bootstrap 5**: UI styling and layout

### Browser Compatibility
- Modern browsers with ES6+ support
- Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

## Troubleshooting

### "No job ID provided" Error
- Ensure the URL includes `?job_id=<JOB_ID>`
- Check that the job ID is valid

### Empty Visualization
- Job may not have any ancestors (single baseline job)
- Gap analysis reports may not exist for jobs
- Check browser console for errors

### Export Not Working
- Browser may block downloads - check settings
- Try different export format (PNG vs SVG)
- Ensure visualization is fully loaded before exporting

## Future Enhancements

Potential improvements (not currently implemented):
- Real-time updates via WebSocket
- 3D visualization option
- Collaborative annotations
- Comparison mode (side-by-side lineages)
- Custom date range filtering
- Pillar-specific gap tracking charts
