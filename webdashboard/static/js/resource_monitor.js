// Resource Monitor - Real-time system metrics monitoring
// Displays CPU, Memory, and Disk usage with charts and alerts

class ResourceMonitor {
    constructor() {
        this.socket = null;
        this.charts = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3 seconds
        
        this.initCharts();
        this.initWebSocket();
    }
    
    initCharts() {
        // CPU Chart
        const cpuCtx = document.getElementById('cpuChart');
        if (cpuCtx) {
            this.charts.cpu = new Chart(cpuCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU %',
                        data: [],
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            min: 0,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'CPU: ' + context.parsed.y.toFixed(1) + '%';
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Memory Chart
        const memoryCtx = document.getElementById('memoryChart');
        if (memoryCtx) {
            this.charts.memory = new Chart(memoryCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Memory %',
                        data: [],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            min: 0,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'Memory: ' + context.parsed.y.toFixed(1) + '%';
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    
    initWebSocket() {
        // Determine WebSocket protocol based on page protocol
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/system/ws/monitor`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('Resource monitor WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };
            
            this.socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                if (message.type === 'metrics_update') {
                    this.updateMetrics(message.data);
                }
            };
            
            this.socket.onerror = (error) => {
                console.error('Resource monitor WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
            this.socket.onclose = () => {
                console.log('Resource monitor WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.updateConnectionStatus(false);
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.initWebSocket();
            }, this.reconnectDelay);
        } else {
            console.error('Max reconnect attempts reached. Please refresh the page.');
        }
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('monitorConnectionStatus');
        if (statusElement) {
            if (connected) {
                statusElement.className = 'badge bg-success';
                statusElement.textContent = 'Connected';
            } else {
                statusElement.className = 'badge bg-danger';
                statusElement.textContent = 'Disconnected';
            }
        }
    }
    
    updateMetrics(metrics) {
        // Update current usage displays
        this.updateCurrentUsage(metrics);
        
        // Update charts
        this.updateCharts(metrics);
        
        // Check for alerts
        this.checkAlerts(metrics);
    }
    
    updateCurrentUsage(metrics) {
        // CPU
        const cpuPercent = document.getElementById('cpuPercent');
        const cpuBar = document.getElementById('cpuBar');
        if (cpuPercent && cpuBar) {
            const cpu = metrics.cpu.percent.toFixed(1);
            cpuPercent.textContent = `${cpu}%`;
            cpuBar.style.width = `${cpu}%`;
            cpuBar.className = `progress-bar ${this.getProgressBarClass(cpu)}`;
        }
        
        // Memory
        const memoryPercent = document.getElementById('memoryPercent');
        const memoryBar = document.getElementById('memoryBar');
        if (memoryPercent && memoryBar) {
            const memory = metrics.memory.percent.toFixed(1);
            memoryPercent.textContent = `${memory}%`;
            memoryBar.style.width = `${memory}%`;
            memoryBar.className = `progress-bar ${this.getProgressBarClass(memory)}`;
        }
        
        // Disk
        const diskPercent = document.getElementById('diskPercent');
        const diskBar = document.getElementById('diskBar');
        if (diskPercent && diskBar) {
            const disk = metrics.disk.percent.toFixed(1);
            diskPercent.textContent = `${disk}%`;
            diskBar.style.width = `${disk}%`;
            diskBar.className = `progress-bar ${this.getProgressBarClass(disk)}`;
        }
        
        // Update detailed metrics
        const cpuCores = document.getElementById('cpuCores');
        if (cpuCores) {
            cpuCores.textContent = `${metrics.cpu.count} cores`;
        }
        
        const memoryUsed = document.getElementById('memoryUsed');
        if (memoryUsed) {
            const usedGB = (metrics.memory.used / (1024**3)).toFixed(1);
            const totalGB = (metrics.memory.total / (1024**3)).toFixed(1);
            memoryUsed.textContent = `${usedGB} / ${totalGB} GB`;
        }
        
        const diskUsed = document.getElementById('diskUsed');
        if (diskUsed) {
            const usedGB = (metrics.disk.used / (1024**3)).toFixed(1);
            const totalGB = (metrics.disk.total / (1024**3)).toFixed(1);
            diskUsed.textContent = `${usedGB} / ${totalGB} GB`;
        }
    }
    
    getProgressBarClass(percentage) {
        if (percentage >= 90) return 'bg-danger';
        if (percentage >= 80) return 'bg-warning';
        return 'bg-success';
    }
    
    updateCharts(metrics) {
        const now = new Date().toLocaleTimeString();
        
        // Update CPU Chart
        if (this.charts.cpu) {
            this.charts.cpu.data.labels.push(now);
            this.charts.cpu.data.datasets[0].data.push(metrics.cpu.percent);
            
            // Keep only last 20 data points
            if (this.charts.cpu.data.labels.length > 20) {
                this.charts.cpu.data.labels.shift();
                this.charts.cpu.data.datasets[0].data.shift();
            }
            
            this.charts.cpu.update('none'); // Update without animation for performance
        }
        
        // Update Memory Chart
        if (this.charts.memory) {
            this.charts.memory.data.labels.push(now);
            this.charts.memory.data.datasets[0].data.push(metrics.memory.percent);
            
            // Keep only last 20 data points
            if (this.charts.memory.data.labels.length > 20) {
                this.charts.memory.data.labels.shift();
                this.charts.memory.data.datasets[0].data.shift();
            }
            
            this.charts.memory.update('none');
        }
    }
    
    checkAlerts(metrics) {
        const alertDiv = document.getElementById('resourceAlerts');
        if (!alertDiv) return;
        
        const alerts = [];
        
        if (metrics.cpu.percent > 80) {
            alerts.push({
                type: 'warning',
                icon: '⚠️',
                message: `High CPU usage: ${metrics.cpu.percent.toFixed(1)}%`
            });
        }
        
        if (metrics.memory.percent > 80) {
            alerts.push({
                type: 'warning',
                icon: '⚠️',
                message: `High memory usage: ${metrics.memory.percent.toFixed(1)}%`
            });
        }
        
        if (metrics.disk.percent > 80) {
            alerts.push({
                type: 'warning',
                icon: '💾',
                message: `High disk usage: ${metrics.disk.percent.toFixed(1)}%`
            });
        }
        
        // Display alerts
        if (alerts.length > 0) {
            alertDiv.innerHTML = alerts.map(alert => `
                <div class="alert alert-warning alert-dismissible fade show" role="alert">
                    ${alert.icon} <strong>${alert.message}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `).join('');
        } else {
            alertDiv.innerHTML = '';
        }
    }
    
    destroy() {
        // Clean up when component is destroyed
        if (this.socket) {
            this.socket.close();
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
    }
}

// Initialize resource monitor when DOM is ready
let resourceMonitor = null;

document.addEventListener('DOMContentLoaded', () => {
    // Check if resource monitor container exists
    const monitorContainer = document.getElementById('resourceMonitorContainer');
    
    if (monitorContainer) {
        resourceMonitor = new ResourceMonitor();
        
        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            if (resourceMonitor) {
                resourceMonitor.destroy();
            }
        });
    }
});
