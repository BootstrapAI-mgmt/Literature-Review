# 🔄 N8N Documentation Update Chain Blueprint

> **Purpose:** Automate documentation updates when code or documentation changes are pushed/merged to GitHub, using a multi-agent orchestration system in n8n.

---

## 📋 Executive Summary

This system creates an automated "update chain" triggered by GitHub events (push/merge) that:
1. Detects what changed (code or docs)
2. Determines which documentation needs updating based on the dependency matrix
3. Orchestrates multiple documentation agents to update in the correct cascade order
4. Ensures sequential completion before proceeding to dependent updates

**Scope:** Documentation and record-keeping only - no core functionality changes.

---

## 🏗️ System Architecture

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
│                               N8N WORKFLOW                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         1. TRIGGER LAYER                               │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐   │ │
│  │  │ GitHub Webhook  │───▶│ Change Parser   │───▶│ Matrix Lookup    │   │ │
│  │  │ Receiver        │    │ (files changed) │    │ (find deps)      │   │ │
│  │  └─────────────────┘    └─────────────────┘    └──────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      2. ORCHESTRATION LAYER                            │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    TASK MASTER AGENT                             │  │ │
│  │  │  • Analyzes change impact                                        │  │ │
│  │  │  • Generates Update List with execution order                    │  │ │
│  │  │  • Submits to Task Distributor                                   │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                              │                                         │ │
│  │                              ▼                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                  TASK DISTRIBUTOR AGENT                          │  │ │
│  │  │  • Maintains Update List Queue (FIFO)                            │  │ │
│  │  │  • Executes lists serially (one complete before next)            │  │ │
│  │  │  • Tracks task completion within each list                       │  │ │
│  │  │  • Unlocks dependent tasks when prerequisites complete           │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                       3. EXECUTION LAYER                               │ │
│  │                                                                        │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │ @core    │  │@dashboard│  │@evidence │  │ @api     │  │ @parity  │ │ │
│  │  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │ │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │ │
│  │       │             │             │             │             │        │ │
│  │       └─────────────┴─────────────┴─────────────┴─────────────┘        │ │
│  │                              │                                         │ │
│  │                              ▼                                         │ │
│  │                    Completion Callbacks                                │ │
│  │                    (back to Distributor)                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        4. COMMIT LAYER                                 │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐   │ │
│  │  │ Change          │───▶│ PR Creator      │───▶│ Auto-Merge       │   │ │
│  │  │ Aggregator      │    │ (doc updates)   │    │ (if configured)  │   │ │
│  │  └─────────────────┘    └─────────────────┘    └──────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Component Specifications

### 1. Trigger Layer

#### 1.1 GitHub Webhook Receiver
```yaml
node_type: n8n-nodes-base.webhook
trigger: push, pull_request (merged)
config:
  path: /github-doc-trigger
  method: POST
  authentication: GitHub signature verification
  
output:
  event_type: push | pull_request
  repository: owner/repo
  branch: main
  commits: [commit_sha, ...]
  changed_files: [path, ...]
  author: username
  timestamp: ISO-8601
```

#### 1.2 Change Parser
```yaml
node_type: n8n-nodes-base.code
purpose: Extract and categorize changed files

logic:
  - Fetch commit details via GitHub API
  - Categorize files:
      - code_changes: *.py, *.js, *.json (non-doc)
      - doc_changes: *.md
      - config_changes: docker-compose.yml, requirements.txt
  - Filter to relevant paths (literature_review/, webdashboard/, docs/)
  
output:
  trigger_type: code | docs | config
  changed_files: [
    { path: "...", type: "code|docs|config", action: "added|modified|deleted" }
  ]
```

#### 1.3 Matrix Lookup
```yaml
node_type: n8n-nodes-base.code
purpose: Query documentation_matrix.json for dependencies

inputs:
  - changed_files from Change Parser
  
logic:
  - Load docs/documentation_matrix.json
  - For each changed file:
      - If code file: lookup script_to_docs mapping
      - If doc file: lookup document dependencies (reverse cascade)
  - Deduplicate and sort by priority level (L1 → L2 → L3)
  
output:
  affected_docs: [
    { path: "...", owner: "@domain", level: "L1|L2|L3", depends_on: [...] }
  ]
  cascade_order: [[L1 docs], [L2 docs], [L3 docs]]
```

---

### 2. Orchestration Layer

#### 2.1 Task Master Agent

```yaml
node_type: n8n-nodes-langchain.agent
model: gpt-4o | claude-3.5-sonnet
purpose: Analyze changes and generate ordered update list

system_prompt: |
  You are the Task Master Agent for documentation updates.
  
  Your responsibilities:
  1. Analyze the GitHub change event and affected documentation list
  2. Determine what updates are needed for each document
  3. Generate an Update List with proper execution order
  4. Respect cascade dependencies (L1 before L2, L2 before L3)
  
  Update types you can assign:
  - SYNC_STATUS: Update status/completion markers
  - UPDATE_REFERENCE: Update code references or examples
  - UPDATE_TODO: Mark tasks complete or add new ones
  - UPDATE_ARCHITECTURE: Reflect structural changes
  - UPDATE_ROADMAP: Update progress/milestones
  - REVIEW_NEEDED: Flag for human review (complex changes)

inputs:
  - event_summary: What changed (commit message, PR title)
  - changed_files: List of modified files
  - affected_docs: Documents that need updating
  - cascade_order: Execution priority levels

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

### 3. Execution Layer - Domain Agents

Each domain agent is specialized for its documentation area:

#### 3.1 Agent Base Template

```yaml
node_type: n8n-nodes-langchain.agent
model: gpt-4o-mini | claude-3.5-haiku  # Cost-effective for focused tasks

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

#### 3.2 Domain-Specific Agents

| Agent | Domain Tag | Specialized Skills | Documents |
|-------|------------|-------------------|-----------|
| **Core Agent** | `@core` | README updates, feature summaries | README.md, USER_MANUAL |
| **Dashboard Agent** | `@dashboard` | UI/API documentation | DASHBOARD_GUIDE, CLI_PARITY |
| **Evidence Agent** | `@evidence` | Scoring methodology docs | EVIDENCE_* guides |
| **API Agent** | `@api` | API reference updates | API_DOCUMENTATION_* |
| **Testing Agent** | `@testing` | Test documentation | TESTING_GUIDE, test READMEs |
| **Architecture Agent** | `@architecture` | System design docs | architecture/* |
| **Roadmap Agent** | `@roadmap` | Progress tracking | CONSOLIDATED_ROADMAP |
| **Parity Agent** | `@parity` | Task card updates | PARITY-*.md task cards |
| **Guides Agent** | `@guides` | User guides | guides/* |
| **Incremental Agent** | `@incremental` | Incremental review docs | INCREMENTAL_REVIEW_* |

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

## 🔧 N8N Workflow Structure

### Main Workflow: Documentation Update Chain

```
[Webhook: GitHub Push/Merge]
           │
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

### Sub-Workflow: Task Distributor

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

### Logging

```yaml
log_structure:
  level: info | warn | error
  timestamp: ISO-8601
  component: trigger | task_master | distributor | agent:{domain} | commit
  update_list_id: string
  task_id: string (if applicable)
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
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up GitHub webhook in n8n
- [ ] Implement Change Parser node
- [ ] Create Matrix Lookup node
- [ ] Basic end-to-end test with logging only

### Phase 2: Orchestration (Week 2)
- [ ] Build Task Master Agent with basic prompts
- [ ] Implement Task Distributor state management
- [ ] Create queue and dependency tracking
- [ ] Test with mock domain agents

### Phase 3: Domain Agents (Week 3)
- [ ] Implement @core and @dashboard agents first
- [ ] Add GitHub read/write capabilities
- [ ] Implement completion callbacks
- [ ] Test update flow end-to-end

### Phase 4: Commit & Merge (Week 4)
- [ ] Build Change Aggregator
- [ ] Implement PR Creator
- [ ] Add auto-merge logic (optional)
- [ ] Full integration testing

### Phase 5: Expansion (Week 5+)
- [ ] Add remaining domain agents
- [ ] Fine-tune agent prompts
- [ ] Add monitoring dashboard
- [ ] Documentation and runbooks

---

## 🔒 Security Considerations

1. **GitHub Token Scoping**
   - Use fine-grained PAT with minimal permissions
   - Read: code, pull requests
   - Write: only to docs/ and specific doc files
   
2. **Webhook Verification**
   - Validate GitHub signature on all webhooks
   - Reject unsigned or invalid requests
   
3. **Rate Limiting**
   - Limit update chain frequency (debounce rapid commits)
   - Respect GitHub API rate limits
   
4. **Change Boundaries**
   - Agents can only modify documentation files
   - Blocklist: *.py, *.js, *.json (except matrix), *.yml
   - Allowlist: *.md, task-cards/**/*.md

---

## 📝 Configuration

### Environment Variables

```bash
# GitHub
GITHUB_WEBHOOK_SECRET=<secret>
GITHUB_PAT=<personal-access-token>
GITHUB_REPO=BootstrapAI-mgmt/Literature-Review

# n8n
N8N_WEBHOOK_BASE_URL=https://n8n.example.com
N8N_ENCRYPTION_KEY=<key>

# AI Providers
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>

# Configuration
AUTO_MERGE_ENABLED=false
MAX_QUEUE_SIZE=10
TASK_TIMEOUT_SECONDS=300
```

### Feature Flags

```json
{
  "enabled_domains": ["@core", "@dashboard", "@api"],
  "auto_merge": false,
  "require_human_review": ["README.md", "USER_MANUAL.md"],
  "skip_on_label": ["skip-doc-update"],
  "debug_mode": false
}
```

---

## 🔗 Integration Points

### Required Repository Files

| File | Purpose |
|------|---------|
| `docs/documentation_matrix.json` | Dependency mappings |
| `docs/DOCUMENTATION_MATRIX.md` | Human-readable matrix |
| `.github/workflows/` | Optional CI integration |

### GitHub Webhook Configuration

```
Payload URL: https://n8n.example.com/webhook/github-doc-trigger
Content type: application/json
Secret: <GITHUB_WEBHOOK_SECRET>
Events: 
  - Push
  - Pull requests (closed/merged only)
```

---

*Blueprint Version: 1.0*
*Created: 2025-12-07*
*Status: Draft - Ready for Implementation*
