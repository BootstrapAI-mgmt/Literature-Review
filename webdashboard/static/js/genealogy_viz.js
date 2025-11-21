/**
 * Job Genealogy Visualization
 * 
 * D3.js-based interactive tree visualization for job lineage,
 * showing parent-child relationships, gap reduction, and coverage progress.
 */

let lineageData = null;
let treeData = null;
let gapChart = null;
let coverageChart = null;

/**
 * Load genealogy data and render all visualizations
 */
async function loadGenealogyViz(jobId) {
    try {
        const apiKey = 'dev-key-change-in-production';
        const response = await fetch(`/api/jobs/${jobId}/lineage`, {
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        lineageData = await response.json();
        
        // Update title
        document.getElementById('jobTitle').textContent = `Job ${jobId.substring(0, 8)}... Lineage`;
        
        // Transform to tree structure
        treeData = transformLineageToTree(lineageData);
        
        // Render visualizations
        renderTree(treeData);
        renderGapReductionChart(lineageData.metrics_timeline);
        renderCoverageProgressChart(lineageData.metrics_timeline);
        renderTableView(lineageData.metrics_timeline);
        
    } catch (error) {
        console.error('Failed to load genealogy:', error);
        alert('Error loading job genealogy: ' + error.message);
    }
}

/**
 * Transform flat lineage data to hierarchical tree structure
 */
function transformLineageToTree(lineageData) {
    const timeline = lineageData.metrics_timeline || [];
    
    if (timeline.length === 0) {
        // Single node (no ancestors)
        return {
            name: formatJobName(lineageData.job_id),
            job_id: lineageData.job_id,
            created_at: lineageData.current_metrics?.created_at,
            gaps: lineageData.current_metrics?.gap_metrics?.total_gaps || 0,
            coverage: lineageData.current_metrics?.overall_coverage || 0,
            papers: lineageData.current_metrics?.papers_analyzed || 0,
            children: []
        };
    }
    
    // Build tree from timeline (oldest to newest)
    const root = {
        name: formatJobName(timeline[0].job_id),
        job_id: timeline[0].job_id,
        created_at: timeline[0].created_at,
        gaps: timeline[0].gap_metrics?.total_gaps || 0,
        coverage: timeline[0].overall_coverage || 0,
        papers: timeline[0].papers_analyzed || 0,
        children: []
    };
    
    // Build chain of nodes
    let current = root;
    for (let i = 1; i < timeline.length; i++) {
        const job = timeline[i];
        const node = {
            name: formatJobName(job.job_id),
            job_id: job.job_id,
            created_at: job.created_at,
            gaps: job.gap_metrics?.total_gaps || 0,
            coverage: job.overall_coverage || 0,
            papers: job.papers_analyzed || 0,
            children: []
        };
        current.children.push(node);
        current = node;
    }
    
    return root;
}

/**
 * Format job ID for display
 */
function formatJobName(jobId) {
    // Extract date if job_id follows pattern job_YYYYMMDD_HHMMSS
    const match = jobId.match(/job_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})/);
    if (match) {
        const [_, year, month, day, hour, minute] = match;
        return `${month}/${day}/${year}`;
    }
    return jobId.substring(0, 12);
}

/**
 * Render D3.js tree visualization
 */
function renderTree(data) {
    const container = d3.select('#genealogy-tree');
    container.html(''); // Clear previous
    
    const width = 1000;
    const height = 600;
    const margin = { top: 50, right: 90, bottom: 50, left: 90 };
    
    const svg = container
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Create tree layout
    const treeLayout = d3.tree()
        .size([width - margin.left - margin.right, height - margin.top - margin.bottom]);
    
    // Build hierarchy
    const root = d3.hierarchy(data);
    treeLayout(root);
    
    // Draw links (parent-child connections)
    svg.selectAll('.link')
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
    const nodes = svg.selectAll('.node')
        .data(root.descendants())
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${d.x},${d.y})`)
        .on('click', (event, d) => handleNodeClick(d))
        .on('mouseover', (event, d) => showTooltip(event, d))
        .on('mouseout', () => hideTooltip())
        .style('cursor', 'pointer');
    
    // Node circles
    nodes.append('circle')
        .attr('r', 40)
        .attr('fill', d => getNodeColor(d.data))
        .attr('stroke', '#333')
        .attr('stroke-width', 2);
    
    // Node labels (date)
    nodes.append('text')
        .attr('dy', -50)
        .attr('text-anchor', 'middle')
        .text(d => d.data.name)
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .attr('fill', '#333');
    
    // Gap count
    nodes.append('text')
        .attr('dy', 0)
        .attr('text-anchor', 'middle')
        .text(d => `${d.data.gaps} gaps`)
        .attr('font-size', '11px')
        .attr('fill', '#fff')
        .attr('font-weight', 'bold');
    
    // Coverage
    nodes.append('text')
        .attr('dy', 15)
        .attr('text-anchor', 'middle')
        .text(d => `${Math.round(d.data.coverage)}%`)
        .attr('font-size', '11px')
        .attr('fill', '#fff');
    
    // Papers count
    nodes.append('text')
        .attr('dy', 55)
        .attr('text-anchor', 'middle')
        .text(d => `${d.data.papers} papers`)
        .attr('font-size', '9px')
        .attr('fill', '#666');
}

/**
 * Get node color based on coverage
 */
function getNodeColor(nodeData) {
    const coverage = nodeData.coverage || 0;
    if (coverage >= 90) return '#28a745'; // Green
    if (coverage >= 70) return '#ffc107'; // Yellow
    if (coverage >= 50) return '#fd7e14'; // Orange
    return '#dc3545'; // Red
}

/**
 * Handle node click - navigate to job details
 */
function handleNodeClick(node) {
    window.location.href = `/?job_id=${node.data.job_id}#jobDetail`;
}

/**
 * Show tooltip on hover
 */
function showTooltip(event, node) {
    const tooltip = d3.select('#tooltip');
    const data = node.data;
    
    const date = data.created_at ? new Date(data.created_at).toLocaleDateString() : 'Unknown';
    
    tooltip.style('display', 'block')
        .style('left', `${event.pageX + 10}px`)
        .style('top', `${event.pageY + 10}px`)
        .html(`
            <strong>${data.name}</strong><br>
            <strong>Job ID:</strong> ${data.job_id}<br>
            <strong>Date:</strong> ${date}<br>
            <strong>Papers:</strong> ${data.papers}<br>
            <strong>Gaps:</strong> ${data.gaps}<br>
            <strong>Coverage:</strong> ${Math.round(data.coverage)}%
        `);
}

/**
 * Hide tooltip
 */
function hideTooltip() {
    d3.select('#tooltip').style('display', 'none');
}

/**
 * Render gap reduction line chart
 */
function renderGapReductionChart(timeline) {
    const ctx = document.getElementById('gapReductionChart').getContext('2d');
    
    // Destroy previous chart if exists
    if (gapChart) {
        gapChart.destroy();
    }
    
    const labels = timeline.map(job => {
        const date = job.created_at ? new Date(job.created_at).toLocaleDateString() : 'Unknown';
        return date;
    });
    
    const data = timeline.map(job => job.gap_metrics?.total_gaps || 0);
    
    gapChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Gaps',
                data: data,
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointBackgroundColor: '#dc3545',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Gaps'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });
}

/**
 * Render coverage progress line chart
 */
function renderCoverageProgressChart(timeline) {
    const ctx = document.getElementById('coverageProgressChart').getContext('2d');
    
    // Destroy previous chart if exists
    if (coverageChart) {
        coverageChart.destroy();
    }
    
    const labels = timeline.map(job => {
        const date = job.created_at ? new Date(job.created_at).toLocaleDateString() : 'Unknown';
        return date;
    });
    
    const data = timeline.map(job => job.overall_coverage || 0);
    
    coverageChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Coverage %',
                data: data,
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointBackgroundColor: '#28a745',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `Coverage: ${context.parsed.y.toFixed(1)}%`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Coverage %'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });
}

/**
 * Render table view
 */
function renderTableView(timeline) {
    const tbody = document.querySelector('#genealogy-table tbody');
    tbody.innerHTML = '';
    
    timeline.forEach(job => {
        const date = job.created_at ? new Date(job.created_at).toLocaleDateString() : 'Unknown';
        const row = `
            <tr>
                <td><code>${job.job_id.substring(0, 12)}...</code></td>
                <td>${date}</td>
                <td><span class="badge bg-${job.job_type === 'incremental' ? 'primary' : 'secondary'}">${job.job_type}</span></td>
                <td>${job.papers_analyzed || 0}</td>
                <td>${job.gap_metrics?.total_gaps || 0}</td>
                <td>
                    <div class="progress" style="width: 100px;">
                        <div class="progress-bar ${getCoverageClass(job.overall_coverage)}" 
                             role="progressbar" 
                             style="width: ${job.overall_coverage || 0}%">
                            ${Math.round(job.overall_coverage || 0)}%
                        </div>
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="window.location.href='/?job_id=${job.job_id}#jobDetail'">
                        View
                    </button>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

/**
 * Get coverage progress bar class
 */
function getCoverageClass(coverage) {
    if (coverage >= 90) return 'bg-success';
    if (coverage >= 70) return 'bg-info';
    if (coverage >= 50) return 'bg-warning';
    return 'bg-danger';
}

/**
 * Render timeline view (horizontal timeline)
 */
function renderTimelineView() {
    const container = d3.select('#genealogy-timeline');
    container.html(''); // Clear previous
    
    if (!lineageData || !lineageData.metrics_timeline) {
        container.html('<p class="text-muted text-center">No timeline data available</p>');
        return;
    }
    
    const timeline = lineageData.metrics_timeline;
    const width = 1000;
    const height = 300;
    const margin = { top: 50, right: 90, bottom: 50, left: 90 };
    
    const svg = container
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Draw timeline axis
    const xScale = d3.scaleLinear()
        .domain([0, timeline.length - 1])
        .range([0, width - margin.left - margin.right]);
    
    const yCenter = (height - margin.top - margin.bottom) / 2;
    
    // Draw line
    svg.append('line')
        .attr('x1', 0)
        .attr('x2', width - margin.left - margin.right)
        .attr('y1', yCenter)
        .attr('y2', yCenter)
        .attr('stroke', '#999')
        .attr('stroke-width', 2);
    
    // Draw nodes
    timeline.forEach((job, index) => {
        const x = xScale(index);
        
        const node = svg.append('g')
            .attr('transform', `translate(${x},${yCenter})`)
            .style('cursor', 'pointer')
            .on('click', () => window.location.href = `/?job_id=${job.job_id}#jobDetail`)
            .on('mouseover', function(event) {
                const date = job.created_at ? new Date(job.created_at).toLocaleDateString() : 'Unknown';
                const tooltip = d3.select('#tooltip');
                tooltip.style('display', 'block')
                    .style('left', `${event.pageX + 10}px`)
                    .style('top', `${event.pageY + 10}px`)
                    .html(`
                        <strong>${formatJobName(job.job_id)}</strong><br>
                        <strong>Date:</strong> ${date}<br>
                        <strong>Papers:</strong> ${job.papers_analyzed || 0}<br>
                        <strong>Gaps:</strong> ${job.gap_metrics?.total_gaps || 0}<br>
                        <strong>Coverage:</strong> ${Math.round(job.overall_coverage || 0)}%
                    `);
            })
            .on('mouseout', () => d3.select('#tooltip').style('display', 'none'));
        
        // Circle
        node.append('circle')
            .attr('r', 30)
            .attr('fill', getNodeColor(job))
            .attr('stroke', '#333')
            .attr('stroke-width', 2);
        
        // Label above
        node.append('text')
            .attr('dy', -40)
            .attr('text-anchor', 'middle')
            .text(formatJobName(job.job_id))
            .attr('font-size', '11px')
            .attr('font-weight', 'bold')
            .attr('fill', '#333');
        
        // Coverage inside circle
        node.append('text')
            .attr('dy', 5)
            .attr('text-anchor', 'middle')
            .text(`${Math.round(job.overall_coverage || 0)}%`)
            .attr('font-size', '11px')
            .attr('fill', '#fff')
            .attr('font-weight', 'bold');
    });
}

/**
 * Export visualization as PNG or SVG
 */
function exportVisualization(format) {
    const svg = document.querySelector('#genealogy-tree svg');
    
    if (!svg) {
        alert('No visualization to export');
        return;
    }
    
    if (format === 'svg') {
        // Export as SVG
        const svgData = new XMLSerializer().serializeToString(svg);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `job-genealogy-${Date.now()}.svg`;
        a.click();
        
        URL.revokeObjectURL(url);
    } else if (format === 'png') {
        // Export as PNG using canvas
        const svgData = new XMLSerializer().serializeToString(svg);
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        const img = new Image();
        img.onload = function() {
            canvas.width = svg.clientWidth || 1000;
            canvas.height = svg.clientHeight || 600;
            
            // Fill white background
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.drawImage(img, 0, 0);
            
            canvas.toBlob(function(blob) {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `job-genealogy-${Date.now()}.png`;
                a.click();
                URL.revokeObjectURL(url);
            });
        };
        
        img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
    }
}
