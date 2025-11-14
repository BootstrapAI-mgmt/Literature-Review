# Dockerfile for Literature Review Web Dashboard
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements-dev.txt requirements-dashboard.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dashboard.txt

# Copy application code
COPY webdashboard/ ./webdashboard/
COPY literature_review/ ./literature_review/
COPY pipeline_config.json ./
COPY pillar_definitions.json ./

# Create workspace directory
RUN mkdir -p /app/workspace/uploads /app/workspace/jobs /app/workspace/status /app/workspace/logs

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DASHBOARD_API_KEY=change-me-in-production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "webdashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
