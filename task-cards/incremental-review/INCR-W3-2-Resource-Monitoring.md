# INCR-W3-2: Dashboard Resource Monitoring

**Wave:** 3 (User Experience)  
**Priority:** 🟠 High (from parity roadmap)  
**Effort:** 4-6 hours  
**Status:** 🟢 Ready  
**Assignable:** Full-Stack Developer

---

## Overview

Add real-time CPU/Memory monitoring to the dashboard, showing resource usage during job execution. Helps users understand performance bottlenecks and optimize analysis settings.

---

## Dependencies

**Prerequisites:** None (independent UX enhancement)

---

## Scope

### Included
- [x] Backend API for system metrics
- [x] Real-time monitoring panel (WebSocket updates)
- [x] CPU/Memory/Disk usage graphs
- [x] Alerts on high resource usage (>80%)
- [x] Historical metrics (last 24h)
- [x] Per-job resource tracking

### Excluded
- ❌ GPU monitoring (future enhancement)
- ❌ Distributed system monitoring
- ❌ Custom alert rules (fixed threshold only)

---

## Implementation

### Backend API

Create `webdashboard/api/system_metrics.py`:

```python
"""System metrics API for resource monitoring."""

import psutil
import time
from flask import Blueprint, jsonify
from flask_socketio import emit

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/system')

@metrics_bp.route('/metrics', methods=['GET'])
def get_system_metrics():
    """Get current system metrics."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return jsonify({
        'timestamp': time.time(),
        'cpu': {
            'percent': cpu_percent,
            'count': psutil.cpu_count()
        },
        'memory': {
            'total': memory.total,
            'used': memory.used,
            'percent': memory.percent
        },
        'disk': {
            'total': disk.total,
            'used': disk.used,
            'percent': disk.percent
        }
    })

# WebSocket for real-time updates
def emit_metrics_update():
    """Emit metrics every 5 seconds."""
    while True:
        metrics = get_system_metrics().json
        emit('metrics_update', metrics, broadcast=True, namespace='/monitor')
        time.sleep(5)
```

### Frontend Component

```javascript
// static/js/resource_monitor.js

class ResourceMonitor {
    constructor() {
        this.socket = io('/monitor');
        this.charts = {};
        
        this.initCharts();
        this.initWebSocket();
    }
    
    initCharts() {
        // CPU Chart
        this.charts.cpu = new Chart(
            document.getElementById('cpuChart'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU %',
                        data: [],
                        borderColor: '#007bff',
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { min: 0, max: 100 } }
                }
            }
        );
        
        // Memory Chart
        this.charts.memory = new Chart(
            document.getElementById('memoryChart'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Memory %',
                        data: [],
                        borderColor: '#28a745',
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { min: 0, max: 100 } }
                }
            }
        );
    }
    
    initWebSocket() {
        this.socket.on('metrics_update', (metrics) => {
            this.updateCharts(metrics);
            this.checkAlerts(metrics);
        });
    }
    
    updateCharts(metrics) {
        const now = new Date().toLocaleTimeString();
        
        // Update CPU
        this.charts.cpu.data.labels.push(now);
        this.charts.cpu.data.datasets[0].data.push(metrics.cpu.percent);
        
        // Keep only last 20 data points
        if (this.charts.cpu.data.labels.length > 20) {
            this.charts.cpu.data.labels.shift();
            this.charts.cpu.data.datasets[0].data.shift();
        }
        
        this.charts.cpu.update();
        
        // Update Memory
        this.charts.memory.data.labels.push(now);
        this.charts.memory.data.datasets[0].data.push(metrics.memory.percent);
        
        if (this.charts.memory.data.labels.length > 20) {
            this.charts.memory.data.labels.shift();
            this.charts.memory.data.datasets[0].data.shift();
        }
        
        this.charts.memory.update();
    }
    
    checkAlerts(metrics) {
        const alertDiv = document.getElementById('resourceAlerts');
        
        if (metrics.cpu.percent > 80 || metrics.memory.percent > 80) {
            alertDiv.innerHTML = `
                <div class="alert alert-warning">
                    ⚠ High resource usage detected!
                    CPU: ${metrics.cpu.percent}%, Memory: ${metrics.memory.percent}%
                </div>
            `;
        } else {
            alertDiv.innerHTML = '';
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new ResourceMonitor();
});
```

---

## UI Mockup

```
┌──────────────────────────────────────────────────────────┐
│  System Resources                           [Refresh ↻]  │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Current Usage:                                           │
│  ┌────────────┬────────────┬────────────┐                │
│  │ CPU        │ Memory     │ Disk       │                │
│  │ 45%        │ 62%        │ 78%        │                │
│  │ ████░░░░░░ │ ██████░░░░ │ ███████░░░ │                │
│  └────────────┴────────────┴────────────┘                │
│                                                            │
│  📊 CPU Usage (Last 5 Minutes):                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ %                                                   │  │
│  │100┤                                                 │  │
│  │ 80┤                        ●                        │  │
│  │ 60┤                  ●───●   ●                      │  │
│  │ 40┤            ●───●             ●───●             │  │
│  │ 20┤      ●───●                                      │  │
│  │  0└─────────────────────────────────────────────── │  │
│  │    10:00  10:01  10:02  10:03  10:04  10:05        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  📊 Memory Usage (Last 5 Minutes):                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ %                                                   │  │
│  │100┤                                                 │  │
│  │ 80┤                                                 │  │
│  │ 60┤●────●────●────●────●────●                      │  │
│  │ 40┤                                                 │  │
│  │ 20┤                                                 │  │
│  │  0└─────────────────────────────────────────────── │  │
│  │    10:00  10:01  10:02  10:03  10:04  10:05        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  ⚠ Alerts:                                                │
│  (None - system running normally)                         │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

---

## Deliverables

- [ ] Backend metrics API
- [ ] WebSocket real-time updates
- [ ] Frontend monitoring panel
- [ ] CPU/Memory/Disk charts
- [ ] Alert system (>80% threshold)
- [ ] Integration with dashboard layout
- [ ] Unit tests

---

## Success Criteria

✅ **Functional:**
- Real-time metrics displayed
- Charts update every 5 seconds
- Alerts trigger at 80% usage
- No performance impact on jobs

✅ **UX:**
- Clear visual feedback
- Minimal dashboard space
- Mobile-responsive

✅ **Performance:**
- <1% overhead from monitoring
- WebSocket stable (no disconnects)

---

**Status:** 🟢 Ready  
**Assignee:** TBD  
**Estimated Start:** Week 3, Day 3  
**Estimated Completion:** Week 3, Day 4
