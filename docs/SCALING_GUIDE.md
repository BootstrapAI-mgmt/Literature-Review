# Scaling Guide

This guide covers scaling strategies for the Literature Review Dashboard to handle increased load and larger deployments.

---

## Table of Contents

1. [Scaling Overview](#scaling-overview)
2. [Vertical Scaling](#vertical-scaling)
3. [Horizontal Scaling](#horizontal-scaling)
4. [Performance Tuning](#performance-tuning)
5. [Cloud Deployment](#cloud-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)

---

## Scaling Overview

### When to Scale

Scale your deployment when you experience:
- High response times (>2 seconds)
- Memory usage consistently >80%
- CPU usage consistently >70%
- Frequent job queue backlogs
- Multiple concurrent users (>10)

### Scaling Strategies

| Strategy | When to Use | Complexity | Cost |
|----------|-------------|------------|------|
| **Vertical** | Small-medium growth | Low | Medium |
| **Horizontal** | Large-scale, HA required | High | High |
| **Hybrid** | Enterprise deployments | Very High | Very High |

---

## Vertical Scaling

Increase resources on a single server.

### Resource Upgrades

**Small → Medium (10-50 papers, 5 concurrent jobs)**
- CPU: 2 cores → 4 cores
- RAM: 4 GB → 8 GB
- Disk: 50 GB → 100 GB SSD
- Expected capacity: ~50 papers, 10 concurrent jobs

**Medium → Large (50-200 papers, 20 concurrent jobs)**
- CPU: 4 cores → 8 cores
- RAM: 8 GB → 16 GB
- Disk: 100 GB → 200 GB SSD
- Expected capacity: ~200 papers, 20 concurrent jobs

**Large → Enterprise (200-500 papers, 50 concurrent jobs)**
- CPU: 8 cores → 16 cores
- RAM: 16 GB → 32 GB
- Disk: 200 GB → 500 GB SSD
- Expected capacity: ~500 papers, 50 concurrent jobs

### Vertical Scaling Steps

1. **Backup your data**
   ```bash
   /usr/local/bin/backup-literature-review.sh
   ```

2. **Stop the service**
   ```bash
   sudo systemctl stop literature-review
   ```

3. **Upgrade server resources** (cloud provider UI or hardware upgrade)

4. **Verify resources**
   ```bash
   nproc  # CPU cores
   free -h  # RAM
   df -h  # Disk space
   ```

5. **Update worker count** (if using Gunicorn)
   ```bash
   # Edit systemd service
   sudo nano /etc/systemd/system/literature-review.service
   
   # Update workers: (CPU cores × 2) + 1
   ExecStart=/opt/Literature-Review/venv/bin/gunicorn ... --workers 17
   ```

6. **Restart service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start literature-review
   ```

---

## Horizontal Scaling

Deploy multiple instances behind a load balancer.

### Architecture

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │     (Nginx)     │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │  Dashboard  │   │  Dashboard  │   │  Dashboard  │
    │  Instance 1 │   │  Instance 2 │   │  Instance 3 │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                      ┌──────▼──────┐
                      │   Shared    │
                      │   Storage   │
                      │  (NFS/S3)   │
                      └─────────────┘
```

### Load Balancer Setup

**File:** `/etc/nginx/nginx.conf`

```nginx
http {
    upstream dashboard_backend {
        least_conn;  # Route to least busy server
        server 192.168.1.10:8000 max_fails=3 fail_timeout=30s;
        server 192.168.1.11:8000 max_fails=3 fail_timeout=30s;
        server 192.168.1.12:8000 max_fails=3 fail_timeout=30s;
    }

    server {
        listen 80;
        server_name literature-review.yourdomain.com;

        location / {
            proxy_pass http://dashboard_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            
            # Health checks
            proxy_next_upstream error timeout http_502 http_503 http_504;
            proxy_connect_timeout 5s;
        }
    }
}
```

### Shared Storage

**Option 1: NFS (Network File System)**

**On NFS Server:**
```bash
# Install NFS server
sudo apt install nfs-kernel-server

# Create shared directory
sudo mkdir -p /export/literature-review
sudo chown nobody:nogroup /export/literature-review

# Configure exports
sudo nano /etc/exports
# Add:
/export/literature-review 192.168.1.0/24(rw,sync,no_subtree_check)

# Apply changes
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
```

**On Dashboard Instances:**
```bash
# Install NFS client
sudo apt install nfs-common

# Mount shared storage
sudo mkdir -p /var/lib/literature-review
sudo mount 192.168.1.5:/export/literature-review /var/lib/literature-review

# Auto-mount on boot
sudo nano /etc/fstab
# Add:
192.168.1.5:/export/literature-review /var/lib/literature-review nfs defaults 0 0
```

**Option 2: S3-Compatible Storage**

```python
# Install boto3
pip install boto3

# Configure S3 storage using environment variables (recommended)
import boto3
import os

s3 = boto3.client('s3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
)

# Upload/download files
s3.upload_file('local_file.pdf', 'my-bucket', 'remote_file.pdf')
s3.download_file('my-bucket', 'remote_file.pdf', 'local_file.pdf')
```

### Session Management

For sticky sessions (WebSocket support):

```nginx
upstream dashboard_backend {
    ip_hash;  # Same client → same server
    server 192.168.1.10:8000;
    server 192.168.1.11:8000;
    server 192.168.1.12:8000;
}
```

Or use Redis for shared sessions:

```python
# Install redis
pip install redis

# Configure session storage
import redis
session_store = redis.Redis(host='redis-server', port=6379, db=0)
```

---

## Performance Tuning

### 1. Gunicorn Workers

**Optimal worker count:**
```
workers = (CPU cores × 2) + 1
```

**Update systemd service:**
```ini
ExecStart=/opt/Literature-Review/venv/bin/gunicorn webdashboard.app:app \
    --workers 9 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 300 \
    --max-requests 1000 \
    --max-requests-jitter 50
```

### 2. Database Optimization

**Migrate to PostgreSQL for better concurrency:**

```bash
# Install PostgreSQL
sudo apt install postgresql

# Install Python adapter
pip install psycopg2-binary
```

**Connection pooling:**
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/litreview',
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### 3. Caching Strategy

**Add Redis for API caching:**

```bash
# Install Redis
sudo apt install redis-server

# Install Python client
pip install redis
```

**Cache configuration:**
```python
import redis
import hashlib
import json
from functools import wraps

cache = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def cache_response(ttl=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create consistent cache key using hash
            key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
            cache_key = f"{func.__name__}:{hashlib.md5(key_data.encode()).hexdigest()}"
            cached = cache.get(cache_key)
            if cached:
                return cached
            result = func(*args, **kwargs)
            cache.setex(cache_key, ttl, result)
            return result
        return wrapper
    return decorator
```

### 4. Nginx Optimization

```nginx
http {
    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css application/json application/javascript;

    # Connection optimization
    keepalive_timeout 65;
    keepalive_requests 100;

    # Buffer sizes
    client_body_buffer_size 128k;
    client_max_body_size 100M;
    client_header_buffer_size 1k;

    # Worker processes
    worker_processes auto;
    worker_connections 1024;
}
```

### 5. Python Performance

**Enable uvloop for better async performance:**

```bash
pip install uvloop
```

**Update app initialization:**
```python
import uvloop
uvloop.install()
```

---

## Cloud Deployment

### AWS Deployment

**Architecture:**
```
┌─────────────────────────────────────────────┐
│  Route 53 (DNS)                             │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  Application Load Balancer (ALB)            │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────┐
│   EC2       │  │   EC2       │
│  Instance 1 │  │  Instance 2 │
└──────┬──────┘  └──────┬──────┘
       │                │
       └───────┬────────┘
               │
┌──────────────▼──────────────────────────────┐
│  RDS (PostgreSQL) + S3 (File Storage)       │
└─────────────────────────────────────────────┘
```

**Setup steps:**

1. **Create VPC and Subnets**
   ```bash
   aws ec2 create-vpc --cidr-block 10.0.0.0/16
   ```

2. **Launch EC2 instances**
   ```bash
   # Find latest Ubuntu 22.04 AMI for your region
   aws ec2 describe-images \
     --owners 099720109477 \
     --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
     --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
     --output text
   
   # Launch instances using the AMI ID from above
   aws ec2 run-instances \
     --image-id ami-xxxxxxxxxxxxxxxxx \  # Replace with AMI from above command
     --instance-type t3.medium \
     --count 2
   ```

3. **Create Application Load Balancer**
   ```bash
   aws elbv2 create-load-balancer \
     --name literature-review-alb \
     --subnets subnet-xxx subnet-yyy
   ```

4. **Setup RDS**
   ```bash
   aws rds create-db-instance \
     --db-instance-identifier litreview-db \
     --db-instance-class db.t3.small \
     --engine postgres
   ```

### Google Cloud Platform

**Architecture:**
```
Cloud Load Balancer
    │
    ├─ Managed Instance Group
    │  ├─ VM Instance 1
    │  ├─ VM Instance 2
    │  └─ VM Instance 3
    │
    ├─ Cloud SQL (PostgreSQL)
    └─ Cloud Storage (Files)
```

**Deployment:**

1. **Create instance template**
   ```bash
   gcloud compute instance-templates create literature-review-template \
     --machine-type=n1-standard-2 \
     --image-family=ubuntu-2004-lts
   ```

2. **Create managed instance group**
   ```bash
   gcloud compute instance-groups managed create literature-review-group \
     --template=literature-review-template \
     --size=3
   ```

3. **Setup load balancer**
   ```bash
   gcloud compute forwarding-rules create literature-review-lb \
     --target-pool=literature-review-pool
   ```

### Azure Deployment

**Architecture:**
```
Azure Load Balancer
    │
    ├─ VM Scale Set
    │  ├─ VM 1
    │  ├─ VM 2
    │  └─ VM 3
    │
    ├─ Azure Database for PostgreSQL
    └─ Blob Storage
```

---

## Kubernetes Deployment

### Helm Chart

**File:** `helm/literature-review/values.yaml`

```yaml
replicaCount: 3

image:
  repository: your-registry/literature-review
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: literature-review.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

env:
  - name: FLASK_ENV
    value: production
  - name: DASHBOARD_API_KEY
    valueFrom:
      secretKeyRef:
        name: dashboard-secrets
        key: api-key
```

**File:** `helm/literature-review/templates/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "literature-review.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: literature-review
  template:
    metadata:
      labels:
        app: literature-review
    spec:
      containers:
      - name: dashboard
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: 8000
        env:
        {{- range .Values.env }}
        - name: {{ .name }}
          {{- if .value }}
          value: {{ .value }}
          {{- else }}
          valueFrom:
            {{- toYaml .valueFrom | nindent 12 }}
          {{- end }}
        {{- end }}
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace literature-review

# Create secrets
kubectl create secret generic dashboard-secrets \
  --from-literal=api-key=your-secure-key \
  --namespace=literature-review

# Install with Helm
helm install literature-review ./helm/literature-review \
  --namespace=literature-review

# Check status
kubectl get pods -n literature-review

# Scale deployment
kubectl scale deployment literature-review --replicas=5 -n literature-review
```

---

## Monitoring at Scale

### Prometheus + Grafana

**Deploy monitoring stack:**

```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts

# Install Prometheus
helm install prometheus prometheus-community/prometheus

# Install Grafana
helm install grafana grafana/grafana
```

**Key metrics to monitor:**
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (%)
- CPU usage per instance
- Memory usage per instance
- Active jobs
- Queue depth
- API cost per day

---

## Cost Optimization

### Resource Optimization

1. **Auto-scaling policies**
   - Scale down during off-hours
   - Use spot/preemptible instances for non-critical workloads

2. **Storage tiering**
   - Move old reviews to cheaper storage (S3 Glacier, Azure Cool Blob)
   - Archive after 90 days

3. **API cost reduction**
   - Cache API responses
   - Batch requests when possible
   - Use cheaper models for preliminary analysis

### Cost Monitoring

```bash
# AWS Cost Explorer API
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-30 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

---

## Performance Benchmarks

### Expected Performance

| Setup | Papers | Concurrent Jobs | Response Time | Memory | CPU |
|-------|--------|-----------------|---------------|--------|-----|
| **Small** | 0-50 | 1-5 | <1s | 2GB | 40% |
| **Medium** | 50-200 | 5-20 | <2s | 4GB | 60% |
| **Large** | 200-500 | 20-50 | <3s | 8GB | 70% |
| **Enterprise** | 500+ | 50+ | <5s | 16GB+ | 80% |

### Load Testing

**Using Apache Bench:**
```bash
ab -n 1000 -c 10 http://localhost:8000/
```

**Using k6:**
```javascript
import http from 'k6/http';

export default function() {
  http.get('http://localhost:8000/');
}
```

Run test:
```bash
k6 run --vus 10 --duration 30s loadtest.js
```

---

## High Availability

### Multi-Region Deployment

```
         ┌──────────────────┐
         │   Global DNS     │
         │   (Route 53)     │
         └────────┬─────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼─────┐     ┌────▼─────┐
    │ Region 1 │     │ Region 2 │
    │  (Primary)│     │(Failover)│
    └──────────┘     └──────────┘
```

**Health check configuration:**
```bash
# Route 53 health check
aws route53 create-health-check \
  --health-check-config \
    IPAddress=1.2.3.4,Port=443,Type=HTTPS,ResourcePath=/health
```

---

## Additional Resources

- [Production Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Dashboard Guide](DASHBOARD_GUIDE.md)
- [Main README](../README.md)

---

## Support

For scaling assistance:
1. Review this guide
2. Check current resource usage
3. Plan scaling strategy
4. Test in staging environment
5. Monitor post-deployment
