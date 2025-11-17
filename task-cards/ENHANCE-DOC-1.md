# ENHANCE-DOC-1: Production Deployment Guide

**Status:** BASIC DOCUMENTATION ONLY  
**Priority:** 🟡 Medium  
**Effort Estimate:** 3 hours  
**Category:** Documentation  
**Created:** November 17, 2025  
**Related Docs:** README.md, DASHBOARD_GUIDE.md

---

## 📋 Overview

Create comprehensive deployment guide covering production setup, environment configuration, monitoring, backup strategies, and troubleshooting.

**Current State:**
- ✅ Basic `run_dashboard.sh` for local development
- ✅ Dockerfile for containerization
- ❌ No production deployment guide
- ❌ No Nginx/reverse proxy setup
- ❌ No systemd service configuration
- ❌ No monitoring/alerting guide

**Gap:** Users cannot deploy to production without significant DevOps knowledge.

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Production deployment guide (Nginx + systemd)
- [ ] Docker deployment guide (Docker Compose)
- [ ] Environment configuration (secrets, API keys)
- [ ] Database backup strategy
- [ ] Monitoring setup (logs, metrics)

### Should Have
- [ ] SSL/TLS certificate setup (Let's Encrypt)
- [ ] Firewall configuration
- [ ] Resource requirements (CPU, RAM, disk)
- [ ] Scaling guide (horizontal/vertical)

### Nice to Have
- [ ] Kubernetes deployment (Helm chart)
- [ ] Cloud provider guides (AWS, GCP, Azure)
- [ ] CI/CD pipeline setup
- [ ] High availability configuration

---

## 🛠️ Documentation Content

### 1. Production Deployment Guide

**New File:** `docs/DEPLOYMENT_GUIDE.md`

```markdown
# Production Deployment Guide

This guide covers deploying the Literature Review Dashboard to production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [Nginx + Systemd Deployment](#nginx--systemd-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup Strategy](#backup-strategy)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 50 GB SSD
- OS: Ubuntu 20.04+ / Debian 11+ / RHEL 8+

**Recommended:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 200 GB SSD (for large review collections)
- OS: Ubuntu 22.04 LTS

### Software Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3-pip python3-venv nginx certbot

# RHEL/CentOS
sudo dnf install -y python310 python3-pip nginx certbot
```

---

## Deployment Options

| Option | Pros | Cons | Best For |
|--------|------|------|----------|
| **Nginx + Systemd** | Simple, direct control | Manual updates | Single server deployments |
| **Docker** | Isolation, easy updates | Overhead | Development, staging |
| **Kubernetes** | Auto-scaling, HA | Complex setup | Large-scale production |

---

## Nginx + Systemd Deployment

### Step 1: Clone Repository

```bash
cd /opt
sudo git clone https://github.com/your-org/literature-review.git
sudo chown -R $USER:$USER /opt/literature-review
cd /opt/literature-review
```

### Step 2: Python Virtual Environment

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dashboard.txt
```

### Step 3: Environment Configuration

```bash
# Create production config
sudo mkdir -p /etc/literature-review
sudo nano /etc/literature-review/production.env
```

**File:** `/etc/literature-review/production.env`

```bash
# API Keys (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...
SEMANTIC_SCHOLAR_API_KEY=...

# Application Settings
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=$(openssl rand -hex 32)  # Generate secure key
PORT=5001
HOST=127.0.0.1  # Only localhost (Nginx will proxy)

# Database
DATABASE_PATH=/var/lib/literature-review/data/review_log.json
CACHE_DIR=/var/lib/literature-review/cache

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/literature-review/dashboard.log
```

### Step 4: Create Systemd Service

**File:** `/etc/systemd/system/literature-review.service`

```ini
[Unit]
Description=Literature Review Dashboard
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/literature-review
EnvironmentFile=/etc/literature-review/production.env

# Use virtual environment Python
ExecStart=/opt/literature-review/venv/bin/python webdashboard/app.py

# Restart policy
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/var/lib/literature-review /var/log/literature-review

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=literature-review

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable literature-review
sudo systemctl start literature-review
sudo systemctl status literature-review
```

### Step 5: Nginx Reverse Proxy

**File:** `/etc/nginx/sites-available/literature-review`

```nginx
server {
    listen 80;
    server_name literature-review.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name literature-review.yourdomain.com;

    # SSL Certificates (from Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/literature-review.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/literature-review.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    # Max upload size (for PDFs)
    client_max_body_size 100M;

    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;  # Long for job execution
    }

    # Static files (if any)
    location /static/ {
        alias /opt/literature-review/webdashboard/static/;
        expires 1y;
        access_log off;
    }

    # Logging
    access_log /var/log/nginx/literature-review-access.log;
    error_log /var/log/nginx/literature-review-error.log;
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/literature-review /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

### Step 6: SSL Certificate (Let's Encrypt)

```bash
# Obtain certificate
sudo certbot --nginx -d literature-review.yourdomain.com

# Auto-renewal (cron job)
sudo crontab -e
# Add:
0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

---

## Docker Deployment

### Step 1: Docker Compose Setup

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: literature-review-dashboard
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: literature-review-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - dashboard
    restart: unless-stopped
```

**Start:**
```bash
docker-compose up -d
docker-compose logs -f dashboard
```

---

## Environment Configuration

### Secrets Management

**Option 1: Environment Variables**
```bash
# .env file (DO NOT COMMIT)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

**Option 2: Docker Secrets**
```bash
echo "sk-ant-..." | docker secret create anthropic_api_key -
```

**Option 3: Vault (Enterprise)**
```bash
vault kv put secret/literature-review \
  anthropic_api_key="sk-ant-..." \
  openai_api_key="sk-..."
```

---

## Monitoring & Logging

### Application Logs

**Systemd logs:**
```bash
sudo journalctl -u literature-review -f
```

**File logs:**
```bash
tail -f /var/log/literature-review/dashboard.log
```

### Metrics

**Prometheus + Grafana:**
```python
# Add to webdashboard/app.py
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)
```

**Grafana Dashboard:**
- Request rate
- Response time
- Job completion rate
- API cost per day

### Alerts

**Example: Disk space alert**
```bash
# /etc/cron.hourly/check-disk
#!/bin/bash
USAGE=$(df -h /var/lib/literature-review | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $USAGE -gt 80 ]; then
  echo "Disk usage ${USAGE}% on /var/lib/literature-review" | mail -s "ALERT: Disk Space" admin@example.com
fi
```

---

## Backup Strategy

### Database Backups

```bash
# Backup script: /usr/local/bin/backup-literature-review.sh
#!/bin/bash

BACKUP_DIR="/var/backups/literature-review"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
mkdir -p $BACKUP_DIR
cp /var/lib/literature-review/data/review_log.json $BACKUP_DIR/review_log_$DATE.json
cp -r /var/lib/literature-review/cache $BACKUP_DIR/cache_$DATE

# Compress
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*
rm -rf $BACKUP_DIR/*_$DATE.*

# Keep last 30 days
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: backup_$DATE.tar.gz"
```

**Schedule:**
```bash
# Daily backups at 2 AM
sudo crontab -e
0 2 * * * /usr/local/bin/backup-literature-review.sh
```

### S3 Sync (AWS)

```bash
# Sync backups to S3
aws s3 sync /var/backups/literature-review s3://my-bucket/literature-review-backups/ --delete
```

---

## Troubleshooting

### Dashboard Not Starting

**Check systemd status:**
```bash
sudo systemctl status literature-review
sudo journalctl -u literature-review -n 50
```

**Common issues:**
- Missing API keys → Check `/etc/literature-review/production.env`
- Port 5001 in use → Change `PORT` in env file
- Permission errors → `sudo chown -R www-data:www-data /var/lib/literature-review`

### High Memory Usage

**Restart service:**
```bash
sudo systemctl restart literature-review
```

**Reduce cache:**
```bash
rm -rf /var/lib/literature-review/cache/*
```

### SSL Certificate Issues

**Renew certificate:**
```bash
sudo certbot renew
sudo systemctl reload nginx
```

---

## Security Checklist

- [ ] API keys stored in environment variables (not code)
- [ ] HTTPS enabled with valid certificate
- [ ] Firewall configured (only 80/443 open)
- [ ] Regular security updates (`sudo apt update && sudo apt upgrade`)
- [ ] Access logs monitored
- [ ] Backups tested (restore procedure verified)
```

---

## 📚 Additional Documentation

**File:** `docs/SCALING_GUIDE.md`

**New Content:**
```markdown
# Scaling Guide

## Vertical Scaling (Increase Resources)

- Upgrade server: 4 cores → 8 cores, 8 GB → 16 GB RAM
- SSD: 200 GB → 500 GB
- Expected capacity: ~500 papers, 100 concurrent jobs

## Horizontal Scaling (Multiple Servers)

### Load Balancer Setup

**Nginx load balancer:**
```nginx
upstream dashboard_backend {
    server 192.168.1.10:5001;
    server 192.168.1.11:5001;
    server 192.168.1.12:5001;
}

server {
    location / {
        proxy_pass http://dashboard_backend;
    }
}
```

### Shared Storage

- Use NFS for shared `/var/lib/literature-review`
- Or use S3-compatible object storage

## Performance Tuning

- **Gunicorn workers:** `workers = (CPU cores * 2) + 1`
- **Database:** Migrate to PostgreSQL for better concurrency
- **Cache:** Add Redis for session/API cache
```

---

## ✅ Definition of Done

- [ ] `DEPLOYMENT_GUIDE.md` created (comprehensive production setup)
- [ ] Nginx configuration example included
- [ ] Systemd service file included
- [ ] Docker Compose configuration included
- [ ] SSL/TLS setup guide (Let's Encrypt)
- [ ] Environment configuration documented
- [ ] Backup strategy documented (scripts included)
- [ ] Monitoring setup guide (logs, metrics, alerts)
- [ ] Troubleshooting section (common issues)
- [ ] Security checklist included
- [ ] `SCALING_GUIDE.md` created (horizontal/vertical scaling)
- [ ] Resource requirements documented
- [ ] Code review approved
- [ ] Merged to main branch
