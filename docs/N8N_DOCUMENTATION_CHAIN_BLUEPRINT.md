# 🔄 N8N Documentation Update Chain Blueprint

> **Purpose:** Automate documentation updates when code or documentation changes are pushed/merged to GitHub, using a multi-agent orchestration system in n8n.
> 
> **Version:** 2.0 (December 2025)  
> **Status:** Production Ready - 6 Workflows Implemented

---

## 📋 Executive Summary

This system creates an automated documentation maintenance pipeline with **6 interconnected workflows**:

### Event-Driven (Workflows 1-4)
1. **Trigger** - Detects what changed (code or docs) from GitHub push/merge events
2. **Distributor** - Orchestrates task execution with dependency management
3. **Agent** - AI-powered domain agents that make targeted documentation updates
4. **Errors** - Centralized error handling and recovery

### Proactive Maintenance (Workflows 5-6)
5. **Staleness Review** - Weekly scheduled checks for documentation that may have drifted
6. **State Reconciliation** - Daily verification that task card status matches claimed percentages

**Scope:** Documentation and record-keeping only - no core functionality changes.

### Key Capabilities
- 56+ documents tracked across 17 owner domains
- Cascade rules for task card → index → roadmap propagation
- AI-powered staleness detection with configurable thresholds
- Deep state reconciliation ensuring status accuracy

---

## 🏗️ System Architecture

### Complete Workflow Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GITHUB                                          │
│  ┌──────────────┐                                                            │
│  │ Push/Merge   │ ─────────────────────────────────────────────────────────┐ │
│  │ Event        │                                                          │ │
│  └──────────────┘                                                          │ │
└────────────────────────────────────────────────────────────────────────────┼─┘
                                                                             │
                                    Webhook                                  │
                                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          N8N WORKFLOW ECOSYSTEM                              │
│                                                                              │
│  ┌─────────────┐     ┌─────────────────┐     ┌──────────────┐              │
│  │  GitHub     │────▶│  Doc Chain -    │────▶│  Doc Chain - │◀───────────┐ │
│  │  Webhook    │     │  Trigger (1)    │     │  Distributor │            │ │
│  └─────────────┘     └─────────────────┘     │    (2)       │◀─────────┐ │ │
│                                              └──────┬───────┘          │ │ │
│                                                     │                  │ │ │
│                         ┌───────────────────────────┘                  │ │ │
│                         ▼                                              │ │ │
│                  ┌──────────────┐     callback     ┌──────────────┐   │ │ │
│                  │  Doc Chain - │─────────────────▶│  Distributor │   │ │ │
│                  │  Agent (3)   │                  │  (continues) │   │ │ │
│                  └──────────────┘                  └──────────────┘   │ │ │
│                         │                                              │ │ │
│                         ▼                                              │ │ │
│                  ┌──────────────┐                                     │ │ │
│                  │  Doc Chain - │ (catches errors from all)           │ │ │
│                  │  Errors (4)  │                                     │ │ │
│                  └──────────────┘                                     │ │ │
│                                                                        │ │ │
│  ┌────────────────────────────────────────────────────────────────────┼─┼─┤
│  │                    PROACTIVE MAINTENANCE                           │ │ │ │
│  │                                                                    │ │ │ │
│  │  ┌───────────────┐     ┌─────────────────┐     (tasks)            │ │ │ │
│  │  │  Schedule     │────▶│  Doc Chain -    │─────────────────────────┘ │ │ │
│  │  │  (Weekly)     │     │  Staleness (5)  │                           │ │ │
│  │  └───────────────┘     │  Review         │────▶ GitHub Issues        │ │ │
│  │                        └─────────────────┘      (if manual review)   │ │ │
│  │                                                                      │ │ │
│  │  ┌───────────────┐     ┌─────────────────┐     (tasks)              │ │ │
│  │  │  Schedule     │────▶│  Doc Chain -    │──────────────────────────┘ │ │
│  │  │  (Daily 4AM)  │     │  State Recon    │                            │ │
│  │  └───────────────┘     │  (6)            │────▶ Fixes mismatches       │ │
│  │                        └─────────────────┘      (status vs claimed %)  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Workflow Communication
- **Trigger → Distributor:** HTTP POST to `/webhook/task-distributor`
- **Distributor → Agent:** HTTP POST to `/webhook/domain-agent` (fire-and-forget)
- **Agent → Distributor:** HTTP callback with completion status
- **Staleness Review → Distributor:** HTTP POST to `/webhook/task-distributor` (same endpoint)
- **State Reconciliation → Distributor:** HTTP POST to `/webhook/task-distributor` (same endpoint)

### Event-Driven Flow (Workflows 1-4)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               TRIGGER LAYER                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐         │
│  │ GitHub Webhook  │───▶│ Change Parser   │───▶│ Matrix Lookup    │         │
│  │ Receiver        │    │ (files changed) │    │ (find deps)      │         │
│  └─────────────────┘    └─────────────────┘    └──────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │                                        
                                      ▼                                        
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATION LAYER                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    TASK MASTER AGENT                                 │    │
│  │  • Analyzes change impact                                            │    │
│  │  • Generates Update List with execution order                        │    │
│  │  • Submits to Task Distributor                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  TASK DISTRIBUTOR AGENT                              │    │
│  │  • Maintains Update List Queue (FIFO)                                │    │
│  │  • Executes lists serially (one complete before next)                │    │
│  │  • Tracks task completion within each list                           │    │
│  │  • Unlocks dependent tasks when prerequisites complete               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │                                        
                                      ▼                                        
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXECUTION LAYER                                    │
│                                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │
│  │ @core    │ │@dashboard│ │@evidence │ │ @api     │ │ @parity  │ │ +12   │ │
│  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │ more  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬───┘ │
│       │            │            │            │            │           │      │
│       └────────────┴────────────┴────────────┴────────────┴───────────┘      │
│                              │                                               │
│                    Completion Callbacks → Distributor                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │                                        
                                      ▼                                        
┌─────────────────────────────────────────────────────────────────────────────┐
│                            COMMIT LAYER                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐         │
│  │ Change          │───▶│ PR Creator      │───▶│ Auto-Merge       │         │
│  │ Aggregator      │    │ (doc updates)   │    │ (if configured)  │         │
│  └─────────────────┘    └─────────────────┘    └──────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Component Specifications

### 1. Trigger Layer (Workflow 1)

#### 1.1 GitHub Webhook Receiver
```yaml
node_type: n8n-nodes-base.webhook
trigger: push, pull_request (merged)
config:
  path: /github-doc-trigger
  method: POST
  authentication: GitHub signature verification (or secret query param)
  
output:
  event_type: push | pull_request
  repository: owner/repo
  branch: main
  commits: [commit_sha, ...]
  changed_files: [path, ...]
  author: username
  timestamp: ISO-8601
```

#### 1.2 Filter Valid Events (Feedback Loop Prevention)
```yaml
node_type: n8n-nodes-base.code
purpose: Prevent automated n8n commits from triggering infinite loops

logic:
  - Check for valid commits or merged PR
  - Detect automated n8n commits: [n8n] docs: or [n8n] chore:
  - Allow manual [n8n] commits (like [n8n] fix:)
  - Return empty array to stop workflow for invalid/automated events
  
patterns:
  automated_prefixes:
    - "[n8n] docs:"
    - "[n8n] chore:"
  allowed_prefixes:
    - "[n8n] fix:"
    - "[n8n] feat:"
```

#### 1.3 Change Parser
```yaml
node_type: n8n-nodes-base.code
purpose: Extract and categorize changed files

logic:
  - Fetch commit details via GitHub API
  - Categorize files:
      - code_changes: *.py, *.js, *.json (non-doc)
      - doc_changes: *.md
      - config_changes: docker-compose.yml, requirements.txt
      - task_card_changes: task-cards/**/*.md
  - Filter to relevant paths (literature_review/, webdashboard/, docs/, task-cards/)
  
output:
  trigger_type: code | docs | config | task_card
  changed_files: [
    { path: "...", type: "code|docs|config|task_card", action: "added|modified|deleted" }
  ]
```

#### 1.4 Matrix Lookup
```yaml
node_type: n8n-nodes-base.code
purpose: Query documentation_matrix.json for dependencies

inputs:
  - changed_files from Change Parser
  
logic:
  - Load docs/documentation_matrix.json (v1.3)
  - For each changed file:
      - If code file: lookup script_to_docs mapping
      - If doc file: lookup document dependencies and cascade_rules
      - If task card: lookup cascade_rules for parent indexes
  - Deduplicate and sort by priority level (L1 → L2 → L3)
  - Apply cascade_rules for task card → index → roadmap propagation
  
output:
  affected_docs: [
    { path: "...", owner: "@domain", level: "L1|L2|L3", depends_on: [...] }
  ]
  cascade_order: [[L1 docs], [L2 docs], [L3 docs]]
```

---

### 2. Orchestration Layer (Workflow 2)

#### 2.1 Task Master Agent

```yaml
node_type: n8n-nodes-langchain.agent
model: gemini-2.5-flash | gpt-4o-mini
purpose: Analyze changes and generate ordered update list

system_prompt: |
  You are the Task Master Agent for documentation updates.
  
  Your responsibilities:
  1. Analyze the GitHub change event and affected documentation list
  2. Determine what updates are needed for each document
  3. Generate an Update List with proper execution order
  4. Respect cascade dependencies (L1 before L2, L2 before L3)
  5. Apply cascade_rules from the documentation matrix
  
  Update types you can assign:
  - SYNC_STATUS: Update status/completion markers
  - UPDATE_REFERENCE: Update code references or examples
  - UPDATE_TODO: Mark tasks complete or add new ones
  - UPDATE_ARCHITECTURE: Reflect structural changes
  - UPDATE_ROADMAP: Update progress/milestones
  - STATUS_UPDATE: Propagate task card status to indexes
  - CHECKBOX_TOGGLE: Update checkbox states in indexes
  - COMPLETION_PERCENTAGE: Recalculate and update completion %
  - REVIEW_NEEDED: Flag for human review (complex changes)

inputs:
  - event_summary: What changed (commit message, PR title)
  - changed_files: List of modified files
  - affected_docs: Documents that need updating
  - cascade_order: Execution priority levels
  - cascade_rules: From documentation_matrix.json

output:
  update_list_id: UUID
  created_at: ISO-8601
  trigger_event: { commit_sha, pr_number, author }
  tasks: [
    {
      task_id: "task-001",
      document: "docs/DASHBOARD_GUIDE.md",
      owner: "@dashboard",
      update_type: "UPDATE_REFERENCE",
      description: "Update API endpoint examples after app.py changes",
      depends_on: [],  # Can run first
      priority: 1
    },
    {
      task_id: "task-002", 
      document: "README.md",
      owner: "@core",
      update_type: "SYNC_STATUS",
      description: "Update feature status after dashboard changes",
      depends_on: ["task-001"],  # Must wait for task-001
      priority: 2
    }
  ]
```

#### 2.2 Task Distributor Agent

```yaml
node_type: n8n-nodes-base.code + n8n-nodes-base.wait
purpose: Orchestrate task execution with dependency management

state_management:
  storage: n8n static data OR external Redis/DB
  
  state_schema:
    update_queue: [update_list_id, ...]  # FIFO queue
    current_list: {
      id: update_list_id,
      status: "in_progress" | "completed" | "failed",
      tasks: {
        "task-001": { status: "pending|running|completed|failed", started_at, completed_at },
        ...
      }
    }
    completed_lists: [update_list_id, ...]

behaviors:
  on_new_list_received:
    - Add to update_queue
    - If no current_list active, start processing
    
  process_list:
    - Set as current_list
    - Find all tasks with no dependencies (or all deps completed)
    - Dispatch to appropriate domain agents
    
  on_task_completion:
    - Mark task as completed
    - Check if any blocked tasks can now run
    - Dispatch newly unblocked tasks
    - If all tasks complete, mark list complete and process next

  on_task_failure:
    - Log failure with error details
    - Option 1: Retry with backoff
    - Option 2: Skip and continue (configurable)
    - Option 3: Halt and alert (for critical docs)
    
concurrency_rules:
  - Only ONE update_list active at a time
  - Within a list: parallel execution of independent tasks
  - Dependent tasks wait for prerequisites
```

**Task Distributor Flow Diagram:**

```
                    ┌─────────────────────────────┐
                    │   Receive Update List       │
                    │   from Task Master          │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │   Add to Queue              │
                    │   (FIFO order)              │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
              ┌────▶│   Is Current List Active?   │
              │     └─────────────┬───────────────┘
              │                   │
              │         No ───────┴──────── Yes
              │          │                    │
              │          ▼                    ▼
              │     ┌───────────────┐   ┌───────────────┐
              │     │ Pop Next List │   │ Wait for      │
              │     │ from Queue    │   │ Completion    │
              │     └───────┬───────┘   └───────────────┘
              │             │
              │             ▼
              │     ┌─────────────────────────────┐
              │     │ Find Runnable Tasks         │
              │     │ (deps satisfied)            │
              │     └─────────────┬───────────────┘
              │                   │
              │                   ▼
              │     ┌─────────────────────────────┐
              │     │ Dispatch to Domain Agents   │◀────────┐
              │     │ (parallel if independent)   │         │
              │     └─────────────┬───────────────┘         │
              │                   │                         │
              │                   ▼                         │
              │     ┌─────────────────────────────┐         │
              │     │ Wait for Completion         │         │
              │     │ Callbacks                   │         │
              │     └─────────────┬───────────────┘         │
              │                   │                         │
              │                   ▼                         │
              │     ┌─────────────────────────────┐         │
              │     │ Mark Task Complete          │         │
              │     │ Unlock Dependents           │         │
              │     └─────────────┬───────────────┘         │
              │                   │                         │
              │                   ▼                         │
              │     ┌─────────────────────────────┐         │
              │     │ More Runnable Tasks?        │─── Yes ─┘
              │     └─────────────┬───────────────┘
              │                   │ No
              │                   ▼
              │     ┌─────────────────────────────┐
              │     │ All Tasks Complete?         │─── No ──▶ Error State
              │     └─────────────┬───────────────┘
              │                   │ Yes
              │                   ▼
              │     ┌─────────────────────────────┐
              │     │ Mark List Complete          │
              │     │ Move to completed_lists     │
              │     └─────────────┬───────────────┘
              │                   │
              │                   ▼
              │     ┌─────────────────────────────┐
              └─────│ More Lists in Queue?        │─── No ──▶ Idle
                    └─────────────────────────────┘
```

---

### 3. Execution Layer - Domain Agents (Workflow 3)

Each domain agent is specialized for its documentation area:

#### 3.1 Agent Base Template

```yaml
node_type: n8n-nodes-langchain.agent
model: gemini-2.5-flash | gpt-4o-mini  # Cost-effective for focused tasks

base_tools:
  - github_read_file: Read current file content
  - github_write_file: Write updated content  
  - github_create_branch: Create feature branch for changes
  - matrix_lookup: Query documentation_matrix.json
  - notify_distributor: Report task completion/failure

base_prompt: |
  You are a documentation update agent for the {domain} domain.
  
  Your responsibilities:
  1. Read the current document content
  2. Understand the change context (what triggered this update)
  3. Make targeted, minimal updates to keep documentation accurate
  4. Preserve document structure and formatting
  5. Report completion to the Task Distributor
  
  Rules:
  - Only update what's necessary
  - Don't rewrite entire documents
  - Preserve existing formatting and style
  - Add timestamps to updated sections if appropriate
  - Flag for human review if unsure about changes
```

#### 3.2 Domain-Specific Agents (17 Domains)

| Agent | Domain Tag | Review Interval | Priority | Key Documents |
|-------|------------|-----------------|----------|---------------|
| **Core Agent** | `@core` | 7 days | high | README.md, USER_MANUAL.md |
| **Dashboard Agent** | `@dashboard` | 7 days | high | DASHBOARD_GUIDE.md, DASHBOARD_CLI_PARITY.md |
| **Evidence Agent** | `@evidence` | 14 days | medium | EVIDENCE_*.md guides |
| **API Agent** | `@api` | 7 days | high | API_DOCUMENTATION_*.md |
| **Testing Agent** | `@testing` | 14 days | medium | TESTING_GUIDE.md, MANUAL_TESTING_GUIDE.md |
| **Architecture Agent** | `@architecture` | 21 days | high | architecture/*.md, ORCHESTRATOR_V2_GUIDE.md |
| **Roadmap Agent** | `@roadmap` | 7 days | high | CONSOLIDATED_ROADMAP.md, WAVE_PLAN.md |
| **Parity Agent** | `@parity` | 7 days | high | PARITY-MASTER.md, PARITY-W*.md |
| **Guides Agent** | `@guides` | 14 days | medium | guides/*.md |
| **Incremental Agent** | `@incremental` | 14 days | medium | INCREMENTAL_REVIEW_*.md |
| **Output Agent** | `@output` | 14 days | medium | OUTPUT_*.md |
| **Deployment Agent** | `@deployment` | 14 days | medium | DEPLOYMENT_GUIDE.md, SCALING_GUIDE.md |
| **Task-Tracking Agent** | `@task-tracking` | 3 days | high | task-cards/README.md, INDEX.md |
| **Docs Agent** | `@docs` | 14 days | medium | N8N_*.md, DOCUMENTATION_MATRIX.md |
| **CI/CD Agent** | `@cicd` | 7 days | high | CICD_WORKFLOWS_GUIDE.md |
| **Status Reports Agent** | `@status-reports` | 7 days | high | status-reports/*.md |
| **Assessments Agent** | `@assessments` | 21 days | low | assessments/*.md |

#### 3.3 Agent Task Execution Flow

```yaml
agent_execution:
  1_receive_task:
    input:
      task_id: string
      document: file path
      update_type: enum
      description: what to update
      context: 
        commit_message: string
        changed_files: [paths]
        
  2_fetch_context:
    - Read target document from GitHub
    - Read relevant changed files (if code change triggered update)
    - Load any referenced documents
    
  3_analyze_and_plan:
    - Understand what changed
    - Determine specific sections to update
    - Plan minimal edits
    
  4_execute_update:
    - Create feature branch: docs/auto-update-{task_id}
    - Apply changes to document
    - Commit with descriptive message
    
  5_report_completion:
    callback_to_distributor:
      task_id: string
      status: completed | failed
      branch: branch name (if changes made)
      changes_summary: brief description
      error: null | error message
```

---

### 4. Commit Layer

#### 4.1 Change Aggregator

```yaml
node_type: n8n-nodes-base.code
purpose: Collect all doc update branches from completed update list

trigger: All tasks in update_list completed

logic:
  - Collect all branches created by domain agents
  - Group by update_list_id
  - Prepare for PR creation
  
output:
  update_list_id: string
  branches: [branch_name, ...]
  total_files_changed: number
  summary: aggregated changes description
```

#### 4.2 PR Creator

```yaml
node_type: n8n-nodes-base.httpRequest (GitHub API)
purpose: Create documentation update PR

action:
  - Create new branch: docs/chain-update-{update_list_id}
  - Merge all agent branches into this branch
  - Create PR with:
      title: "docs: automated update chain [{trigger_event}]"
      body: |
        ## 🤖 Automated Documentation Update
        
        Triggered by: {commit_sha or PR number}
        
        ### Changes Made
        {list of documents updated with summaries}
        
        ### Agents Involved
        {list of domain agents that made updates}
        
        ---
        *This PR was automatically generated by the Documentation Update Chain*
      
      labels: ["documentation", "automated"]
      reviewers: [] # Optional: add human reviewers
```

#### 4.3 Auto-Merge (Optional)

```yaml
node_type: n8n-nodes-base.httpRequest
purpose: Auto-merge doc update PRs (if configured)

conditions:
  - All CI checks pass
  - No conflicts
  - auto_merge_enabled: true in config

action:
  - Enable auto-merge on PR
  - Or merge immediately if checks already pass
```

---

## 📊 Data Structures

### Update List Schema

```json
{
  "update_list_id": "ul-2025-12-07-abc123",
  "created_at": "2025-12-07T10:30:00Z",
  "status": "pending | in_progress | completed | failed",
  "trigger": {
    "type": "push | pull_request",
    "ref": "refs/heads/main",
    "commit_sha": "abc123def456",
    "pr_number": null,
    "author": "developer-username",
    "message": "feat(dashboard): add new API endpoint"
  },
  "affected_files": [
    "webdashboard/app.py",
    "webdashboard/routes/api.py"
  ],
  "tasks": [
    {
      "task_id": "task-001",
      "document": "docs/DASHBOARD_GUIDE.md",
      "owner": "@dashboard",
      "update_type": "UPDATE_REFERENCE",
      "description": "Add documentation for new API endpoint",
      "depends_on": [],
      "status": "pending | running | completed | failed",
      "assigned_at": null,
      "completed_at": null,
      "result": {
        "branch": null,
        "changes_made": null,
        "error": null
      }
    }
  ],
  "completion": {
    "completed_at": null,
    "total_tasks": 3,
    "completed_tasks": 0,
    "failed_tasks": 0,
    "pr_number": null
  }
}
```

### Task Completion Callback Schema

```json
{
  "task_id": "task-001",
  "update_list_id": "ul-2025-12-07-abc123",
  "status": "completed",
  "agent": "@dashboard",
  "branch": "docs/auto-update-task-001",
  "changes_made": [
    {
      "file": "docs/DASHBOARD_GUIDE.md",
      "sections_updated": ["API Reference", "Endpoints List"],
      "lines_changed": 15
    }
  ],
  "execution_time_ms": 4500,
  "error": null
}
```

---

## � Proactive Maintenance Workflows

### 5. Staleness Review (Workflow 5)

> **Full specification:** See [N8N_STALENESS_REVIEW_BLUEPRINT.md](./N8N_STALENESS_REVIEW_BLUEPRINT.md)  
> **Builder prompt:** See [N8N_STALENESS_REVIEW_BUILDER_PROMPT.md](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md)

```yaml
purpose: Proactive detection of documentation that may have drifted out of sync
schedule: Weekly (Sunday 2 AM UTC)
trigger: Also available via manual webhook at /staleness-review
nodes: 22 total

workflow:
  1_schedule_trigger: Weekly cron job
  2_fetch_matrix: Load documentation_matrix.json with staleness_config
  3_for_each_domain:
    - Get last activity date from GitHub API
    - Compare against review_interval_days
    - Skip if within interval
  4_fetch_recent_changes: For domains needing review
  5_ai_staleness_assessment: Score staleness 0.0 - 1.0
  6_route_by_score:
    - >= 0.7: Auto-update via Task Distributor
    - >= 0.5: Create GitHub issue for manual review
    - >= 0.3: Create low-priority issue
    - < 0.3: Log as healthy

staleness_config:
  thresholds:
    auto_update: 0.7
    manual_review: 0.5
    create_issue: 0.3
    healthy: 0.0
  default_review_interval_days: 7
  max_inactivity_before_alert_days: 21
  ignore_patterns:
    - "test_*.py"
    - "tests/**"
    - "*.md"  # Only check code changes for staleness
```

### 6. State Reconciliation (Workflow 6)

> **Full specification:** See [N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md](./N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md)  
> **Minimal reference:** See [N8N_STATE_RECONCILIATION_MINIMAL.md](./N8N_STATE_RECONCILIATION_MINIMAL.md)

```yaml
purpose: Ensure task card status matches claimed completion percentages
schedule: Daily (4 AM UTC)
trigger: Also available via manual webhook at /state-reconciliation
nodes: 28 total

workflow:
  1_fetch_all_files: Git tree recursive to get all files
  2_filter_task_cards: Extract task card paths
  3_process_each_card:
    - Fetch content via GitHub API
    - Parse Status: field using regex
    - Normalize status values
  4_aggregate_status: Group by directory
  5_process_status_reports: (parallel branch)
    - Fetch status report contents
    - Extract current status and completion %
  6_fetch_target_documents:
    - task-cards/README.md
    - task-cards/INDEX.md
    - docs/CONSOLIDATED_ROADMAP.md
  7_find_all_mismatches:
    - File count discrepancies
    - Completion percentage drifts (>5% tolerance)
    - Status accuracy issues
    - Roadmap vs index inconsistencies
  8_generate_corrections: AI agent creates update tasks
  9_send_to_distributor: POST to task distributor

state_reconciliation_config:
  rollup_targets:
    task_cards_to_indexes:
      source_patterns: ["task-cards/**/*.md"]
      target_documents: ["task-cards/README.md", "task-cards/INDEX.md"]
      aggregation: "count_by_status"
    indexes_to_roadmap:
      source_patterns: ["task-cards/README.md", "task-cards/INDEX.md"]
      target_documents: ["docs/CONSOLIDATED_ROADMAP.md"]
      aggregation: "summarize_progress"
    status_reports_to_roadmap:
      source_patterns: ["docs/status-reports/*.md"]
      target_documents: ["docs/CONSOLIDATED_ROADMAP.md"]
      aggregation: "latest_status"

status_extraction_patterns:
  task_card_status: "^Status:\\s*(.+)$"
  completion_percentage: "(\\d+)%\\s*(?:complete|done)"
  checkbox_count: "- \\[([x ])\\]"
  
status_mappings:
  "complete": "Complete"
  "done": "Complete"
  "✅ complete": "Complete"
  "in progress": "In Progress"
  "🔄 in progress": "In Progress"
  "not started": "Not Started"
  "ready": "Not Started"
  "blocked": "Blocked"
  "deferred": "Deferred"
```

---

## 🔧 N8N Workflow Structure

### Workflow 1: Doc Chain - Trigger

```
[Webhook: GitHub Push/Merge]
           │
           ▼
[Code: Filter Valid Events]
           │ (stops on automated [n8n] commits)
           ▼
[Code: Parse Changed Files]
           │
           ▼
[Code: Matrix Lookup]
           │
           ▼
[IF: Has Affected Docs?]──── No ────▶ [End]
           │
          Yes
           │
           ▼
[AI Agent: Task Master]
           │
           ▼
[HTTP: Post to Distributor Workflow]
           │
           ▼
[End: Acknowledgment]
```

### Workflow 2: Task Distributor

```
[Webhook: Receive Update List]
           │
           ▼
[Code: Add to Queue]
           │
           ▼
[Code: Check Active List]
           │
    ┌──────┴──────┐
    │             │
  Active       No Active
    │             │
    ▼             ▼
[Wait: Poll   [Code: Pop & Start]
 for signal]       │
                   ▼
           [Code: Get Runnable Tasks]
                   │
                   ▼
           [Split: For Each Task]
                   │
           ┌───────┴───────┐
           ▼               ▼
    [Execute Workflow:  [Execute Workflow:
     Domain Agent 1]     Domain Agent 2]
           │               │
           └───────┬───────┘
                   ▼
           [Merge: Wait All]
                   │
                   ▼
           [Code: Update State]
                   │
                   ▼
           [IF: More Tasks?]
                   │
           ┌───────┴───────┐
          Yes              No
           │               │
           ▼               ▼
    [Loop Back]    [Code: Complete List]
                          │
                          ▼
                   [Execute: PR Creator]
                          │
                          ▼
                   [IF: More in Queue?]
                          │
                   ┌──────┴──────┐
                  Yes            No
                   │              │
                   ▼              ▼
            [Loop Back]       [End: Idle]
```

### Sub-Workflow: Domain Agent (Template)

```
[Webhook: Receive Task]
           │
           ▼
[HTTP: Fetch Document from GitHub]
           │
           ▼
[HTTP: Fetch Changed Files Context]
           │
           ▼
[AI Agent: Analyze & Update]
           │
           ▼
[IF: Changes Needed?]
           │
    ┌──────┴──────┐
   Yes            No
    │              │
    ▼              ▼
[HTTP: Create   [Code: Skip]
 Branch]            │
    │               │
    ▼               │
[HTTP: Commit      │
 Changes]          │
    │               │
    └───────┬───────┘
            ▼
[HTTP: Callback to Distributor]
            │
            ▼
[End]
```

### Workflow 4: Doc Chain - Errors

```
[Execute Workflow Trigger: Catch All Errors]
           │
           ▼
[Code: Parse Error Details]
           │
           ▼
[IF: Critical Error?]
           │
    ┌──────┴──────┐
   Yes            No
    │              │
    ▼              ▼
[HTTP: Create   [Code: Log Warning]
 GitHub Issue]      │
    │               │
    └───────┬───────┘
            ▼
[Code: Update Task Status to Failed]
            │
            ▼
[HTTP: Notify Distributor]
            │
            ▼
[End]
```

### Workflow 5: Doc Chain - Staleness Review

```
[Schedule: Weekly Sunday 2AM UTC]  [Webhook: /staleness-review]
           │                                │
           └────────────┬───────────────────┘
                        ▼
             [HTTP: Fetch Matrix]
                        │
                        ▼
             [Code: Get Domains Needing Review]
                        │
                        ▼
             [Split: For Each Domain]
                        │
                        ▼
             [HTTP: Get Last Activity]
                        │
                        ▼
             [Code: Calculate Inactivity]
                        │
                        ▼
             [IF: Needs Review?]
                        │
              ┌─────────┴─────────┐
             Yes                  No
              │                    │
              ▼                    ▼
    [HTTP: Fetch Changes]     [Skip Domain]
              │
              ▼
    [AI Agent: Staleness Assessment]
              │
              ▼
    [Switch: Route By Score]
              │
    ┌─────────┼─────────────┐
    ▼         ▼             ▼
[>=0.7]    [>=0.5]       [<0.3]
Auto-     Create      Log Healthy
Update    Issue
    │         │
    ▼         ▼
[Send to  [HTTP: Create
Distrib.]  Issue]
```

### Workflow 6: Doc Chain - State Reconciliation

```
[Schedule: Daily 4AM UTC]  [Webhook: /state-reconciliation]
           │                          │
           └──────────┬───────────────┘
                      ▼
           [Code: Workflow Config]
                      │
                      ▼
           [HTTP: List All Files]
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
[Filter Task Cards]      [Filter Status Reports]
         │                         │
         ▼                         ▼
[Loop: Fetch & Parse]    [Loop: Fetch & Parse]
         │                         │
         ▼                         ▼
[Aggregate Status]       [Aggregate Status]
         │                         │
         └──────────┬──────────────┘
                    ▼
         [Fetch Target Documents]
         (README, INDEX, ROADMAP)
                    │
                    ▼
         [Code: Find All Mismatches]
                    │
                    ▼
         [IF: Has Mismatches?]
                    │
         ┌──────────┴──────────┐
        Yes                   No
         │                     │
         ▼                     ▼
[AI: Generate            [Log In Sync]
 Corrections]
         │
         ▼
[HTTP: Send to Distributor]
```

---

## 📈 Monitoring & Observability

### Metrics to Track

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `update_lists_queued` | Lists waiting in queue | > 5 |
| `active_list_duration` | Time to complete a list | > 10 min |
| `task_success_rate` | % tasks completing successfully | < 95% |
| `avg_task_duration` | Average time per task | > 60 sec |
| `agent_error_rate` | Errors by domain agent | > 10% |
| `pr_merge_rate` | Auto-merged vs manual review | < 80% auto |
| `staleness_score_avg` | Average staleness across domains | > 0.5 |
| `reconciliation_mismatches` | Count of detected mismatches | > 10 |
| `domains_reviewed` | Domains checked per staleness run | < 10 (of 17) |

### Logging

```yaml
log_structure:
  level: info | warn | error
  timestamp: ISO-8601
  component: trigger | task_master | distributor | agent:{domain} | commit | staleness | reconciliation
  update_list_id: string
  task_id: string (if applicable)
  workflow: 1-6
  message: string
  metadata: {...}
```

### Alerts

```yaml
alerts:
  - name: queue_backup
    condition: update_lists_queued > 5 for 10m
    action: Notify via Slack/Email
    
  - name: task_failure_spike
    condition: task_success_rate < 90% in 1h
    action: Pause queue, notify team
    
  - name: agent_timeout
    condition: task running > 5m
    action: Kill task, retry, or skip
    
  - name: high_staleness
    condition: staleness_score_avg > 0.6 for 7d
    action: Create summary issue, notify team
    
  - name: reconciliation_drift
    condition: reconciliation_mismatches > 20
    action: Create urgent issue, flag for manual review
```

---

## 🚀 Implementation Status

### Phase 1: Foundation ✅ Complete
- [x] Set up GitHub webhook in n8n
- [x] Implement Change Parser node with feedback loop prevention
- [x] Create Matrix Lookup node
- [x] Basic end-to-end test with logging

### Phase 2: Orchestration ✅ Complete
- [x] Build Task Master Agent with Gemini 2.5 Flash
- [x] Implement Task Distributor state management
- [x] Create queue and dependency tracking
- [x] Test with mock domain agents

### Phase 3: Domain Agents ✅ Complete
- [x] Implement all 17 domain agents
- [x] Add GitHub read/write capabilities
- [x] Implement completion callbacks
- [x] Test update flow end-to-end

### Phase 4: Commit & Merge ✅ Complete
- [x] Build Change Aggregator
- [x] Implement PR Creator
- [x] Add auto-merge logic (configurable)
- [x] Full integration testing

### Phase 5: Proactive Maintenance ✅ Complete
- [x] Staleness Review workflow (Workflow 5)
- [x] State Reconciliation workflow (Workflow 6)
- [x] Fine-tune agent prompts
- [x] Add error handling workflow (Workflow 4)

### Phase 6: Production Refinement 🔄 Ongoing
- [ ] Add monitoring dashboard
- [ ] Create runbooks for common issues
- [ ] Performance optimization
- [ ] Cost tracking and optimization

---

## 🔒 Security Considerations

1. **GitHub Token Scoping**
   - Use fine-grained PAT with minimal permissions
   - Read: code, pull requests
   - Write: only to docs/ and specific doc files
   
2. **Webhook Verification**
   - Use secret query parameter for webhook validation
   - Validate in Filter Valid Events node
   
3. **Rate Limiting**
   - Limit update chain frequency (debounce rapid commits)
   - Respect GitHub API rate limits
   - Filter automated [n8n] commits to prevent loops
   
4. **Change Boundaries**
   - Agents can only modify documentation files
   - Blocklist: *.py, *.js, *.json (except matrix), *.yml
   - Allowlist: *.md, task-cards/**/*.md

---

## 📝 Configuration

### n8n Cloud Setup

> ⚠️ **n8n Cloud Limitation:** Environment variables (`$env.*`) are blocked in node expressions on n8n Cloud. Use hardcoded URLs instead.

**Webhook Base URL:** `https://gitlitreview.app.n8n.cloud`

### Credentials Required

| Credential | Type | Purpose |
|------------|------|---------|
| GitHub API Token | Header Auth or Manual Headers | Contents read/write |
| Gemini API | Google Gemini API | AI agent operations |

**Recommended:** Use manual headers in HTTP Request nodes due to n8n Cloud credential resolution issues:
- Set Authentication: `None`
- Add headers directly:
  - `Authorization: Bearer github_pat_YOUR_TOKEN_HERE`
  - `Accept: application/vnd.github.v3+json`

### Feature Flags

```json
{
  "enabled_domains": [
    "@core", "@dashboard", "@api", "@evidence", "@testing",
    "@architecture", "@roadmap", "@parity", "@guides", "@incremental",
    "@output", "@deployment", "@task-tracking", "@docs", "@cicd",
    "@status-reports", "@assessments"
  ],
  "auto_merge": false,
  "require_human_review": ["README.md", "docs/USER_MANUAL.md"],
  "skip_on_label": ["skip-doc-update"],
  "debug_mode": false,
  "staleness_review_enabled": true,
  "state_reconciliation_enabled": true
}
```

---

## 🔗 Integration Points

### Required Repository Files

| File | Purpose | Version |
|------|---------|---------|
| `docs/documentation_matrix.json` | Dependency mappings, staleness config, cascade rules | v1.3 |
| `docs/DOCUMENTATION_MATRIX.md` | Human-readable matrix | - |
| `.github/workflows/` | Optional CI integration | - |

### GitHub Webhook Configuration

```
Payload URL: https://gitlitreview.app.n8n.cloud/webhook/github-doc-trigger?secret=YOUR_SECRET
Content type: application/json
Events: 
  - Push
  - Pull requests (closed/merged only)
```

---

## 📚 Related Documentation

| Document | Description |
|----------|-------------|
| [N8N_AI_BUILDER_PROMPT.md](./N8N_AI_BUILDER_PROMPT.md) | Step-by-step workflow building prompts |
| [N8N_STALENESS_REVIEW_BLUEPRINT.md](./N8N_STALENESS_REVIEW_BLUEPRINT.md) | Detailed Workflow 5 specification |
| [N8N_STALENESS_REVIEW_BUILDER_PROMPT.md](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md) | Builder prompt for Workflow 5 |
| [N8N_STALENESS_REVIEW_MINIMAL.md](./N8N_STALENESS_REVIEW_MINIMAL.md) | Quick reference for Workflow 5 |
| [N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md](./N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md) | Full builder prompt for Workflow 6 |
| [N8N_STATE_RECONCILIATION_MINIMAL.md](./N8N_STATE_RECONCILIATION_MINIMAL.md) | Quick reference for Workflow 6 |
| [CURRENT_STATE_SYNC_ANALYSIS.md](./CURRENT_STATE_SYNC_ANALYSIS.md) | Gap analysis and state sync strategy |
| [documentation_matrix.json](./documentation_matrix.json) | Machine-readable configuration |

---

*Blueprint Version: 2.0*  
*Created: 2025-12-07*  
*Last Updated: 2025-12-20*  
*Status: Production Ready - 6 Workflows Implemented*
