# Client SDK Guide

This guide provides code examples for interacting with the Literature Review Dashboard API using popular programming languages.

---

## Table of Contents

1. [Python Client](#python-client)
2. [JavaScript/Node.js Client](#javascriptnodejs-client)
3. [cURL Examples](#curl-examples)
4. [Postman Collection](#postman-collection)

---

## Python Client

### Installation

```bash
# Install required dependencies
pip install requests websockets
```

### Basic Usage

```python
import requests
import json
from pathlib import Path

class LiteratureReviewClient:
    """Python client for Literature Review Dashboard API"""
    
    def __init__(self, base_url="http://localhost:5001", api_key="dev-key-change-in-production"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-KEY": api_key}
    
    def upload_pdf(self, file_path):
        """Upload a single PDF file"""
        url = f"{self.base_url}/api/upload"
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, headers=self.headers, files=files)
        response.raise_for_status()
        return response.json()
    
    def upload_batch(self, file_paths):
        """Upload multiple PDF files"""
        url = f"{self.base_url}/api/upload/batch"
        files = [('files', open(fp, 'rb')) for fp in file_paths]
        try:
            response = requests.post(url, headers=self.headers, files=files)
            response.raise_for_status()
            return response.json()
        finally:
            for _, f in files:
                f.close()
    
    def confirm_upload(self, job_id, action="skip_duplicates"):
        """Confirm batch upload after duplicate detection"""
        url = f"{self.base_url}/api/upload/confirm"
        data = {"action": action, "job_id": job_id}
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self):
        """List all jobs"""
        url = f"{self.base_url}/api/jobs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_job(self, job_id):
        """Get job details"""
        url = f"{self.base_url}/api/jobs/{job_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def configure_job(self, job_id, pillar_selections=["ALL"], run_mode="ONCE", convergence_threshold=5.0):
        """Configure job parameters"""
        url = f"{self.base_url}/api/jobs/{job_id}/configure"
        data = {
            "pillar_selections": pillar_selections,
            "run_mode": run_mode,
            "convergence_threshold": convergence_threshold
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def start_job(self, job_id):
        """Start job execution"""
        url = f"{self.base_url}/api/jobs/{job_id}/start"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def retry_job(self, job_id, force=False):
        """Retry a failed job"""
        url = f"{self.base_url}/api/jobs/{job_id}/retry"
        data = {"force": force}
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_results(self, job_id):
        """Get list of result files"""
        url = f"{self.base_url}/api/jobs/{job_id}/results"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def download_result_file(self, job_id, file_path, output_path):
        """Download a specific result file"""
        url = f"{self.base_url}/api/jobs/{job_id}/results/{file_path}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
    
    def download_all_results(self, job_id, output_path):
        """Download all results as ZIP"""
        url = f"{self.base_url}/api/jobs/{job_id}/results/download/all"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
    
    def get_proof_scorecard(self, job_id):
        """Get proof scorecard summary"""
        url = f"{self.base_url}/api/jobs/{job_id}/proof-scorecard"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_cost_summary(self, job_id):
        """Get API cost summary"""
        url = f"{self.base_url}/api/jobs/{job_id}/cost-summary"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_sufficiency_summary(self, job_id):
        """Get evidence sufficiency summary"""
        url = f"{self.base_url}/api/jobs/{job_id}/sufficiency-summary"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_progress_history(self, job_id):
        """Get progress history timeline"""
        url = f"{self.base_url}/api/jobs/{job_id}/progress-history"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def compare_jobs(self, job_id_1, job_id_2):
        """Compare two jobs"""
        url = f"{self.base_url}/api/compare-jobs/{job_id_1}/{job_id_2}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_logs(self, job_id, tail=100):
        """Get job logs"""
        url = f"{self.base_url}/api/logs/{job_id}?tail={tail}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def suggest_field(self, papers):
        """Auto-suggest research field"""
        url = f"{self.base_url}/api/suggest-field"
        data = {"papers": papers}
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_field_presets(self):
        """Get all field presets"""
        url = f"{self.base_url}/api/field-presets"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
```

### Example: Complete Workflow

```python
#!/usr/bin/env python3
"""
Example: Complete literature review workflow
"""

from literature_review_client import LiteratureReviewClient
import time

def main():
    # Initialize client
    client = LiteratureReviewClient(
        base_url="http://localhost:5001",
        api_key="dev-key-change-in-production"
    )
    
    # 1. Upload PDFs (batch)
    print("Uploading papers...")
    pdf_files = [
        "papers/paper1.pdf",
        "papers/paper2.pdf",
        "papers/paper3.pdf"
    ]
    upload_result = client.upload_batch(pdf_files)
    
    # 2. Handle duplicates if detected
    if upload_result.get('status') == 'duplicates_found':
        print(f"Found {len(upload_result['duplicates'])} duplicates")
        print("Skipping duplicates...")
        upload_result = client.confirm_upload(
            upload_result['job_id'],
            action='skip_duplicates'
        )
    
    job_id = upload_result['job_id']
    print(f"Job created: {job_id}")
    
    # 3. Configure job
    print("Configuring job...")
    client.configure_job(
        job_id,
        pillar_selections=["ALL"],
        run_mode="ONCE",
        convergence_threshold=5.0
    )
    
    # 4. Start job
    print("Starting job...")
    client.start_job(job_id)
    
    # 5. Monitor progress
    print("Monitoring progress...")
    while True:
        job = client.get_job(job_id)
        status = job['status']
        
        if status == 'completed':
            print("✓ Job completed!")
            break
        elif status == 'failed':
            print("✗ Job failed!")
            print(f"Error: {job.get('error', 'Unknown error')}")
            return
        else:
            if 'progress' in job and job['progress']:
                progress = job['progress'].get('percentage', 0)
                print(f"Progress: {progress:.1f}%")
        
        time.sleep(10)  # Poll every 10 seconds
    
    # 6. Get results
    print("\nFetching results...")
    
    # Proof scorecard
    scorecard = client.get_proof_scorecard(job_id)
    if scorecard['available']:
        print(f"\nProof Readiness Score: {scorecard['overall_score']}")
        print(f"Verdict: {scorecard['verdict']}")
    
    # Cost summary
    cost = client.get_cost_summary(job_id)
    if cost['available']:
        print(f"\nTotal Cost: ${cost['total_cost']:.2f}")
        print(f"Budget Used: {cost['budget_percent']:.1f}%")
    
    # Sufficiency summary
    sufficiency = client.get_sufficiency_summary(job_id)
    if sufficiency['available']:
        print(f"\nEvidence Sufficiency:")
        for quadrant, count in sufficiency['quadrants'].items():
            print(f"  {quadrant}: {count}")
    
    # 7. Download all results
    print("\nDownloading results...")
    client.download_all_results(job_id, f"results_{job_id}.zip")
    print(f"Results saved to results_{job_id}.zip")
    
    # 8. Compare with previous job (if available)
    jobs = client.list_jobs()
    if jobs['count'] >= 2:
        print("\nComparing with previous job...")
        prev_job_id = jobs['jobs'][1]['id']  # Second most recent
        comparison = client.compare_jobs(prev_job_id, job_id)
        
        delta = comparison['delta']
        print(f"Completeness Change: {delta['completeness_change']:+.1f}%")
        print(f"Papers Added: {delta['papers_added_count']}")
        print(f"Gaps Filled: {delta['gaps_filled_count']}")

if __name__ == "__main__":
    main()
```

### WebSocket Integration

```python
import asyncio
import websockets
import json

async def monitor_job_progress(job_id):
    """Monitor job progress via WebSocket"""
    uri = f"ws://localhost:5001/ws/jobs/{job_id}/progress"
    
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.receive()
            data = json.loads(message)
            
            msg_type = data.get('type')
            
            if msg_type == 'initial_status':
                print(f"Job Status: {data['job']['status']}")
            
            elif msg_type == 'progress':
                event = data['event']
                print(f"[{event['stage']}] {event['phase']} - {event.get('percentage', 0):.1f}%")
            
            elif msg_type == 'logs':
                for line in data['lines']:
                    print(line.strip())
            
            elif msg_type == 'job_complete':
                print(f"Job finished: {data['status']}")
                break

# Usage
asyncio.run(monitor_job_progress("550e8400-e29b-41d4-a716-446655440000"))
```

---

## JavaScript/Node.js Client

### Installation

```bash
npm install axios ws
```

### Basic Usage

```javascript
const axios = require('axios');
const WebSocket = require('ws');
const fs = require('fs');
const FormData = require('form-data');

class LiteratureReviewClient {
  constructor(baseURL = 'http://localhost:5001', apiKey = 'dev-key-change-in-production') {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'X-API-KEY': this.apiKey
      }
    });
  }

  async uploadPDF(filePath) {
    const formData = new FormData();
    formData.append('file', fs.createReadStream(filePath));
    
    const response = await this.client.post('/api/upload', formData, {
      headers: formData.getHeaders()
    });
    return response.data;
  }

  async uploadBatch(filePaths) {
    const formData = new FormData();
    filePaths.forEach(path => {
      formData.append('files', fs.createReadStream(path));
    });
    
    const response = await this.client.post('/api/upload/batch', formData, {
      headers: formData.getHeaders()
    });
    return response.data;
  }

  async confirmUpload(jobId, action = 'skip_duplicates') {
    const response = await this.client.post('/api/upload/confirm', {
      action,
      job_id: jobId
    });
    return response.data;
  }

  async listJobs() {
    const response = await this.client.get('/api/jobs');
    return response.data;
  }

  async getJob(jobId) {
    const response = await this.client.get(`/api/jobs/${jobId}`);
    return response.data;
  }

  async configureJob(jobId, config = {}) {
    const defaultConfig = {
      pillar_selections: ['ALL'],
      run_mode: 'ONCE',
      convergence_threshold: 5.0
    };
    
    const response = await this.client.post(
      `/api/jobs/${jobId}/configure`,
      { ...defaultConfig, ...config }
    );
    return response.data;
  }

  async startJob(jobId) {
    const response = await this.client.post(`/api/jobs/${jobId}/start`);
    return response.data;
  }

  async retryJob(jobId, force = false) {
    const response = await this.client.post(`/api/jobs/${jobId}/retry`, { force });
    return response.data;
  }

  async getResults(jobId) {
    const response = await this.client.get(`/api/jobs/${jobId}/results`);
    return response.data;
  }

  async downloadResultFile(jobId, filePath, outputPath) {
    const response = await this.client.get(
      `/api/jobs/${jobId}/results/${filePath}`,
      { responseType: 'arraybuffer' }
    );
    fs.writeFileSync(outputPath, response.data);
  }

  async downloadAllResults(jobId, outputPath) {
    const response = await this.client.get(
      `/api/jobs/${jobId}/results/download/all`,
      { responseType: 'arraybuffer' }
    );
    fs.writeFileSync(outputPath, response.data);
  }

  async getProofScorecard(jobId) {
    const response = await this.client.get(`/api/jobs/${jobId}/proof-scorecard`);
    return response.data;
  }

  async getCostSummary(jobId) {
    const response = await this.client.get(`/api/jobs/${jobId}/cost-summary`);
    return response.data;
  }

  async getSufficiencySummary(jobId) {
    const response = await this.client.get(`/api/jobs/${jobId}/sufficiency-summary`);
    return response.data;
  }

  async getProgressHistory(jobId) {
    const response = await this.client.get(`/api/jobs/${jobId}/progress-history`);
    return response.data;
  }

  async compareJobs(jobId1, jobId2) {
    const response = await this.client.get(`/api/compare-jobs/${jobId1}/${jobId2}`);
    return response.data;
  }

  async getLogs(jobId, tail = 100) {
    const response = await this.client.get(`/api/logs/${jobId}?tail=${tail}`);
    return response.data;
  }

  async suggestField(papers) {
    const response = await axios.post(`${this.baseURL}/api/suggest-field`, { papers });
    return response.data;
  }

  async getFieldPresets() {
    const response = await axios.get(`${this.baseURL}/api/field-presets`);
    return response.data;
  }

  monitorJobProgress(jobId, callbacks = {}) {
    const ws = new WebSocket(`ws://localhost:5001/ws/jobs/${jobId}/progress`);
    
    ws.on('message', (data) => {
      const message = JSON.parse(data);
      
      switch (message.type) {
        case 'initial_status':
          if (callbacks.onStatus) callbacks.onStatus(message.job);
          break;
        
        case 'progress':
          if (callbacks.onProgress) callbacks.onProgress(message.event);
          break;
        
        case 'logs':
          if (callbacks.onLogs) callbacks.onLogs(message.lines);
          break;
        
        case 'job_complete':
          if (callbacks.onComplete) callbacks.onComplete(message.status);
          ws.close();
          break;
      }
    });
    
    ws.on('error', (error) => {
      if (callbacks.onError) callbacks.onError(error);
    });
    
    return ws;
  }
}

module.exports = LiteratureReviewClient;
```

### Example: Complete Workflow

```javascript
const LiteratureReviewClient = require('./literature-review-client');

async function main() {
  // Initialize client
  const client = new LiteratureReviewClient(
    'http://localhost:5001',
    'dev-key-change-in-production'
  );
  
  try {
    // 1. Upload PDFs
    console.log('Uploading papers...');
    const pdfFiles = [
      'papers/paper1.pdf',
      'papers/paper2.pdf',
      'papers/paper3.pdf'
    ];
    
    let uploadResult = await client.uploadBatch(pdfFiles);
    
    // 2. Handle duplicates
    if (uploadResult.status === 'duplicates_found') {
      console.log(`Found ${uploadResult.duplicates.length} duplicates`);
      console.log('Skipping duplicates...');
      uploadResult = await client.confirmUpload(
        uploadResult.job_id,
        'skip_duplicates'
      );
    }
    
    const jobId = uploadResult.job_id;
    console.log(`Job created: ${jobId}`);
    
    // 3. Configure job
    console.log('Configuring job...');
    await client.configureJob(jobId, {
      pillar_selections: ['ALL'],
      run_mode: 'ONCE',
      convergence_threshold: 5.0
    });
    
    // 4. Start job
    console.log('Starting job...');
    await client.startJob(jobId);
    
    // 5. Monitor progress via WebSocket
    console.log('Monitoring progress...');
    
    await new Promise((resolve, reject) => {
      client.monitorJobProgress(jobId, {
        onProgress: (event) => {
          const percentage = event.percentage || 0;
          console.log(`[${event.stage}] ${event.phase} - ${percentage.toFixed(1)}%`);
        },
        
        onLogs: (lines) => {
          lines.forEach(line => console.log(line.trim()));
        },
        
        onComplete: (status) => {
          if (status === 'completed') {
            console.log('✓ Job completed!');
            resolve();
          } else {
            console.log('✗ Job failed!');
            reject(new Error(`Job failed with status: ${status}`));
          }
        },
        
        onError: (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        }
      });
    });
    
    // 6. Get results
    console.log('\nFetching results...');
    
    // Proof scorecard
    const scorecard = await client.getProofScorecard(jobId);
    if (scorecard.available) {
      console.log(`\nProof Readiness Score: ${scorecard.overall_score}`);
      console.log(`Verdict: ${scorecard.verdict}`);
    }
    
    // Cost summary
    const cost = await client.getCostSummary(jobId);
    if (cost.available) {
      console.log(`\nTotal Cost: $${cost.total_cost.toFixed(2)}`);
      console.log(`Budget Used: ${cost.budget_percent.toFixed(1)}%`);
    }
    
    // Sufficiency summary
    const sufficiency = await client.getSufficiencySummary(jobId);
    if (sufficiency.available) {
      console.log('\nEvidence Sufficiency:');
      Object.entries(sufficiency.quadrants).forEach(([quadrant, count]) => {
        console.log(`  ${quadrant}: ${count}`);
      });
    }
    
    // 7. Download results
    console.log('\nDownloading results...');
    await client.downloadAllResults(jobId, `results_${jobId}.zip`);
    console.log(`Results saved to results_${jobId}.zip`);
    
    // 8. Compare with previous job
    const jobs = await client.listJobs();
    if (jobs.count >= 2) {
      console.log('\nComparing with previous job...');
      const prevJobId = jobs.jobs[1].id;
      const comparison = await client.compareJobs(prevJobId, jobId);
      
      const delta = comparison.delta;
      console.log(`Completeness Change: ${delta.completeness_change >= 0 ? '+' : ''}${delta.completeness_change.toFixed(1)}%`);
      console.log(`Papers Added: ${delta.papers_added_count}`);
      console.log(`Gaps Filled: ${delta.gaps_filled_count}`);
    }
    
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

main();
```

---

## cURL Examples

### Upload PDF

```bash
curl -X POST "http://localhost:5001/api/upload" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -F "file=@paper.pdf"
```

### List Jobs

```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs
```

### Get Job Details

```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

### Configure Job

```bash
curl -X POST "http://localhost:5001/api/jobs/550e8400.../configure" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "pillar_selections": ["ALL"],
    "run_mode": "ONCE",
    "convergence_threshold": 5.0
  }'
```

### Start Job

```bash
curl -X POST "http://localhost:5001/api/jobs/550e8400.../start" \
  -H "X-API-KEY: dev-key-change-in-production"
```

### Download All Results

```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../results/download/all \
  -o results.zip
```

---

## Postman Collection

### Import OpenAPI Specification

1. Open Postman
2. Click **Import** button
3. Select **Link** tab
4. Enter: `http://localhost:5001/api/openapi.json`
5. Click **Import**

This will create a complete Postman collection with all endpoints pre-configured.

### Environment Variables

Create a Postman environment with:

```json
{
  "base_url": "http://localhost:5001",
  "api_key": "dev-key-change-in-production",
  "job_id": ""
}
```

Use these variables in requests:
- URL: `{{base_url}}/api/jobs`
- Header: `X-API-KEY: {{api_key}}`

### Collection Variables

Set collection-level variables for reuse:
- `job_id`: Automatically set from upload response
- `file_path`: Path to result file for download

### Example Pre-request Script

```javascript
// Auto-generate job ID from upload response
pm.test("Extract job ID", function() {
  var jsonData = pm.response.json();
  pm.environment.set("job_id", jsonData.job_id);
});
```

### Example Tests

```javascript
// Verify upload success
pm.test("Upload successful", function() {
  pm.response.to.have.status(200);
  pm.expect(pm.response.json()).to.have.property('job_id');
});

// Verify job completed
pm.test("Job completed", function() {
  pm.response.to.have.status(200);
  pm.expect(pm.response.json().status).to.eql('completed');
});
```

---

## Error Handling

### Python

```python
from requests.exceptions import HTTPError

try:
    job = client.get_job(job_id)
except HTTPError as e:
    if e.response.status_code == 404:
        print("Job not found")
    elif e.response.status_code == 401:
        print("Invalid API key")
    else:
        print(f"Error: {e.response.json()['detail']}")
```

### JavaScript

```javascript
try {
  const job = await client.getJob(jobId);
} catch (error) {
  if (error.response) {
    // Server responded with error status
    const status = error.response.status;
    const detail = error.response.data.detail;
    
    if (status === 404) {
      console.log('Job not found');
    } else if (status === 401) {
      console.log('Invalid API key');
    } else {
      console.log(`Error: ${detail}`);
    }
  } else {
    // Network error
    console.error('Network error:', error.message);
  }
}
```

---

## Best Practices

### Retry Logic

```python
import time
from requests.exceptions import HTTPError

def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except HTTPError as e:
            if e.response.status_code >= 500:
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    print(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
            else:
                raise

# Usage
job = retry_with_backoff(lambda: client.get_job(job_id))
```

### Rate Limiting

```javascript
class RateLimiter {
  constructor(requestsPerMinute = 60) {
    this.requestsPerMinute = requestsPerMinute;
    this.queue = [];
  }
  
  async throttle(fn) {
    const now = Date.now();
    this.queue = this.queue.filter(time => now - time < 60000);
    
    if (this.queue.length >= this.requestsPerMinute) {
      const oldestRequest = this.queue[0];
      const waitTime = 60000 - (now - oldestRequest);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    this.queue.push(Date.now());
    return await fn();
  }
}

// Usage
const limiter = new RateLimiter(60);
const job = await limiter.throttle(() => client.getJob(jobId));
```

---

## Support

For issues or questions:
- **API Reference:** See `docs/API_REFERENCE.md`
- **GitHub Issues:** https://github.com/BootstrapAI-mgmt/Literature-Review/issues
- **Documentation:** `/docs` directory

---

**Last Updated:** November 18, 2024
