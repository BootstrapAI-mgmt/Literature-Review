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
sudo git clone https://github.com/BootstrapAI-mgmt/Literature-Review.git
sudo chown -R $USER:$USER /opt/Literature-Review
cd /opt/Literature-Review
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
PORT=8000
HOST=127.0.0.1  # Only localhost (Nginx will proxy)

# Dashboard API Key (REQUIRED)
DASHBOARD_API_KEY=your-secure-api-key-here

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
WorkingDirectory=/opt/Literature-Review
EnvironmentFile=/etc/literature-review/production.env

# Use virtual environment Python
ExecStart=/opt/Literature-Review/venv/bin/uvicorn webdashboard.app:app --host 127.0.0.1 --port 8000

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

**Setup directories and permissions:**
```bash
# Create data directories
sudo mkdir -p /var/lib/literature-review/data
sudo mkdir -p /var/lib/literature-review/cache
sudo mkdir -p /var/log/literature-review

# Set ownership
sudo chown -R www-data:www-data /var/lib/literature-review
sudo chown -R www-data:www-data /var/log/literature-review
sudo chown -R www-data:www-data /opt/Literature-Review

# Enable and start
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

    # Proxy to FastAPI app
    location / {
        proxy_pass http://127.0.0.1:8000;
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
        alias /opt/Literature-Review/webdashboard/static/;
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
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DASHBOARD_API_KEY=${DASHBOARD_API_KEY}
    volumes:
      - ./data:/app/data
      - ./workspace:/app/workspace
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
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

### Step 2: Create Environment File

**File:** `.env` (DO NOT COMMIT)

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...
DASHBOARD_API_KEY=your-secure-api-key-here
```

### Step 3: Nginx Configuration for Docker

**File:** `nginx.conf`

```nginx
events {
    worker_connections 1024;
}

http {
    upstream dashboard {
        server dashboard:8000;
    }

    server {
        listen 80;
        server_name literature-review.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name literature-review.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/literature-review.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/literature-review.yourdomain.com/privkey.pem;

        client_max_body_size 100M;

        location / {
            proxy_pass http://dashboard;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

### Step 4: Deploy with Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f dashboard

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

---

## Environment Configuration

### Secrets Management

**Option 1: Environment Variables**
```bash
# .env file (DO NOT COMMIT)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DASHBOARD_API_KEY=your-secure-api-key-here
```

**Option 2: Docker Secrets**
```bash
echo "sk-ant-..." | docker secret create anthropic_api_key -
echo "sk-..." | docker secret create openai_api_key -
```

**Option 3: Vault (Enterprise)**
```bash
vault kv put secret/literature-review \
  anthropic_api_key="sk-ant-..." \
  openai_api_key="sk-..." \
  dashboard_api_key="your-secure-key"
```

### Required Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `DASHBOARD_API_KEY` | Dashboard authentication key | Yes | - |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key | No | - |
| `PORT` | Application port | No | 8000 |
| `HOST` | Bind address | No | 0.0.0.0 |
| `LOG_LEVEL` | Logging level | No | INFO |

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

**Docker logs:**
```bash
docker-compose logs -f dashboard
```

### Metrics

**Prometheus + Grafana:**
```python
# Add to webdashboard/app.py
from prometheus_fastapi_instrumentator import Instrumentator

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

**Install metrics:**
```bash
pip install prometheus-fastapi-instrumentator
```

**Grafana Dashboard:**
- Request rate
- Response time
- Job completion rate
- API cost per day
- Upload success/failure rate

### Alerts

**Example: Disk space alert**

**File:** `/etc/cron.hourly/check-disk`

```bash
#!/bin/bash
USAGE=$(df -h /var/lib/literature-review | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $USAGE -gt 80 ]; then
  echo "Disk usage ${USAGE}% on /var/lib/literature-review" | mail -s "ALERT: Disk Space" admin@example.com
fi
```

Make executable:
```bash
sudo chmod +x /etc/cron.hourly/check-disk
```

---

## Backup Strategy

### Database Backups

**File:** `/usr/local/bin/backup-literature-review.sh`

```bash
#!/bin/bash

BACKUP_DIR="/var/backups/literature-review"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
mkdir -p $BACKUP_DIR
cp /var/lib/literature-review/data/review_log.json $BACKUP_DIR/review_log_$DATE.json
cp -r /var/lib/literature-review/workspace $BACKUP_DIR/workspace_$DATE

# Compress
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz -C $BACKUP_DIR review_log_$DATE.json workspace_$DATE
rm -rf $BACKUP_DIR/review_log_$DATE.json $BACKUP_DIR/workspace_$DATE

# Keep last 30 days
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: backup_$DATE.tar.gz"
```

**Setup:**
```bash
sudo chmod +x /usr/local/bin/backup-literature-review.sh

# Daily backups at 2 AM
sudo crontab -e
# Add:
0 2 * * * /usr/local/bin/backup-literature-review.sh
```

### S3 Sync (AWS)

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Sync backups to S3
aws s3 sync /var/backups/literature-review s3://my-bucket/literature-review-backups/ --delete
```

**Automated S3 backup:**

**File:** `/usr/local/bin/backup-to-s3.sh`

```bash
#!/bin/bash

# Run local backup first
/usr/local/bin/backup-literature-review.sh

# Sync to S3
aws s3 sync /var/backups/literature-review s3://my-bucket/literature-review-backups/ \
  --storage-class STANDARD_IA \
  --delete

echo "S3 sync completed"
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

1. **Missing API keys**
   - Check `/etc/literature-review/production.env`
   - Ensure all required keys are set

2. **Port 8000 in use**
   - Change `PORT` in env file
   - Or find and kill process: `sudo lsof -i :8000`

3. **Permission errors**
   ```bash
   sudo chown -R www-data:www-data /var/lib/literature-review
   sudo chown -R www-data:www-data /opt/Literature-Review
   ```

### High Memory Usage

**Check memory usage:**
```bash
ps aux | grep uvicorn
```

**Restart service:**
```bash
sudo systemctl restart literature-review
```

**Reduce cache:**
```bash
rm -rf /var/lib/literature-review/workspace/uploads/*
rm -rf /var/lib/literature-review/workspace/jobs/*
```

### SSL Certificate Issues

**Renew certificate:**
```bash
sudo certbot renew
sudo systemctl reload nginx
```

**Test SSL configuration:**
```bash
sudo certbot certificates
```

### Nginx 502 Bad Gateway

**Check if dashboard is running:**
```bash
sudo systemctl status literature-review
curl http://127.0.0.1:8000/health
```

**Check Nginx configuration:**
```bash
sudo nginx -t
```

**View Nginx error logs:**
```bash
sudo tail -f /var/log/nginx/literature-review-error.log
```

### Docker Container Issues

**Check container status:**
```bash
docker-compose ps
```

**View container logs:**
```bash
docker-compose logs dashboard
```

**Restart containers:**
```bash
docker-compose restart
```

**Rebuild containers:**
```bash
docker-compose down
docker-compose up -d --build
```

---

## Security Checklist

- [ ] API keys stored in environment variables (not code)
- [ ] HTTPS enabled with valid certificate
- [ ] Strong `DASHBOARD_API_KEY` generated (32+ characters)
- [ ] Firewall configured (only 80/443 open)
- [ ] Regular security updates (`sudo apt update && sudo apt upgrade`)
- [ ] Access logs monitored
- [ ] Backups tested (restore procedure verified)
- [ ] Systemd service hardening enabled (NoNewPrivileges, PrivateTmp)
- [ ] Nginx security headers configured
- [ ] File upload size limits set (`client_max_body_size`)
- [ ] SSH key-based authentication (disable password auth)
- [ ] Fail2ban configured for SSH protection
- [ ] Database backups encrypted
- [ ] Log rotation configured

### Firewall Configuration

**Ubuntu (UFW):**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**RHEL/CentOS (firewalld):**
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Fail2ban Setup

```bash
sudo apt install fail2ban

# Configure jail
sudo nano /etc/fail2ban/jail.local
```

**File:** `/etc/fail2ban/jail.local`

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
```

---

## Performance Optimization

### Gunicorn for Production

For better performance, use Gunicorn with multiple workers:

```bash
pip install gunicorn
```

**Update systemd service:**
```ini
ExecStart=/opt/Literature-Review/venv/bin/gunicorn webdashboard.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 300
```

**Workers calculation:**
```
workers = (CPU cores × 2) + 1
```

### Caching

Enable caching for API responses:

```python
# Install redis
pip install redis

# Use redis for caching
import redis
cache = redis.Redis(host='localhost', port=6379, db=0)
```

---

## Health Checks

### Application Health Endpoint

The dashboard provides a health check endpoint at `/health`:

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-18T17:00:00Z"
}
```

### Monitoring Script

**File:** `/usr/local/bin/health-check.sh`

```bash
#!/bin/bash

HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE != "200" ]; then
    echo "Health check failed! Status: $RESPONSE"
    # Restart service
    sudo systemctl restart literature-review
    # Send alert
    echo "Dashboard health check failed. Service restarted." | mail -s "ALERT: Dashboard Down" admin@example.com
else
    echo "Health check passed"
fi
```

**Schedule:**
```bash
# Every 5 minutes
*/5 * * * * /usr/local/bin/health-check.sh
```

---

## Additional Resources

- [Dashboard User Guide](DASHBOARD_GUIDE.md)
- [Scaling Guide](SCALING_GUIDE.md)
- [Main README](../README.md)
- [User Manual](USER_MANUAL.md)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs (`journalctl -u literature-review`)
3. Open an issue on GitHub
4. Contact system administrator
