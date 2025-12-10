# 🔄 N8N Documentation Staleness Review Blueprint

> **Purpose:** Extend the documentation automation chain with proactive staleness detection, enabling domain agents to periodically audit their documentation against repository changes—even when no explicit update request has been made.

---

## 📋 Executive Summary

This enhancement adds a **5th workflow** to the existing n8n Documentation Chain that:

1. **Schedules periodic reviews** for each documentation domain
2. **Detects dormant domains** that haven't been updated recently
3. **Analyzes repository changes** since the domain's last activity
4. **Assesses staleness** using AI to compare docs against code evolution
5. **Routes findings** to the existing Task Distributor for updates or human review

**Goal:** Ensure documentation doesn't silently drift out of sync with the codebase, even when development activity focuses on other areas.

---

## 🏗️ System Architecture

### Integration with Existing Chain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXISTING DOCUMENTATION CHAIN                        │
│                                                                              │
│  ┌─────────────┐     ┌─────────────────┐     ┌──────────────┐              │
│  │  GitHub     │────▶│  Doc Chain -    │────▶│  Doc Chain - │              │
│  │  Webhook    │     │  Trigger        │     │  Distributor │◀─────────┐   │
│  └─────────────┘     └─────────────────┘     └──────┬───────┘          │   │
│                                                     │                   │   │
│                                                     ▼                   │   │
│                                              ┌──────────────┐          │   │
│                                              │  Doc Chain - │          │   │
│                                              │  Agent       │          │   │
│                                              └──────────────┘          │   │
└──────────────────────────────────────────────────────────────────────────┼──┘
                                                                           │
                          ┌────────────────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────────────────────┐
│                         │    NEW: Doc Chain - Staleness Review              │
│                         │                                                    │
│  ┌─────────────────┐    │    ┌─────────────────┐    ┌────────────────────┐  │
│  │ Schedule Trigger│────┼───▶│ Domain Scanner  │───▶│ Change Aggregator  │  │
│  │ (Cron: Weekly)  │    │    │                 │    │                    │  │
│  └─────────────────┘    │    └─────────────────┘    └─────────┬──────────┘  │
│                         │                                      │             │
│                         │                                      ▼             │
│  ┌─────────────────┐    │    ┌─────────────────────────────────────────────┐│
│  │ Manual Trigger  │────┘    │        Staleness Assessment Agent           ││
│  │ (Webhook)       │         │  • Fetch domain docs                        ││
│  └─────────────────┘         │  • Compare against recent changes           ││
│                              │  • Score staleness likelihood               ││
│                              │  • Generate update recommendations          ││
│                              └────────────────────────────────────┬────────┘│
│                                                                   │         │
│                                      ┌────────────────────────────┘         │
│                                      ▼                                      │
│                         ┌─────────────────────────────────────────────┐     │
│                         │              Decision Router                │     │
│                         │                                             │     │
│                         │  staleness > 0.5  ──▶ Task Distributor     ─┼─────┘
│                         │  staleness > 0.3  ──▶ Create GitHub Issue   │
│                         │  staleness ≤ 0.3  ──▶ Log & Exit            │
│                         └─────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Flow Diagram

```
                    ┌─────────────────────────┐
                    │    CRON: Every Sunday   │
                    │    2:00 AM UTC          │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   Load Staleness Config │
                    │   from matrix.json      │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   For Each Domain in    │
                    │   owner_domains         │◀──────────────────┐
                    └───────────┬─────────────┘                   │
                                │                                  │
                                ▼                                  │
                    ┌─────────────────────────┐                   │
                    │   Get Last Activity     │                   │
                    │   (GitHub API)          │                   │
                    └───────────┬─────────────┘                   │
                                │                                  │
                                ▼                                  │
                    ┌─────────────────────────┐                   │
                    │   Days Since Activity   │                   │
                    │   > review_interval?    │                   │
                    └───────────┬─────────────┘                   │
                                │                                  │
                    ┌───────────┴───────────┐                     │
                   No                      Yes                    │
                    │                       │                     │
                    ▼                       ▼                     │
              ┌──────────┐    ┌─────────────────────────┐        │
              │   Skip   │    │  Fetch Repository       │        │
              │   Domain │    │  Changes Since Last     │        │
              └──────────┘    │  Domain Activity        │        │
                    │         └───────────┬─────────────┘        │
                    │                     │                       │
                    │                     ▼                       │
                    │         ┌─────────────────────────┐        │
                    │         │  Filter to Relevant     │        │
                    │         │  Changes (scripts,      │        │
                    │         │  dependencies, etc.)    │        │
                    │         └───────────┬─────────────┘        │
                    │                     │                       │
                    │                     ▼                       │
                    │         ┌─────────────────────────┐        │
                    │         │  AI: Staleness          │        │
                    │         │  Assessment Agent       │        │
                    │         └───────────┬─────────────┘        │
                    │                     │                       │
                    │                     ▼                       │
                    │         ┌─────────────────────────┐        │
                    │         │  staleness_score > 0.5? │        │
                    │         └───────────┬─────────────┘        │
                    │                     │                       │
                    │         ┌───────────┴───────────┐          │
                    │        Yes                      No         │
                    │         │                       │          │
                    │         ▼                       ▼          │
                    │  ┌──────────────┐    ┌──────────────────┐  │
                    │  │ Send Tasks   │    │ staleness > 0.3? │  │
                    │  │ to Distrib.  │    └────────┬─────────┘  │
                    │  └──────────────┘             │            │
                    │                    ┌──────────┴──────────┐ │
                    │                   Yes                    No│
                    │                    │                      ││
                    │                    ▼                      ▼│
                    │         ┌──────────────────┐    ┌─────────┐│
                    │         │ Create GitHub    │    │ Log OK  ││
                    │         │ Issue for Review │    │         ││
                    │         └──────────────────┘    └─────────┘│
                    │                    │                      ││
                    └────────────────────┴──────────────────────┼┘
                                                                │
                                         ┌──────────────────────┘
                                         ▼
                              ┌──────────────────────┐
                              │   More Domains?      │
                              └──────────┬───────────┘
                                         │
                                 ┌───────┴───────┐
                                Yes              No
                                 │                │
                                 │                ▼
                                 │     ┌──────────────────────┐
                                 │     │   Generate Weekly    │
                                 │     │   Digest Report      │
                                 │     └──────────────────────┘
                                 │                │
                                 └────────────────┴─────▶ [End]
```

---

## 📊 Data Structures

### Enhanced Documentation Matrix Schema

Add these new fields to `docs/documentation_matrix.json`:

```json
{
  "version": "1.1",
  "last_updated": "2025-12-10",
  
  "staleness_config": {
    "enabled": true,
    "default_review_interval_days": 7,
    "max_inactivity_before_alert_days": 21,
    "thresholds": {
      "auto_update": 0.7,
      "manual_review": 0.5,
      "create_issue": 0.3,
      "healthy": 0.0
    },
    "ignore_patterns": [
      "test_*.py",
      "tests/**",
      ".github/workflows/**",
      "*.md"
    ],
    "schedule": {
      "frequency": "weekly",
      "day": "sunday",
      "hour_utc": 2,
      "stagger_domains": true
    },
    "notifications": {
      "create_github_issues": true,
      "issue_labels": ["documentation", "staleness-review", "automated"],
      "digest_enabled": true,
      "digest_channel": "github-issue"
    }
  },
  
  "owner_domains": {
    "@core": {
      "documents": ["README.md", "docs/USER_MANUAL.md"],
      "review_interval_days": 7,
      "priority": "high",
      "stagger_day": "monday"
    },
    "@dashboard": {
      "documents": ["docs/DASHBOARD_GUIDE.md", "docs/DASHBOARD_CLI_PARITY.md"],
      "review_interval_days": 7,
      "priority": "high",
      "stagger_day": "tuesday"
    },
    "@evidence": {
      "documents": ["docs/EVIDENCE_ENHANCEMENT_OVERVIEW.md", "docs/EVIDENCE_SCORING_DOCUMENTATION.md"],
      "review_interval_days": 14,
      "priority": "medium",
      "stagger_day": "wednesday"
    },
    "@api": {
      "documents": ["docs/API_DOCUMENTATION_README.md", "docs/API_DOCUMENTATION_SUMMARY.md"],
      "review_interval_days": 7,
      "priority": "high",
      "stagger_day": "thursday"
    },
    "@incremental": {
      "documents": ["docs/INCREMENTAL_REVIEW_USER_GUIDE.md", "docs/INCREMENTAL_REVIEW_MIGRATION_GUIDE.md"],
      "review_interval_days": 14,
      "priority": "medium",
      "stagger_day": "friday"
    }
  },
  
  "documents": [
    {
      "path": "docs/EVIDENCE_DECAY_README.md",
      "level": "L2",
      "owner": "@evidence",
      "last_reviewed": "2025-12-01T10:30:00Z",
      "last_reviewed_by": "staleness-agent",
      "review_interval_days": 14,
      "staleness_indicators": [
        "literature_review/utils/evidence_decay.py",
        "literature_review/utils/decay_presets.py"
      ],
      "staleness_history": [
        {
          "date": "2025-12-01",
          "score": 0.2,
          "action": "healthy"
        }
      ]
    }
  ]
}
```

### Staleness Assessment Output Schema

```json
{
  "assessment_id": "sa-2025-12-10-evidence",
  "timestamp": "2025-12-10T02:15:00Z",
  "domain": "@evidence",
  "documents_reviewed": [
    "docs/EVIDENCE_DECAY_README.md",
    "docs/EVIDENCE_SCORING_DOCUMENTATION.md"
  ],
  "analysis_window": {
    "from": "2025-11-26T00:00:00Z",
    "to": "2025-12-10T02:15:00Z",
    "days": 14
  },
  "repository_changes_analyzed": 45,
  "relevant_changes_found": 8,
  
  "staleness_score": 0.65,
  "confidence": 0.8,
  "needs_update": true,
  
  "findings": [
    {
      "document": "docs/EVIDENCE_DECAY_README.md",
      "issue_type": "missing_feature",
      "severity": "medium",
      "description": "New decay presets added in PR #95 are not documented",
      "evidence": {
        "commit": "abc123",
        "file": "literature_review/utils/decay_presets.py",
        "change": "Added 'aggressive' and 'conservative' presets"
      },
      "suggested_update": "Add section documenting new preset configurations",
      "estimated_effort": "small"
    },
    {
      "document": "docs/EVIDENCE_SCORING_DOCUMENTATION.md",
      "issue_type": "outdated_reference",
      "severity": "low",
      "description": "References old scoring weight defaults",
      "evidence": {
        "commit": "def456",
        "file": "literature_review/evidence_scorer.py",
        "change": "Changed default weights from 0.3/0.7 to 0.4/0.6"
      },
      "suggested_update": "Update weight values in scoring section",
      "estimated_effort": "trivial"
    }
  ],
  
  "recommended_action": "auto_update",
  
  "update_tasks": [
    {
      "task_id": "stale-001",
      "document": "docs/EVIDENCE_DECAY_README.md",
      "owner": "@evidence",
      "update_type": "UPDATE_FEATURE",
      "description": "Document new decay presets from PR #95",
      "depends_on": [],
      "priority": 1,
      "source": "staleness_review"
    }
  ]
}
```

### Weekly Digest Report Schema

```json
{
  "digest_id": "digest-2025-W50",
  "week": "2025-W50",
  "generated_at": "2025-12-10T03:00:00Z",
  
  "summary": {
    "domains_reviewed": 10,
    "domains_healthy": 7,
    "domains_need_attention": 2,
    "domains_auto_updated": 1,
    "total_findings": 5,
    "total_updates_triggered": 3
  },
  
  "domain_statuses": [
    {
      "domain": "@core",
      "status": "healthy",
      "staleness_score": 0.15,
      "last_activity": "2025-12-08",
      "days_inactive": 2
    },
    {
      "domain": "@evidence",
      "status": "needs_attention",
      "staleness_score": 0.65,
      "last_activity": "2025-11-26",
      "days_inactive": 14,
      "findings_count": 2,
      "action_taken": "auto_update"
    },
    {
      "domain": "@api",
      "status": "review_requested",
      "staleness_score": 0.42,
      "last_activity": "2025-12-01",
      "days_inactive": 9,
      "findings_count": 1,
      "action_taken": "github_issue_created",
      "issue_number": 142
    }
  ],
  
  "actions_taken": [
    {
      "domain": "@evidence",
      "action": "sent_to_distributor",
      "tasks_count": 2,
      "update_list_id": "ul-stale-2025-12-10-evidence"
    },
    {
      "domain": "@api",
      "action": "created_github_issue",
      "issue_number": 142,
      "issue_title": "📚 Staleness Review: @api domain may need updates"
    }
  ]
}
```

---

## 🎯 Component Specifications

### 1. Schedule Trigger

```yaml
node_type: n8n-nodes-base.scheduleTrigger
name: "Weekly Staleness Review"

config:
  rule:
    interval:
      - field: weeks
        value: 1
    # Alternatively, use cron expression
    # cronExpression: "0 2 * * 0"  # Every Sunday at 2 AM
  
output:
  trigger_type: "scheduled_staleness_review"
  timestamp: ISO-8601
  week_number: "2025-W50"
```

### 2. Domain Scanner

```yaml
node_type: n8n-nodes-base.code
name: "Scan All Domains"
purpose: Load matrix and identify domains due for review

javascript: |
  // Fetch the documentation matrix
  const matrixUrl = 'https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json';
  
  // This would be fetched via HTTP Request node in practice
  const matrix = $input.first().json.matrix;
  const config = matrix.staleness_config;
  const now = new Date();
  
  const domainsToReview = [];
  
  for (const [domain, info] of Object.entries(matrix.owner_domains)) {
    // Handle both old format (array) and new format (object)
    const domainConfig = Array.isArray(info) 
      ? { documents: info, review_interval_days: config.default_review_interval_days }
      : info;
    
    // Check if this domain is due for review based on stagger schedule
    if (config.schedule.stagger_domains) {
      const today = now.toLocaleDateString('en-US', { weekday: 'lowercase' });
      if (domainConfig.stagger_day && domainConfig.stagger_day !== today) {
        continue; // Not this domain's day
      }
    }
    
    domainsToReview.push({
      domain,
      documents: domainConfig.documents,
      review_interval_days: domainConfig.review_interval_days || config.default_review_interval_days,
      priority: domainConfig.priority || 'medium'
    });
  }
  
  return domainsToReview.map(d => ({ json: d }));

output:
  # Returns multiple items, one per domain
  - domain: "@evidence"
    documents: ["docs/EVIDENCE_DECAY_README.md", ...]
    review_interval_days: 14
    priority: "medium"
```

### 3. Activity Checker (Per Domain)

```yaml
node_type: n8n-nodes-base.httpRequest
name: "Get Domain Last Activity"
purpose: Query GitHub for last commit touching domain files

method: GET
url: "https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/commits"
queryParameters:
  path: "{{ $json.documents[0] }}"  # Primary doc path
  per_page: 1
  
headers:
  Accept: "application/vnd.github.v3+json"
  Authorization: "Bearer {{ $credentials.githubApi.accessToken }}"

output:
  last_commit_date: "2025-11-26T15:30:00Z"
  last_commit_sha: "abc123"
  last_commit_author: "developer"
```

### 4. Inactivity Calculator

```yaml
node_type: n8n-nodes-base.code
name: "Calculate Inactivity"
purpose: Determine if domain needs review

javascript: |
  const domain = $('Scan All Domains').item.json;
  const lastActivity = $('Get Domain Last Activity').first().json;
  
  const lastCommitDate = new Date(lastActivity[0]?.commit?.author?.date || '2000-01-01');
  const now = new Date();
  const daysInactive = Math.floor((now - lastCommitDate) / (1000 * 60 * 60 * 24));
  
  const needsReview = daysInactive >= domain.review_interval_days;
  
  return {
    domain: domain.domain,
    documents: domain.documents,
    last_activity: lastCommitDate.toISOString(),
    days_inactive: daysInactive,
    review_interval: domain.review_interval_days,
    needs_review: needsReview,
    priority: domain.priority
  };

output:
  domain: "@evidence"
  documents: [...]
  last_activity: "2025-11-26T15:30:00Z"
  days_inactive: 14
  review_interval: 14
  needs_review: true
```

### 5. Repository Change Aggregator

```yaml
node_type: n8n-nodes-base.httpRequest
name: "Fetch Recent Changes"
purpose: Get all commits since domain's last activity

method: GET
url: "https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/commits"
queryParameters:
  since: "{{ $json.last_activity }}"
  per_page: 100

headers:
  Accept: "application/vnd.github.v3+json"
  Authorization: "Bearer {{ $credentials.githubApi.accessToken }}"
```

### 6. Change Filter

```yaml
node_type: n8n-nodes-base.code
name: "Filter Relevant Changes"
purpose: Extract changes relevant to this domain

javascript: |
  const domain = $('Calculate Inactivity').first().json;
  const commits = $('Fetch Recent Changes').first().json;
  const matrix = $('Fetch Matrix').first().json;
  
  // Get scripts that affect this domain's docs
  const relevantScripts = [];
  for (const doc of domain.documents) {
    const docEntry = matrix.documents?.find(d => d.path === doc);
    if (docEntry?.staleness_indicators) {
      relevantScripts.push(...docEntry.staleness_indicators);
    }
    // Also check script_to_docs mapping (reverse lookup)
    for (const [script, docs] of Object.entries(matrix.script_to_docs || {})) {
      if (docs.includes(doc)) {
        relevantScripts.push(script);
      }
    }
  }
  
  const ignorePatterns = matrix.staleness_config?.ignore_patterns || [];
  
  // Filter commits to those touching relevant files
  const relevantChanges = [];
  
  for (const commit of commits) {
    // Would need to fetch commit details for file list
    // Simplified: check commit message for relevant keywords
    const message = commit.commit?.message || '';
    const isRelevant = relevantScripts.some(script => 
      message.toLowerCase().includes(script.replace('.py', '').toLowerCase())
    );
    
    if (isRelevant) {
      relevantChanges.push({
        sha: commit.sha,
        message: message.split('\n')[0],  // First line only
        author: commit.commit?.author?.name,
        date: commit.commit?.author?.date,
        url: commit.html_url
      });
    }
  }
  
  return {
    ...domain,
    total_commits_since: commits.length,
    relevant_changes: relevantChanges,
    relevant_scripts: [...new Set(relevantScripts)]
  };
```

### 7. Staleness Assessment AI Agent

```yaml
node_type: n8n-nodes-langchain.agent
name: "Staleness Assessment Agent"
model: gemini-1.5-pro
temperature: 0.3

system_prompt: |
  You are a Documentation Staleness Reviewer for a software project.
  
  Your task is to analyze whether documentation has become stale by comparing
  the current documentation content against recent repository changes.
  
  ## Input You Receive
  
  1. **Domain Info**: Which documentation domain you're reviewing
  2. **Documents**: The current content of the domain's documentation files
  3. **Recent Changes**: Commits and changes since the docs were last updated
  4. **Relevant Scripts**: Code files that these docs describe
  
  ## What to Look For
  
  1. **Missing Features**: New functionality added to code but not documented
  2. **Outdated References**: Code references in docs that no longer match reality
  3. **Changed Behavior**: Default values, parameters, or behaviors that changed
  4. **Deprecated Patterns**: Old approaches still documented but replaced in code
  5. **Missing Cross-References**: New related docs that should be linked
  6. **Version/Date Staleness**: Outdated version numbers or dates
  7. **API Changes**: Endpoints, parameters, or responses that changed
  
  ## Staleness Scoring
  
  - **0.0 - 0.2**: Healthy - docs accurately reflect current code
  - **0.2 - 0.4**: Minor drift - cosmetic issues, no functional inaccuracies
  - **0.4 - 0.6**: Moderate staleness - some outdated info, may confuse users
  - **0.6 - 0.8**: Significant staleness - notable inaccuracies, needs attention
  - **0.8 - 1.0**: Critical staleness - docs are misleading, urgent update needed
  
  ## Output Format
  
  You MUST output valid JSON in this exact structure:
  
  ```json
  {
    "domain": "@example",
    "staleness_score": 0.65,
    "confidence": 0.8,
    "needs_update": true,
    "summary": "Brief summary of findings",
    "findings": [
      {
        "document": "docs/EXAMPLE.md",
        "issue_type": "missing_feature|outdated_reference|changed_behavior|deprecated_pattern|missing_link|version_stale|api_change",
        "severity": "critical|high|medium|low|trivial",
        "description": "What is wrong or missing",
        "evidence": {
          "commit": "sha or PR number",
          "file": "affected code file",
          "change": "what changed in the code"
        },
        "suggested_update": "Specific recommendation for fixing",
        "estimated_effort": "trivial|small|medium|large"
      }
    ],
    "recommended_action": "auto_update|manual_review|create_issue|healthy",
    "update_tasks": [
      {
        "task_id": "stale-NNN",
        "document": "path/to/doc.md",
        "owner": "@domain",
        "update_type": "UPDATE_FEATURE|UPDATE_REFERENCE|SYNC_STATUS",
        "description": "Task description for the domain agent",
        "depends_on": [],
        "priority": 1
      }
    ]
  }
  ```
  
  ## Guidelines
  
  - Be conservative: only flag real issues, not stylistic preferences
  - Consider context: a commit touching a file doesn't mean docs must change
  - Provide specific, actionable recommendations
  - When in doubt, recommend manual review over auto-update
  - Include evidence (commit refs) so humans can verify

user_prompt: |
  Review the following domain for staleness:
  
  **Domain:** {{ $json.domain }}
  **Days Since Last Activity:** {{ $json.days_inactive }}
  **Documents to Review:** {{ $json.documents.join(', ') }}
  
  **Relevant Code Files (staleness indicators):**
  {{ $json.relevant_scripts.join('\n') }}
  
  **Recent Repository Changes ({{ $json.relevant_changes.length }} commits):**
  {{ $json.relevant_changes.map(c => `- ${c.sha.slice(0,7)}: ${c.message}`).join('\n') }}
  
  **Current Documentation Content:**
  {{ $json.document_contents }}
  
  Analyze this documentation for staleness and provide your assessment.

tools:
  - github_read_file:
      description: Read a file from the repository
      parameters:
        path: File path to read
```

### 8. Response Parser

```yaml
node_type: n8n-nodes-base.code
name: "Parse Assessment"
purpose: Extract and validate AI response

javascript: |
  const response = $input.first().json;
  const text = response.text || response.output || JSON.stringify(response);
  
  // Extract JSON from response
  const jsonMatch = text.match(/```json\n?([\s\S]*?)\n?```/) || text.match(/\{[\s\S]*\}/);
  
  let assessment;
  try {
    assessment = JSON.parse(jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : text);
  } catch (e) {
    // Fallback for unparseable response
    assessment = {
      domain: $('Calculate Inactivity').first().json.domain,
      staleness_score: 0.5,
      confidence: 0.3,
      needs_update: false,
      summary: "Could not parse AI response - manual review recommended",
      findings: [],
      recommended_action: "manual_review",
      update_tasks: []
    };
  }
  
  // Validate and normalize
  assessment.staleness_score = Math.max(0, Math.min(1, assessment.staleness_score || 0));
  assessment.confidence = Math.max(0, Math.min(1, assessment.confidence || 0.5));
  assessment.timestamp = new Date().toISOString();
  assessment.assessment_id = `sa-${new Date().toISOString().slice(0,10)}-${assessment.domain.replace('@','')}`;
  
  return assessment;
```

### 9. Decision Router

```yaml
node_type: n8n-nodes-base.switch
name: "Route by Staleness"
purpose: Determine action based on staleness score

rules:
  - name: "Auto Update"
    condition: "{{ $json.staleness_score >= 0.7 && $json.recommended_action === 'auto_update' }}"
    output: 0  # To Task Distributor
    
  - name: "Manual Review"
    condition: "{{ $json.staleness_score >= 0.5 }}"
    output: 1  # To GitHub Issue Creator
    
  - name: "Create Issue"
    condition: "{{ $json.staleness_score >= 0.3 }}"
    output: 2  # To GitHub Issue Creator (lower priority)
    
  - name: "Healthy"
    condition: "{{ $json.staleness_score < 0.3 }}"
    output: 3  # To Logger
```

### 10. Task Distributor Integration

```yaml
node_type: n8n-nodes-base.httpRequest
name: "Send to Distributor"
purpose: Forward update tasks to existing distributor workflow

method: POST
url: "https://gitlitreview.app.n8n.cloud/webhook/task-distributor"
contentType: application/json

body: |
  {
    "update_list_id": "ul-stale-{{ $json.assessment_id }}",
    "source": "staleness_review",
    "trigger": {
      "type": "scheduled_staleness_review",
      "domain": "{{ $json.domain }}",
      "staleness_score": {{ $json.staleness_score }},
      "assessment_id": "{{ $json.assessment_id }}"
    },
    "tasks": {{ JSON.stringify($json.update_tasks) }}
  }
```

### 11. GitHub Issue Creator

```yaml
node_type: n8n-nodes-base.httpRequest
name: "Create Review Issue"
purpose: Create GitHub issue for manual review

method: POST
url: "https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/issues"

headers:
  Accept: "application/vnd.github.v3+json"
  Authorization: "Bearer {{ $credentials.githubApi.accessToken }}"

body: |
  {
    "title": "📚 Staleness Review: {{ $json.domain }} domain may need updates",
    "body": "## Automated Staleness Review\n\n**Domain:** {{ $json.domain }}\n**Staleness Score:** {{ ($json.staleness_score * 100).toFixed(0) }}%\n**Confidence:** {{ ($json.confidence * 100).toFixed(0) }}%\n**Assessment ID:** {{ $json.assessment_id }}\n\n### Summary\n\n{{ $json.summary }}\n\n### Findings\n\n{{ $json.findings.map(f => `- **${f.document}** (${f.severity}): ${f.description}`).join('\n') }}\n\n### Recommended Actions\n\n{{ $json.findings.map(f => `- [ ] ${f.suggested_update}`).join('\n') }}\n\n---\n*This issue was automatically created by the staleness review workflow.*",
    "labels": ["documentation", "staleness-review", "automated", "{{ $json.domain.replace('@', '') }}"]
  }
```

### 12. Weekly Digest Generator

```yaml
node_type: n8n-nodes-base.code
name: "Generate Digest"
purpose: Compile weekly summary of all domain reviews

javascript: |
  // Collect results from all domain reviews in this run
  const allResults = $items('Parse Assessment');
  const now = new Date();
  const weekNum = getWeekNumber(now);
  
  function getWeekNumber(d) {
    d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return `${d.getUTCFullYear()}-W${Math.ceil((((d - yearStart) / 86400000) + 1) / 7)}`;
  }
  
  const digest = {
    digest_id: `digest-${weekNum}`,
    week: weekNum,
    generated_at: now.toISOString(),
    summary: {
      domains_reviewed: allResults.length,
      domains_healthy: allResults.filter(r => r.json.staleness_score < 0.3).length,
      domains_need_attention: allResults.filter(r => r.json.staleness_score >= 0.5).length,
      domains_auto_updated: allResults.filter(r => r.json.recommended_action === 'auto_update').length,
      total_findings: allResults.reduce((sum, r) => sum + (r.json.findings?.length || 0), 0),
      avg_staleness_score: (allResults.reduce((sum, r) => sum + r.json.staleness_score, 0) / allResults.length).toFixed(2)
    },
    domain_statuses: allResults.map(r => ({
      domain: r.json.domain,
      status: r.json.staleness_score < 0.3 ? 'healthy' : 
              r.json.staleness_score < 0.5 ? 'minor_drift' :
              r.json.staleness_score < 0.7 ? 'needs_attention' : 'critical',
      staleness_score: r.json.staleness_score,
      findings_count: r.json.findings?.length || 0,
      action_taken: r.json.recommended_action
    }))
  };
  
  return digest;
```

---

## 🔧 N8N Workflow Implementation

### Workflow 5: Doc Chain - Staleness Review

```
[Schedule Trigger: Weekly]
           │
           ├─────────────────────────┐
           │                         │
           ▼                         ▼
[HTTP: Fetch Matrix]        [Webhook: Manual Trigger]
           │                         │
           └────────────┬────────────┘
                        │
                        ▼
           [Code: Scan All Domains]
                        │
                        ▼
           [Split In Batches: Per Domain]
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
    [HTTP: Get Activity]   [HTTP: Get Activity]  (parallel per domain)
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
           [Code: Calculate Inactivity]
                        │
                        ▼
           [IF: Needs Review?]
                        │
              ┌─────────┴─────────┐
             No                  Yes
              │                   │
              ▼                   ▼
    [Code: Log Healthy]  [HTTP: Fetch Recent Changes]
              │                   │
              │                   ▼
              │          [Code: Filter Relevant]
              │                   │
              │                   ▼
              │          [HTTP: Fetch Doc Contents]
              │                   │
              │                   ▼
              │          [AI: Staleness Assessment]
              │                   │
              │                   ▼
              │          [Code: Parse Assessment]
              │                   │
              │                   ▼
              │          [Switch: Route by Score]
              │                   │
              │     ┌──────┬──────┼──────┬──────┐
              │     │      │      │      │      │
              │     ▼      ▼      ▼      ▼      ▼
              │  [HTTP:  [HTTP:  [HTTP:  [Code:
              │   Dist]   Issue]  Issue]  Log]
              │     │      │      │      │
              │     │      │      │      │
              └─────┴──────┴──────┴──────┴──────┐
                                                │
                                                ▼
                              [Merge: All Results]
                                                │
                                                ▼
                              [Code: Generate Digest]
                                                │
                                                ▼
                              [HTTP: Post Digest Issue]
                                                │
                                                ▼
                                             [End]
```

---

## 💰 Cost Management

### API Call Budgeting

| Component | Calls Per Domain | Domains | Weekly Total | Monthly Estimate |
|-----------|------------------|---------|--------------|------------------|
| GitHub: Get Activity | 1 | 12 | 12 | 48 |
| GitHub: Fetch Commits | 1 | 12 | 12 | 48 |
| GitHub: Read Files | ~3 | 12 | 36 | 144 |
| Gemini: Assessment | 1 | 12 | 12 | 48 |
| GitHub: Create Issue | ~2 | - | ~2 | ~8 |
| **Total** | | | **~74** | **~296** |

### Cost Optimization Strategies

1. **Skip Unchanged Repos**
   ```javascript
   // Before running staleness check, verify repo has commits since last review
   const lastReviewDate = matrix.last_staleness_review;
   const repoActivity = await getRepoCommitsSince(lastReviewDate);
   if (repoActivity.length === 0) {
     return { skip: true, reason: 'No repository activity since last review' };
   }
   ```

2. **Cache Document Contents**
   - Store document SHA and content
   - Only re-fetch if SHA changed
   - Reduces GitHub API calls by ~50%

3. **Batch Domain Reviews**
   - Instead of 12 weekly reviews, do 2-3 domains per day
   - Spreads API usage and Gemini costs

4. **Tiered Review Frequency**
   | Priority | Review Interval | Domains |
   |----------|-----------------|---------|
   | High | Weekly | @core, @dashboard, @api |
   | Medium | Bi-weekly | @evidence, @incremental |
   | Low | Monthly | @guides, @architecture |

5. **Quick Pre-Check**
   - Before AI assessment, do simple heuristic check
   - If no relevant files changed, skip AI call
   - Saves ~60% of AI costs

---

## 🛡️ False Positive Mitigation

### Strategies

1. **Conservative Thresholds**
   - Start with high threshold (0.7) for auto-updates
   - Lower gradually based on accuracy metrics
   
2. **Confidence Weighting**
   - AI provides confidence score
   - Low confidence → manual review, not auto-update
   
3. **Change Type Filtering**
   ```javascript
   const ignoreChangeTypes = [
     'test: ',      // Test-only changes
     'ci: ',        // CI/CD changes
     'chore: ',     // Maintenance
     'style: ',     // Formatting
     'refactor: '   // Internal refactoring (sometimes)
   ];
   
   const isRelevantChange = (commitMessage) => {
     return !ignoreChangeTypes.some(prefix => 
       commitMessage.toLowerCase().startsWith(prefix)
     );
   };
   ```

4. **Human-in-the-Loop Modes**
   | Staleness Score | Action |
   |-----------------|--------|
   | ≥ 0.8 | Auto-update (high confidence) |
   | 0.5 - 0.8 | Create PR for review |
   | 0.3 - 0.5 | Create GitHub issue |
   | < 0.3 | Log only |

5. **Review Before Merge**
   - Even "auto-updates" create PRs, not direct commits
   - Allows human verification before merge
   - Can enable auto-merge after trust is established

6. **Feedback Loop**
   - Track when humans reject/modify AI suggestions
   - Use feedback to tune prompts and thresholds
   
   ```json
   {
     "feedback_tracking": {
       "assessment_id": "sa-2025-12-10-evidence",
       "ai_recommendation": "auto_update",
       "human_action": "modified",
       "human_notes": "AI missed context about intentional deprecation",
       "learning": "Check CHANGELOG for intentional deprecations"
     }
   }
   ```

---

## 📈 Observability & Monitoring

### Metrics to Track

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `staleness_reviews_completed` | Weekly review count | < expected domains |
| `avg_staleness_score` | Average across domains | > 0.5 sustained |
| `domains_critical` | Domains with score > 0.8 | > 0 |
| `auto_updates_triggered` | Updates sent to distributor | Monitor trend |
| `issues_created` | GitHub issues from reviews | Monitor trend |
| `ai_confidence_avg` | Average AI confidence | < 0.5 |
| `false_positive_rate` | Rejected AI suggestions | > 20% |
| `review_duration_avg` | Time to complete review | > 5 min/domain |

### Dashboard Queries

```sql
-- Domain health over time
SELECT 
  domain,
  DATE_TRUNC('week', timestamp) as week,
  AVG(staleness_score) as avg_score
FROM staleness_assessments
GROUP BY domain, week
ORDER BY week DESC;

-- Domains trending towards staleness
SELECT 
  domain,
  staleness_score as current_score,
  LAG(staleness_score) OVER (PARTITION BY domain ORDER BY timestamp) as previous_score,
  staleness_score - LAG(staleness_score) OVER (PARTITION BY domain ORDER BY timestamp) as trend
FROM staleness_assessments
WHERE timestamp > NOW() - INTERVAL '4 weeks';
```

### Alerting Rules

```yaml
alerts:
  - name: critical_staleness
    condition: staleness_score > 0.8 for any domain
    action: 
      - Create high-priority GitHub issue
      - Send Slack notification
      
  - name: review_failure
    condition: staleness_review workflow fails
    action:
      - Retry once
      - Alert on second failure
      
  - name: sustained_drift
    condition: avg_staleness_score > 0.5 for 3 consecutive weeks
    action:
      - Create summary issue
      - Request manual audit
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Days 1-2)
- [ ] Update `documentation_matrix.json` with new schema fields
- [ ] Add `staleness_config` section
- [ ] Add `last_reviewed` and `review_interval_days` to documents
- [ ] Create `staleness_indicators` mapping for key docs

### Phase 2: Schedule & Scanning (Days 3-4)
- [ ] Create new n8n workflow "Doc Chain - Staleness Review"
- [ ] Implement Schedule Trigger (weekly cron)
- [ ] Implement Domain Scanner node
- [ ] Implement Activity Checker (GitHub API)
- [ ] Implement Inactivity Calculator
- [ ] Test: verify domains are correctly identified for review

### Phase 3: Change Analysis (Days 5-6)
- [ ] Implement Repository Change Aggregator
- [ ] Implement Change Filter (relevant changes only)
- [ ] Implement document content fetching
- [ ] Test: verify relevant changes are correctly identified

### Phase 4: AI Assessment (Days 7-9)
- [ ] Implement Staleness Assessment AI Agent
- [ ] Create and test system prompt
- [ ] Implement Response Parser with validation
- [ ] Test: verify AI produces valid assessments
- [ ] Tune prompt based on initial results

### Phase 5: Routing & Actions (Days 10-11)
- [ ] Implement Decision Router (Switch node)
- [ ] Implement Task Distributor integration
- [ ] Implement GitHub Issue Creator
- [ ] Implement healthy domain logger
- [ ] Test: verify correct routing based on scores

### Phase 6: Digest & Polish (Days 12-14)
- [ ] Implement Weekly Digest Generator
- [ ] Implement Digest Issue/Report creation
- [ ] Add manual trigger webhook
- [ ] End-to-end testing
- [ ] Documentation

### Phase 7: Optimization (Week 3+)
- [ ] Implement caching layer
- [ ] Add feedback tracking
- [ ] Tune thresholds based on real data
- [ ] Add monitoring dashboard
- [ ] Reduce false positives

---

## 🔗 Integration Points

### Required Credentials

| Credential | Purpose | Setup |
|------------|---------|-------|
| GitHub API Token | Read files, create issues | Fine-grained PAT with `contents:read`, `issues:write` |
| Gemini API | AI assessments | Google AI API key |

### Webhook Endpoints

| Endpoint | Purpose | Workflow |
|----------|---------|----------|
| `/webhook/staleness-review` | Manual trigger | Staleness Review |
| `/webhook/task-distributor` | Send update tasks | Existing Distributor |

### Files Modified

| File | Changes |
|------|---------|
| `docs/documentation_matrix.json` | Add staleness_config, enhance owner_domains |
| `docs/N8N_STALENESS_REVIEW_BLUEPRINT.md` | This document |
| `docs/N8N_AI_BUILDER_PROMPT.md` | Add Workflow 5 prompt (separate section) |

---

## 📝 Configuration Reference

### Environment Variables

```bash
# Staleness Review Configuration
STALENESS_ENABLED=true
STALENESS_DEFAULT_INTERVAL=7          # days
STALENESS_MAX_INACTIVITY=21           # days
STALENESS_AUTO_UPDATE_THRESHOLD=0.7
STALENESS_ISSUE_THRESHOLD=0.3
STALENESS_DIGEST_ENABLED=true

# Cost Controls
STALENESS_MAX_DOMAINS_PER_RUN=12
STALENESS_AI_TIMEOUT_SECONDS=60
STALENESS_CACHE_TTL_HOURS=24
```

### Feature Flags

```json
{
  "staleness_review": {
    "enabled": true,
    "dry_run": false,
    "auto_update_enabled": true,
    "create_issues_enabled": true,
    "digest_enabled": true,
    "domains_enabled": ["@core", "@dashboard", "@api", "@evidence"],
    "domains_disabled": ["@architecture"],
    "debug_mode": false
  }
}
```

---

## 📚 Related Documentation

- [N8N Documentation Chain Blueprint](./N8N_DOCUMENTATION_CHAIN_BLUEPRINT.md) - Main automation system
- [N8N AI Builder Prompt](./N8N_AI_BUILDER_PROMPT.md) - Workflow building prompts
- [Documentation Matrix](./DOCUMENTATION_MATRIX.md) - Human-readable matrix
- [documentation_matrix.json](./documentation_matrix.json) - Machine-readable matrix

---

*Blueprint Version: 1.0*
*Created: 2025-12-10*
*Status: Draft - Ready for Implementation*
*Author: Documentation Automation Team*
