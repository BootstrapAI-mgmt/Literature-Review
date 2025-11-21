"""System metrics API for resource monitoring."""

import asyncio
import time
from typing import Dict

import psutil
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/metrics")
async def get_system_metrics() -> Dict:
    """
    Get current system metrics.
    
    Returns real-time CPU, memory, and disk usage statistics.
    
    **Returns:**
    - timestamp: Current Unix timestamp
    - cpu: CPU usage information
      - percent: Overall CPU usage percentage (0-100)
      - count: Number of CPU cores
    - memory: Memory usage information
      - total: Total system memory in bytes
      - used: Used memory in bytes
      - percent: Memory usage percentage (0-100)
    - disk: Disk usage information
      - total: Total disk space in bytes
      - used: Used disk space in bytes
      - percent: Disk usage percentage (0-100)
    
    **Example Response:**
    ```json
    {
      "timestamp": 1700123456.789,
      "cpu": {
        "percent": 45.2,
        "count": 8
      },
      "memory": {
        "total": 16777216000,
        "used": 10485760000,
        "percent": 62.5
      },
      "disk": {
        "total": 500000000000,
        "used": 390000000000,
        "percent": 78.0
      }
    }
    ```
    
    **Note:** This endpoint does not require API key authentication.
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
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
    }


@router.websocket("/ws/monitor")
async def websocket_metrics_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time system metrics updates.
    
    Streams system metrics every 5 seconds to connected clients.
    
    **Message Format:**
    ```json
    {
      "type": "metrics_update",
      "data": {
        "timestamp": 1700123456.789,
        "cpu": {...},
        "memory": {...},
        "disk": {...}
      }
    }
    ```
    
    **Connection:**
    ```javascript
    const socket = new WebSocket('ws://localhost:8000/api/system/ws/monitor');
    socket.onmessage = (event) => {
      const update = JSON.parse(event.data);
      console.log('Metrics:', update.data);
    };
    ```
    """
    await websocket.accept()
    
    try:
        while True:
            # Get current metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
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
            }
            
            # Send metrics to client
            await websocket.send_json({
                'type': 'metrics_update',
                'data': metrics
            })
            
            # Wait 5 seconds before next update
            await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        # Log unexpected errors for debugging
        import logging
        logging.getLogger(__name__).error(f"Error in metrics WebSocket: {e}")
