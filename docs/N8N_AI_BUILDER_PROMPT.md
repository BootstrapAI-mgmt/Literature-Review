# N8N AI Builder Prompts: Documentation Update Chain

> **Instructions:** This system requires **6 separate workflows** built one at a time. Each prompt below is designed for a single n8n canvas. Create each workflow manually in n8n, then use the corresponding prompt to build it.
>
> **Note:** Workflows 1-4 handle event-driven documentation updates (triggered by GitHub pushes/merges). Workflow 5 adds proactive staleness detection on a schedule. Workflow 6 ensures current state accuracy through reconciliation. See:
> - [N8N_STALENESS_REVIEW_BUILDER_PROMPT.md](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md) for Workflow 5
> - [N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md](./N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md) for Workflow 6

---

## 🏗️ Architecture Overview (Reference for All Prompts)

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  GitHub     │────▶│  Doc Chain -    │────▶│  Doc Chain - │
│  Webhook    │     │  Trigger        │     │  Distributor │◀───────────────┐
└─────────────┘     └─────────────────┘     └──────┬───────┘                │
                                                   │                        │
                           ┌───────────────────────┘                        │
                           ▼                                                │
                    ┌──────────────┐     callback     ┌──────────────┐     │
                    │  Doc Chain - │─────────────────▶│  Distributor │     │
                    │  Agent       │                  │  (continues) │     │
                    └──────────────┘                  └──────────────┘     │
                           │                                                │
                           ▼                                                │
                    ┌──────────────┐                                       │
                    │  Doc Chain - │ (catches errors from all)             │
                    │  Errors      │                                       │
                    └──────────────┘                                       │
                                                                           │
┌──────────────────────────────────────────────────────────────────────────┘
│                                                                          │
│  ┌───────────────┐     ┌─────────────────┐     (tasks)                   │
│  │  Schedule     │────▶│  Doc Chain -    │─────────────┘                 │
│  │  (Weekly)     │     │  Staleness      │                               │
│  └───────────────┘     │  Review         │────▶ GitHub Issues            │
│                        └─────────────────┘      (if manual review needed)│
│                                                                          │
│  ┌───────────────┐     ┌─────────────────┐     (tasks)                   │
│  │  Schedule     │────▶│  Doc Chain -    │─────────────┘
│  │  (Daily)      │     │  State          │
│  └───────────────┘     │  Reconciliation │────▶ Fixes mismatches
                         └─────────────────┘      (status vs claimed %)
```

**Workflow Communication:**
- Trigger → Distributor: HTTP POST to `/webhook/task-distributor`
- Distributor → Agent: HTTP POST to `/webhook/domain-agent`
- Agent → Distributor: HTTP POST to `/webhook/task-done-{task_id}`
- Staleness Review → Distributor: HTTP POST to `/webhook/task-distributor` (same endpoint)
- State Reconciliation → Distributor: HTTP POST to `/webhook/task-distributor` (same endpoint)

**Webhook Base URL:**
- For this project: `https://gitlitreview.app.n8n.cloud`
- Replace with your n8n instance URL if different

> ⚠️ **n8n Cloud Limitation:** Environment variables (`$env.*`) are blocked in node expressions on n8n Cloud. Use hardcoded URLs instead of `{{$env.N8N_WEBHOOK_URL}}`.

---

## 🔑 Credential Setup

### 1. GitHub API Token (for committing doc updates)

> ⚠️ **n8n Cloud Workaround:** The n8n credential system (Header Auth / Multiple Headers Auth) has known issues on n8n Cloud where credentials aren't properly resolved in HTTP Request nodes. **We recommend using manual headers instead** (see Workflow 3 nodes for the exact configuration).

**Option A: Manual Headers (Recommended)**

Instead of using the credential system, add headers directly in each HTTP Request node:
- Set Authentication: `None`
- Under "Send Headers" → "Specify Headers" → "Using Fields":
  - Name: `Authorization` | Value: `Bearer github_pat_YOUR_TOKEN_HERE`
  - Name: `Accept` | Value: `application/vnd.github.v3+json`

**Option B: Credential-Based (may have issues)**

**Create in n8n:** Credentials → Add Credential → **Header Auth** (or **Multiple Headers Auth** if that's what n8n offers)

| Setting | Value |
|---------|-------|
| **Credential Name** | `GitHub API Token` |
| **Name** | `Authorization` |
| **Value** | `Bearer ghp_YOUR_TOKEN_HERE` |

> **Note:** Some HTTP Request nodes may only offer "Multiple Headers Auth" instead of "Header Auth" in the credential type dropdown. Both work the same way - just create the credential with the same Name/Value pair.

**Token Requirements:** Create a GitHub PAT at *Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens* with:
- Repository access: `BootstrapAI-mgmt/Literature-Review`
- Permissions: `Contents: Read and write`

### 2. Gemini API (for AI agents)

**Create in n8n:** Credentials → Add Credential → **Google Gemini API**

| Setting | Value |
|---------|-------|
| **Credential Name** | `Gemini API` |
| **API Key** | Your Google AI API key |

Get your key at: https://makersuite.google.com/app/apikey

### 3. (Optional) GitHub Webhook Secret

For validating incoming webhooks from GitHub, add a secret query parameter to your webhook URL:
```
https://your-n8n.com/webhook/github-doc-trigger?secret=YOUR_SECRET
```

Then in the Trigger workflow, add validation in the Filter node.

---

## Pre-Setup Checklist

Before using these prompts:
1. [ ] Create 6 empty workflows in n8n named exactly:
   - `Doc Chain - Trigger`
   - `Doc Chain - Distributor`
   - `Doc Chain - Agent`
   - `Doc Chain - Errors`
   - `Doc Chain - Staleness Review` (see [separate prompt](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md))
   - `Doc Chain - State Reconciliation` (see [separate prompt](./N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md))
2. [ ] Configure environment variables in n8n Settings
3. [ ] Create `GitHub API Token` credential (Header Auth)
4. [ ] Create `Gemini API` credential

---

# WORKFLOW 1: Doc Chain - Trigger
**Open the "Doc Chain - Trigger" canvas, then use this prompt:**

```
Build a workflow that receives GitHub webhooks and identifies which documentation files need updating.

CONTEXT: This is workflow 1 of 6 in a documentation auto-update system. This workflow receives GitHub push/merge events, looks up a dependency matrix to find affected docs, uses AI to create a task list, then sends it to a separate "Distributor" workflow via HTTP.

BUILD THESE NODES:

1. WEBHOOK node named "GitHub Webhook"
   - Path: /github-doc-trigger
   - Method: POST
   - Respond: Immediately

2. CODE node named "Filter Valid Events"
   - Mode: Run Once for All Items
   - JavaScript:
   ```javascript
   // CRITICAL: This filter prevents feedback loops from n8n's own commits
   const body = $input.first().json.body || $input.first().json;
   
   // Check if this is a valid event (has commits or merged PR)
   const hasCommits = Array.isArray(body.commits) && body.commits.length > 0;
   const isMergedPR = body.pull_request?.merged === true;
   
   if (!hasCommits && !isMergedPR) {
     return []; // No valid event - return empty to stop workflow
   }
   
   // Check if this is an n8n automated commit (feedback loop prevention)
   const headCommitMsg = body.head_commit?.message || '';
   if (headCommitMsg.startsWith('[n8n]')) {
     return []; // n8n commit - return empty to stop workflow
   }
   
   // Also check all individual commits
   const allCommitsAreN8n = hasCommits && body.commits.every(c => 
     (c.message || '').startsWith('[n8n]')
   );
   if (allCommitsAreN8n) {
     return []; // All commits are n8n - return empty to stop workflow
   }
   
   // Valid event - pass through
   return [{ json: { body, is_valid: true } }];
   ```
   - NOTE: Returns empty array to stop workflow for invalid/n8n events
   - Connect to Parse Changes on success

3. CODE node named "Parse Changes"
   - JavaScript:
   const event = $input.first().json.body;  // NOTE: .body is required - GitHub data is nested
   const files = [];
   if (event.commits) {
     event.commits
       // Filter out ALL n8n automated commits to prevent feedback loops
       .filter(c => !c.message?.startsWith('[n8n]'))
       .forEach(c => {
         files.push(...(c.added || []), ...(c.modified || []));
       });
   }
   // Filter out the matrix file itself - it's internal tracking, not a trigger
   const filteredFiles = [...new Set(files)].filter(f => 
     f !== 'docs/documentation_matrix.json'
   );
   return {
     commit_sha: event.after || event.pull_request?.merge_commit_sha,
     author: event.pusher?.name || event.pull_request?.user?.login,
     message: event.head_commit?.message || event.pull_request?.title,
     changed_files: filteredFiles
   };

4. HTTP REQUEST node named "Fetch Matrix"
   - Method: GET
   - URL: https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json

5. CODE node named "Find Affected Docs"
   - JavaScript:
   // NOTE: Fetch Matrix returns JSON as a string in .data property - must parse it!
   const matrixRaw = $('Fetch Matrix').first().json;
   const matrix = typeof matrixRaw.data === 'string' ? JSON.parse(matrixRaw.data) : matrixRaw;
   const changes = $('Parse Changes').first().json;
   const affected = new Set();
   const newDocs = [];  // Track new docs not yet in matrix
   
   // Helper to get documents array from owner_domains (handles both old array and new object format)
   const getDomainDocs = (domainInfo) => {
     return Array.isArray(domainInfo) ? domainInfo : (domainInfo?.documents || []);
   };
   
   for (const file of changes.changed_files) {
     // Check 1: If a script changed, find docs that depend on it
     for (const [script, docs] of Object.entries(matrix.script_to_docs || {})) {
       // Handle both exact matches and partial matches (for directories like .github/workflows/)
       const scriptBase = script.replace('.py','').replace('.yml','').replace('.yaml','');
       if (file === script || file.includes(scriptBase) || (script.endsWith('/') && file.startsWith(script))) {
         docs.forEach(d => affected.add(d));
       }
     }
     
     // Check 2: If the changed file IS a document in the matrix, include it
     const docEntry = matrix.documents?.find(d => file.endsWith(d.path) || file === d.path);
     if (docEntry) {
       affected.add(docEntry.path);
       // Also add any docs that depend on this doc (reverse dependency lookup)
       matrix.documents?.forEach(otherDoc => {
         if (otherDoc.depends_on?.includes(docEntry.path)) {
           affected.add(otherDoc.path);
         }
       });
       // Check 3: Add other docs owned by same domain (for index/summary updates)
       // This ensures domain owners can update their index docs when siblings change
       if (docEntry.owner) {
         const domainDocs = getDomainDocs(matrix.owner_domains?.[docEntry.owner]);
         domainDocs.forEach(d => affected.add(d));
       }
     }
     
     // Check 4: NEW doc not in matrix - infer domain from path and route to domain owner
     if (!docEntry && (file.startsWith('docs/') || file.endsWith('.md'))) {
       newDocs.push(file);
       // Try to match domain from path patterns
       for (const [owner, domainInfo] of Object.entries(matrix.owner_domains || {})) {
         const paths = getDomainDocs(domainInfo);
         const matchesPattern = paths.some(p => {
           const dir = p.substring(0, p.lastIndexOf('/'));
           return file.startsWith(dir) || file.includes(owner.replace('@',''));
         });
         if (matchesPattern) {
           paths.forEach(d => affected.add(d));
           break;
         }
       }
       // Fallback: always notify @docs domain for any new documentation
       getDomainDocs(matrix.owner_domains?.['@docs']).forEach(d => affected.add(d));
     }
   }
   
   const docs = [...affected].map(path => {
     const info = matrix.documents?.find(d => d.path === path) || {level:'L2',owner:'@core'};
     return {path, ...info};
   }).sort((a,b) => a.level.localeCompare(b.level));
   return { affected_docs: docs, trigger: changes, new_docs: newDocs, has_updates: docs.length > 0 };

6. IF node named "Has Updates"
   - Condition: has_updates equals true
   - On false: connect to NoOp to end

7. AI AGENT node named "Task Master" (use Gemini)
   - Model: gemini-1.5-pro
   - System: You generate JSON task lists for documentation updates. Consider these update types:
     - UPDATE_REFERENCE: Update cross-references when linked docs change
     - UPDATE_INDEX: Add/update entries in index or summary docs when new docs are added to a domain
     - CASCADE_UPDATE: Propagate changes to dependent documentation
     - REVIEW_NEEDED: Flag docs that may need human review due to significant changes
     - STATUS_UPDATE: Update task card status fields (Not Started → In Progress → Complete)
     - CHECKBOX_TOGGLE: Check/uncheck task checkboxes in task cards
     - COMPLETION_PERCENTAGE: Update completion counts in roadmaps/indexes
     
     TASK CARD AWARENESS:
     - When task-cards/*.md files change, also update parent indexes (task-cards/README.md, task-cards/INDEX.md)
     - When individual task cards are marked complete, cascade to docs/CONSOLIDATED_ROADMAP.md
     - For @task-tracking domain docs, always include STATUS_UPDATE or CHECKBOX_TOGGLE types
     
     Output exactly: {"update_list_id":"ul-DATE-TIME","tasks":[{"task_id":"task-001","document":"path","owner":"@domain","update_type":"TYPE","description":"what to update","depends_on":[],"priority":1}]}
   - User message: Create task list for commit: {{$json.trigger.message}}. 
     Affected docs: {{$json.affected_docs.map(d=>d.path + ' (owner: ' + d.owner + ')').join(', ')}}
     {{$json.new_docs?.length > 0 ? 'NEW docs added (not yet in matrix): ' + $json.new_docs.join(', ') : ''}}

8. CODE node named "Parse AI Response"
   - JavaScript:
   const text = $input.first().json.text || $input.first().json.output || JSON.stringify($input.first().json);
   const match = text.match(/\{[\s\S]*\}/);
   if (match) return JSON.parse(match[0]);
   return { update_list_id: 'ul-fallback', tasks: [] };

9. HTTP REQUEST node named "Send to Distributor"
   - Method: POST
   - URL: https://gitlitreview.app.n8n.cloud/webhook/task-distributor
   - Body Type: JSON
   - Body: ={{$json}}

Connect nodes in order: 1→2→3→4→5→6→7→8→9
```

---

# WORKFLOW 2: Doc Chain - Distributor
**Open the "Doc Chain - Distributor" canvas, then use this prompt:**

```
Build a workflow that manages a queue of documentation update tasks and coordinates their execution in dependency order.

CONTEXT: This is workflow 2 of 4. It receives task lists from "Trigger" workflow, maintains a queue, dispatches tasks to "Agent" workflow one at a time respecting dependencies, and waits for completion callbacks.

BUILD THESE NODES:

1. WEBHOOK node named "Receive List"
   - Path: /task-distributor
   - Method: POST
   - Respond: Immediately

2. CODE node named "Load State"
   - JavaScript:
   const staticData = $getWorkflowStaticData('global');
   if (!staticData.state) {
     staticData.state = { queue: [], current_list: null, completed: [] };
   }
   
   const state = staticData.state;
   const now = Date.now();
   const ONE_HOUR = 60 * 60 * 1000;
   
   // === QUEUE CLEANUP: Remove items older than 1 hour ===
   if (state.queue && state.queue.length > 0) {
     const originalLength = state.queue.length;
     state.queue = state.queue.filter(item => {
       const queuedAt = new Date(item.queued_at || 0).getTime();
       const age = now - queuedAt;
       if (age > ONE_HOUR) {
         console.log('Removing stale queue item:', item.update_list_id, 'age:', Math.round(age/60000), 'min');
         return false;
       }
       return true;
     });
     if (state.queue.length < originalLength) {
       console.log('Cleaned', originalLength - state.queue.length, 'stale items from queue');
     }
   }
   
   // === CURRENT LIST RECOVERY: Reset if stuck > 10 min ===
   if (state.current_list) {
     const startTime = new Date(state.current_list.started_at || state.current_list.queued_at).getTime();
     const elapsed = now - startTime;
     const STALE_THRESHOLD = 10 * 60 * 1000; // 10 minutes
     if (elapsed > STALE_THRESHOLD) {
       console.log('Clearing stuck current_list:', state.current_list.update_list_id);
       state.current_list = null;
     }
   }
   
   // === COMPLETED LIST CLEANUP: Keep only last 10 ===
   if (state.completed && state.completed.length > 10) {
     state.completed = state.completed.slice(-10);
   }
   
   staticData.state = state;
   return { state: staticData.state, new_list: $input.first().json };

3. CODE node named "Add To Queue"
   - JavaScript:
   const staticData = $getWorkflowStaticData('global');
   const { state, new_list } = $input.first().json;
   
   // Handle webhook body nesting - task data may be in .body or at root
   const listData = new_list.body || new_list;
   
   // === DEDUPLICATION: Track recently processed documents ===
   if (!staticData.recentDocs) staticData.recentDocs = {};
   
   // Clean up entries older than 1 hour
   const oneHourAgo = Date.now() - (60 * 60 * 1000);
   for (const key of Object.keys(staticData.recentDocs)) {
     if (staticData.recentDocs[key] < oneHourAgo) {
       delete staticData.recentDocs[key];
     }
   }
   
   // Filter out tasks for documents processed recently
   if (listData.tasks && Array.isArray(listData.tasks)) {
     const originalCount = listData.tasks.length;
     listData.tasks = listData.tasks.filter(task => {
       const docKey = task.document || task.path || task.task_id;
       if (staticData.recentDocs[docKey]) {
         console.log('Skipping duplicate task for:', docKey);
         return false;
       }
       return true;
     });
     
     // If all tasks filtered out, don't queue this list
     if (listData.tasks.length === 0) {
       console.log('All tasks filtered as duplicates, skipping list');
       return { should_process: false, skipped: true };
     }
     
     // Mark these docs as being processed
     listData.tasks.forEach(task => {
       const docKey = task.document || task.path || task.task_id;
       staticData.recentDocs[docKey] = Date.now();
     });
   }
   // === END DEDUPLICATION ===
   
   listData.status = 'queued';
   listData.queued_at = new Date().toISOString();
   if (listData.tasks) listData.tasks.forEach(t => t.status = 'pending');
   state.queue.push(listData);
   staticData.state = state;
   return { should_process: !state.current_list };

4. IF node named "Should Process"
   - Condition: should_process equals true
   - On false: End (item is queued, will process later)

5. CODE node named "Pop Next List"
   - JavaScript:
   const staticData = $getWorkflowStaticData('global');
   const state = staticData.state;
   if (state.queue.length === 0) return { has_work: false };
   state.current_list = state.queue.shift();
   state.current_list.status = 'in_progress';
   state.current_list.started_at = new Date().toISOString(); // Track when processing started
   staticData.state = state;
   return { has_work: true, current_list: state.current_list };

6. CODE node named "Get Runnable Tasks"
   - JavaScript:
   const staticData = $getWorkflowStaticData('global');
   const state = staticData.state;
   const list = $input.first().json.current_list;
   
   // Handle webhook body nesting - tasks may be in .body.tasks or .tasks
   const tasks = list?.body?.tasks || list?.tasks || [];
   const listId = list?.body?.update_list_id || list?.update_list_id || null;
   const trigger = list?.body?.trigger || list?.trigger || {};
   
   // If no tasks found, this is an error state - reset and allow retry
   if (!tasks.length || !listId) {
     console.error('No tasks found in list - resetting state');
     if (state.current_list) {
       state.current_list = null;
       staticData.state = state;
     }
     return { runnable: [], list_id: null, error: 'No tasks found' };
   }
   
   // Ensure all tasks have a status (default to 'pending' if missing)
   tasks.forEach(t => { if (!t.status) t.status = 'pending'; });
   
   const done = tasks.filter(t => t.status === 'completed').map(t => t.task_id);
   const runnable = tasks.filter(t => 
     t.status === 'pending' && (!t.depends_on || t.depends_on.length === 0 || t.depends_on.every(d => done.includes(d)))
   );
   // Return each runnable task as a separate item with list_id and trigger attached
   // n8n will automatically iterate over these items in subsequent nodes
   return runnable.map(task => ({ task, list_id: listId, trigger }));

7. IF node named "Has Runnable"
   - Condition: Use boolean expression
   - Expression: `{{ $json.task !== undefined }}`
   - Operator: equals
   - Compare to: `true`
   - On false: End or loop back
   - NOTE: Get Runnable Tasks returns multiple items; this checks if any exist

7.5. CODE node named "Prepare Agent Payload"
   - Mode: Run Once for Each Item
   - JavaScript:
   // Flatten and prepare the payload for the HTTP request
   // This avoids n8n expression evaluation issues with nested objects
   const item = $input.first().json;
   return {
     task: item.task,
     list_id: item.list_id,
     trigger: item.trigger || {},
     // Pass task_id at top level for Wait node
     _task_id: item.task.task_id
   };
   - NOTE: Creates a clean object for the HTTP node to serialize

8. HTTP REQUEST node named "Dispatch to Agent"
   - Method: POST
   - URL: https://gitlitreview.app.n8n.cloud/webhook/domain-agent
   - Body Content Type: JSON
   - Specify Body: Using JSON
   - JSON Body (raw text, NOT expression):
     {
       "task": {{ JSON.stringify($json.task) }},
       "list_id": "{{ $json.list_id }}",
       "trigger": "{{ $json.list_id }}"
     }
   - IMPORTANT: Use JSON.stringify() for nested objects (task, trigger)
   - String values like list_id just need quotes and expression
   - Do NOT use "Using Fields" mode - it converts objects to "[object Object]"

9. WAIT node named "Wait for Callback"
    - Resume: On Webhook Call
    - Webhook Suffix: task-done-{{$('Prepare Agent Payload').item.json._task_id}}
    - Timeout: 5 minutes
    - **On Timeout:** Continue (not fail) - allows Update Task Status to handle it
    - IMPORTANT: Must reference Prepare Agent Payload directly since $json contains HTTP response

10. CODE node named "Update Task Status"
    - JavaScript:
    const staticData = $getWorkflowStaticData('global');
    const state = staticData.state;
    const result = $input.first().json;
    
    // Get the task_id from the callback OR from Prepare Agent Payload (for timeout case)
    let taskId = result.task_id;
    let status = result.status || 'completed';
    
    // Handle TIMEOUT: If no task_id in result, the Wait node timed out
    // Get task_id from Prepare Agent Payload and mark as FAILED (not pending!)
    if (!taskId) {
      try {
        taskId = $('Prepare Agent Payload').first().json._task_id;
        status = 'failed';  // Mark as failed so it doesn't retry infinitely
        console.log('Wait timed out for task:', taskId);
      } catch (e) {
        console.error('Cannot determine task_id on timeout');
      }
    }
    
    if (state.current_list && state.current_list.tasks && taskId) {
      const task = state.current_list.tasks.find(t => t.task_id === taskId);
      if (task) { 
        task.status = status;
        task.completed_at = new Date().toISOString();
      }
    }
    staticData.state = state;
    // Count tasks not yet done (pending only - failed tasks don't retry)
    const pending = state.current_list?.tasks?.filter(t => t.status === 'pending') || [];
    return { all_done: pending.length === 0, state };

11. IF node named "All Done"
    - Condition: all_done equals true
    - On true: Go to Finalize
    - On false: Loop back to "Get Runnable Tasks"

12. CODE node named "Finalize List"
    - JavaScript:
    const staticData = $getWorkflowStaticData('global');
    const state = staticData.state;
    if (state.current_list) {
      state.current_list.status = 'completed';
      state.completed.push(state.current_list);
    }
    state.current_list = null;
    staticData.state = state;
    return { more_queued: state.queue.length > 0 };

13. IF node named "More Queued"
    - Condition: more_queued equals true
    - On true: Loop back to "Pop Next List"
    - On false: End

Connect: 1→2→3→4→5→6→7→8→9→10→11→12→13
Create loops as specified in conditions.
```

---

# WORKFLOW 3: Doc Chain - Agent
**Open the "Doc Chain - Agent" canvas, then use this prompt:**

```
Build a workflow that uses AI to update documentation files and commits changes to GitHub.

CONTEXT: This is workflow 3 of 4. It receives individual tasks from "Distributor", fetches the target document, uses AI to make updates, commits to GitHub, updates the review tracking in documentation_matrix.json, and sends a completion callback.

BUILD THESE NODES:

1. WEBHOOK node named "Receive Task"
   - Path: /domain-agent
   - Method: POST
   - Respond: Immediately

2. CODE node named "Parse Webhook Data"
   - JavaScript:
   // The Distributor sends task/trigger as JSON strings - parse them back to objects
   const body = $input.first().json.body;
   const task = typeof body.task === 'string' ? JSON.parse(body.task) : body.task;
   const trigger = typeof body.trigger === 'string' ? JSON.parse(body.trigger) : (body.trigger || {});
   const listId = typeof body.list_id === 'string' ? body.list_id.replace(/"/g, '') : body.list_id;
   return { task, trigger, list_id: listId };
   - NOTE: Distributor uses JSON.stringify() to avoid [object Object] - we parse it back here

3. HTTP REQUEST node named "Fetch Document"
   - Method: GET
   - URL (use expression mode): {{ "https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/" + $json.task.document }}
   - Response Format: Text
   - NOTE: Click the "fx" icon to enable expression mode. Do NOT include "={{" prefix - just use {{ }}
   - IMPORTANT: Hardcode the repo URL - $env.* is blocked on n8n Cloud

4. AI AGENT node named "Update Document" (use Gemini)
   - Model: gemini-2.5-flash
   - System prompt: You update documentation and task tracking files. Make minimal targeted changes. Preserve formatting.
     
     DOCUMENT TYPES YOU HANDLE:
     1. **Regular Documentation** - Update prose, references, dates
     2. **Task Cards** - Update status fields, checkboxes, completion dates
     3. **Roadmaps/Indexes** - Update completion percentages, status tables
     
     TASK CARD UPDATES:
     - Status field: Change "Status: Not Started" to "Status: Complete" (or In Progress/Blocked)
     - Checkboxes: Change "- [ ] Task item" to "- [x] Task item" when completed
     - Completion dates: Add "Completion Date: YYYY-MM-DD" when status changes to Complete
     - Completion percentage: Calculate from checkbox counts (e.g., "3/5 Complete (60%)")
     
     ROADMAP/INDEX UPDATES:
     - Update status emoji: 🟢 Ready → 🔄 Active → ✅ COMPLETE
     - Update "Status: X/Y Complete" counts in summary tables
     - Update wave completion percentages
     
     Output JSON: {"changes_needed":true/false,"updated_content":"full updated doc","summary":"brief description","update_type":"PROSE|STATUS|CHECKBOX|PERCENTAGE"}
   - User message: Task: {{$('Parse Webhook Data').first().json.task.description}}. Document: {{$('Parse Webhook Data').first().json.task.document}}. Trigger: {{$('Parse Webhook Data').first().json.trigger.message}}. Current content: {{$json.data}}
   - NOTE: Reference parsed webhook data via $('Parse Webhook Data').first().json

5. CODE node named "Parse AI Output"
   - JavaScript:
   const taskData = $('Parse Webhook Data').first().json;
   const text = $input.first().json.text || $input.first().json.output || '';
   // Use greedy match to capture the FULL JSON object including updated_content
   const match = text.match(/\{[\s\S]*\}/);
   let result = { changes_needed: false, summary: 'No changes', updated_content: '' };
   if (match) {
     try { result = JSON.parse(match[0]); } catch(e) {
       console.error('Failed to parse AI output:', e.message);
     }
   }
   return { ...result, task_id: taskData.task.task_id, document: taskData.task.document };
   // NOTE: Access parsed data via $('Parse Webhook Data').first().json
   // IMPORTANT: Uses greedy regex (.*) not non-greedy (.*?) to capture full JSON with updated_content

6. IF node named "Changes Needed"
   - Condition: changes_needed equals true
   - On false: Skip to Update Review Tracking (node 10)

7. HTTP REQUEST node named "Get File SHA"
   - Method: GET
   - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/{{$json.document}}
   - Authentication: None (we use manual headers instead - more reliable on n8n Cloud)
   - Headers (add under "Send Headers" → "Specify Headers" → "Using Fields"):
     - Name: `Authorization` | Value: `Bearer YOUR_GITHUB_PAT_HERE`
     - Name: `Accept` | Value: `application/vnd.github.v3+json`
   - NOTE: Replace YOUR_GITHUB_PAT_HERE with your actual GitHub token

8. CODE node named "Prepare Commit"
   - JavaScript:
   const prev = $('Parse AI Output').first().json;
   const sha = $input.first().json.sha;
   const content = Buffer.from(prev.updated_content || '').toString('base64');
   // Sanitize summary for commit message (remove special chars that break JSON)
   const safeSummary = (prev.summary || 'Update documentation')
     .replace(/[`"\\]/g, '')  // Remove backticks, quotes, backslashes
     .substring(0, 68);        // Limit length for commit message (shorter to accommodate prefix)
   return { 
     ...prev, 
     sha, 
     content_base64: content,
     // Individual fields for commit (for Using Fields mode)
     // IMPORTANT: [n8n] prefix is used to filter out these commits from triggering the chain again
     commit_message: `[n8n] docs: ${safeSummary}`,
     commit_content: content,
     commit_sha: sha
   };

9. HTTP REQUEST node named "Commit to GitHub"
   - Method: PUT
   - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/{{$json.document}}
   - Authentication: None (use manual headers)
   - Headers (add under "Send Headers" → "Specify Headers" → "Using Fields"):
     - Name: `Authorization` | Value: `Bearer YOUR_GITHUB_PAT_HERE`
     - Name: `Accept` | Value: `application/vnd.github.v3+json`
   - Body Content Type: JSON
   - Specify Body: Using Fields Below
   - Body Parameters (add 3 fields):
     - Name: `message` | Value: `{{ $json.commit_message }}`
     - Name: `content` | Value: `{{ $json.commit_content }}`
     - Name: `sha` | Value: `{{ $json.commit_sha }}`

--- REVIEW TRACKING NODES (connect both paths here) ---

10. HTTP REQUEST node named "Fetch Matrix"
    - Method: GET
    - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/docs/documentation_matrix.json
    - Authentication: None (use manual headers)
    - Headers (add under "Send Headers" → "Specify Headers" → "Using Fields"):
      - Name: `Authorization` | Value: `Bearer YOUR_GITHUB_PAT_HERE`
      - Name: `Accept` | Value: `application/vnd.github.v3+json`
    - NOTE: This returns the file content base64-encoded with SHA

11. CODE node named "Update Review Tracking"
    - JavaScript:
    const prev = $('Parse AI Output').first().json;
    const matrixResponse = $input.first().json;
    
    // Decode the matrix content from base64
    const matrixContent = Buffer.from(matrixResponse.content, 'base64').toString('utf8');
    const matrix = JSON.parse(matrixContent);
    
    // Find the document and update review tracking
    const today = new Date().toISOString().split('T')[0];
    const doc = matrix.documents.find(d => d.path === prev.document);
    
    if (doc) {
      doc.last_reviewed = today;
      // Calculate next_review based on review_interval_days
      const interval = doc.review_interval_days || 7;
      const nextDate = new Date();
      nextDate.setDate(nextDate.getDate() + interval);
      doc.next_review = nextDate.toISOString().split('T')[0];
      // If changes were made, also update last_updated
      if (prev.changes_needed) {
        doc.last_updated = today;
        doc.status = 'current';
      }
    }
    
    // Update matrix version timestamp
    matrix.last_updated = today;
    
    // Encode back to base64 for commit
    const updatedContent = Buffer.from(JSON.stringify(matrix, null, 2)).toString('base64');
    
    // Sanitize summary for callback (remove chars that might break JSON)
    const safeSummary = (prev.summary || 'No changes')
      .replace(/[`"\\]/g, '')
      .substring(0, 100);
    
    return {
      ...prev,
      matrix_sha: matrixResponse.sha,
      matrix_content_base64: updatedContent,
      review_updated: !!doc,
      // Individual fields for matrix commit (for Using Fields mode)
      matrix_commit_message: `[n8n] chore: update review tracking for ${prev.document}`,
      // Individual fields for callback (for Using Fields mode)  
      callback_status: 'completed',
      callback_summary: safeSummary
    };

12. HTTP REQUEST node named "Commit Matrix Update"
    - Method: PUT
    - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/docs/documentation_matrix.json
    - Authentication: None (use manual headers)
    - Headers (add under "Send Headers" → "Specify Headers" → "Using Fields"):
      - Name: `Authorization` | Value: `Bearer YOUR_GITHUB_PAT_HERE`
      - Name: `Accept` | Value: `application/vnd.github.v3+json`
    - Body Content Type: JSON
    - Specify Body: Using Fields Below
    - Body Parameters (add 3 fields):
      - Name: `message` | Value: `{{ $json.matrix_commit_message }}`
      - Name: `content` | Value: `{{ $json.matrix_content_base64 }}`
      - Name: `sha` | Value: `{{ $json.matrix_sha }}`
    - IMPORTANT: Under "Options" → "On Error" → select "Continue On Fail"
    - This prevents failures if another process updated the matrix (race condition)

13. HTTP REQUEST node named "Send Callback"
    - Method: POST
    - URL: https://gitlitreview.app.n8n.cloud/webhook/task-done-{{ $('Update Review Tracking').first().json.task_id }}
    - Body Content Type: JSON
    - Specify Body: Using Fields Below
    - Body Parameters (add 3 fields):
      - Name: `task_id` | Value: `{{ $('Update Review Tracking').first().json.task_id }}`
      - Name: `status` | Value: `{{ $('Update Review Tracking').first().json.callback_status }}`
      - Name: `result` | Value: `{{ JSON.stringify({ summary: $('Update Review Tracking').first().json.callback_summary }) }}`
    - NOTE: References Update Review Tracking directly (not $json) because previous node may be error object
    - **Settings Tab** → On Error: **Continue (using error output)** 
      - This allows the Agent to complete even if Distributor's Wait node has timed out

Connect: 1→2→3→4→5→6→(true: 7→8→9→10, false: 10)→11→12→13
Both "Changes Needed" paths merge at "Fetch Matrix" (node 10).
The review tracking is updated regardless of whether document changes were needed.
```

---

# WORKFLOW 4: Doc Chain - Errors
**Open the "Doc Chain - Errors" canvas, then use this prompt:**

```
Build an error handling workflow that catches failures from the other documentation chain workflows.

CONTEXT: This is workflow 4 of 4. It triggers on errors from workflows 1-3, logs the error, and optionally sends notifications.

BUILD THESE NODES:

1. ERROR TRIGGER node named "Catch Errors"
   - This triggers when any workflow in the instance has an error

2. CODE node named "Log Error"
   - JavaScript:
   const error = $input.first().json;
   console.error('Doc Chain Error:', JSON.stringify(error, null, 2));
   
   // Try multiple paths to find task_id - it may be in different locations
   let task_id = null;
   
   // Path 1: From execution data (if workflow passed it through)
   if (error.execution?.data?.task_id) {
     task_id = error.execution.data.task_id;
   }
   // Path 2: From the HTTP request body that failed (e.g., Send Callback)
   else if (error.execution?.error?.context?.request?.body?.task_id) {
     // Remove leading "=" if present (n8n expression artifact)
     task_id = String(error.execution.error.context.request.body.task_id).replace(/^=/, '');
   }
   // Path 3: Parse from the failed URL (e.g., /webhook/task-done-task-001)
   else if (error.execution?.error?.context?.request?.uri) {
     const match = error.execution.error.context.request.uri.match(/task-done-([^/]+)$/);
     if (match) task_id = match[1];
   }
   
   return {
     workflow: error.workflow?.name || 'Unknown',
     node: error.execution?.lastNodeExecuted || 'Unknown',
     message: error.execution?.error?.message || 'Unknown error',
     timestamp: new Date().toISOString(),
     task_id: task_id
   };

3. IF node named "Has Task ID"
   - Condition: Check if task_id is not null
   - On true: Send failure callback
   - On false: End

4. HTTP REQUEST node named "Send Failure Callback"
   - Method: POST
   - URL: https://gitlitreview.app.n8n.cloud/webhook/task-done-{{$json.task_id}}
   - Body: {"task_id":"{{$json.task_id}}","status":"failed","result":{"error":"{{$json.message}}"}}
   - IMPORTANT: Under "Options" → "On Error" → select "Continue On Fail"
   - This prevents cascading errors when the Wait node has already timed out

5. CODE node named "Log Callback Result" (optional but recommended)
   - JavaScript:
   const result = $input.first().json;
   // Check if callback succeeded or failed (404 = Wait node expired, which is OK)
   const success = !result.error && !result.errorMessage;
   const status = success ? 'notified' : 'expired';
   console.log(`Failure callback ${status} for task: ${$('Log Error').first().json.task_id}`);
   return { callback_status: status, task_id: $('Log Error').first().json.task_id };

6. (Optional) Add a Slack/Email node after Log Error to notify your team

Connect: 1→2→3→(true: 4→5, false: end)
```

---

## Post-Build Verification

After building all 4 workflows:

1. [ ] Activate workflows 2, 3, and 4 (Distributor, Agent, Errors)
2. [ ] Test Trigger workflow manually with this webhook payload:

```json
{
  "ref": "refs/heads/main",
  "after": "abc123",
  "pusher": {"name": "test-user"},
  "head_commit": {"message": "test: update dashboard API"},
  "commits": [{"added": [], "modified": ["webdashboard/app.py"]}]
}
```

3. [ ] Verify the flow: Trigger → Distributor → Agent → Callback → Complete
4. [ ] Check n8n execution logs for any errors
5. [ ] Configure GitHub webhook (see section below)

---

## 🔧 Reset Distributor State (Recovery)

If the Distributor gets stuck (e.g., tasks never dispatched, stale queue items looping), you can reset its state:

**Option 1: Auto-cleanup (built-in)**
The Load State node automatically:
- Removes queue items older than 1 hour
- Clears stuck current_list after 10 minutes
- Keeps only last 10 completed items

**Option 2: Add a Reset Webhook (recommended)**
Add a second webhook to the Distributor workflow for manual resets:

1. Add a WEBHOOK node named "Reset State"
   - Path: `/distributor-reset`
   - Method: POST
   
2. Add a CODE node named "Clear State" connected to it:
```javascript
const staticData = $getWorkflowStaticData('global');
const oldState = staticData.state || {};
const queueLength = oldState.queue?.length || 0;
const currentList = oldState.current_list?.update_list_id || null;

// Reset everything
staticData.state = { queue: [], current_list: null, completed: [] };
staticData.recentDocs = {};  // Also clear deduplication cache

return { 
  reset: true, 
  cleared_queue_items: queueLength,
  cleared_current_list: currentList,
  message: 'State fully cleared' 
};
```

3. Call it: `POST https://gitlitreview.app.n8n.cloud/webhook/distributor-reset`

**Option 3: Temporary inline reset**
Add this to the START of the "Load State" node temporarily:

```javascript
// EMERGENCY RESET - remove after running once!
const staticData = $getWorkflowStaticData('global');
staticData.state = { queue: [], current_list: null, completed: [] };
staticData.recentDocs = {};
return { state: staticData.state, new_list: $input.first().json, RESET: true };
```

**Option 4: Check current state**
Add a Code node to inspect the current state:

```javascript
const staticData = $getWorkflowStaticData('global');
return { 
  state: staticData.state,
  queue_length: staticData.state?.queue?.length || 0,
  current_list_id: staticData.state?.current_list?.update_list_id || null,
  current_list_status: staticData.state?.current_list?.status || null
};
```

---

## 🔗 GitHub Webhook Configuration

### Step 1: Get Your n8n Webhook URL

From n8n, the production webhook URL is:
```
https://gitlitreview.app.n8n.cloud/webhook/github-doc-trigger
```

### Step 2: Configure GitHub Webhook

1. Go to your GitHub repository: **Settings → Webhooks → Add webhook**
2. Configure as follows:

| Setting | Value |
|---------|-------|
| **Payload URL** | `https://gitlitreview.app.n8n.cloud/webhook/github-doc-trigger` |
| **Content type** | `application/json` |
| **Secret** | *(leave blank - no auth needed for incoming webhooks)* |
| **SSL verification** | Enable |
| **Which events?** | Select: **Pushes** and **Pull requests** |
| **Active** | ✅ Checked |

### Step 3: Select Events

Under "Which events would you like to trigger this webhook?":
- Select **"Let me select individual events"**
- Check: ✅ **Pushes** (for direct commits to main)
- Check: ✅ **Pull requests** (for merged PRs)
- Uncheck everything else

### Important Notes

| Topic | Details |
|-------|---------|
| **No Authentication Needed** | For incoming webhooks, n8n's Webhook node is public. GitHub doesn't need a token to POST to it. |
| **GitHub Tokens Are Different** | The `GITHUB_TOKEN` in n8n is for *outgoing* API calls (committing files), not for receiving webhooks. |
| **Ping Event** | When you first add the webhook, GitHub sends a "ping" event. This is expected and will trigger the workflow (but may fail the filter - that's OK). |

---

## 🔍 Troubleshooting GitHub Webhooks

### Check GitHub Delivery Logs

1. Go to: **Repository → Settings → Webhooks → Click your webhook**
2. Scroll to **"Recent Deliveries"**
3. Click on a delivery to see:
   - **Request** - what GitHub sent
   - **Response** - what n8n returned
   - **Status code** - 200 = success

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| **404 Response** | Workflow not active or wrong URL | Activate workflow, verify URL matches exactly |
| **Ping works, Push doesn't** | Filter node rejecting the event | Check Filter node conditions (see below) |
| **No delivery shown** | Wrong events selected | Enable "Pushes" event in GitHub webhook settings |
| **curl works, GitHub doesn't** | Payload structure difference | Use `$json.body.` prefix (see below) |
| **Filter always false** | Wrong JSON path | GitHub data is nested in `body` object |
| **"Wrong type" error in Filter** | "exists" operator on array type | Use boolean expression instead (see below) |

### ⚠️ Critical: IF Node Array Checking

The "exists" operator in n8n IF nodes doesn't handle arrays properly. Instead of using "exists", use a **boolean expression** that checks array length:

**❌ DON'T use "exists" operator:**
```
$json.body.commits exists
```

**✅ DO use boolean expression equals true:**
```
{{ ($json.body.commits?.length > 0) || ($json.body.pull_request?.merged === true) }}
```
Set operator to "equals" and compare to `true`.

This approach:
- Uses optional chaining (`?.`) to safely handle missing properties
- Checks array length instead of existence
- Returns a proper boolean for the IF node to evaluate

### ⚠️ Critical: GitHub Webhook Body Nesting

**n8n wraps the GitHub payload inside a `body` object.** This is the #1 cause of filter failures.

When GitHub sends:
```json
{"commits": [...], "ref": "refs/heads/main"}
```

n8n receives:
```json
{
  "headers": {...},
  "body": {
    "commits": [...],
    "ref": "refs/heads/main"
  }
}
```

**Therefore, always use `$json.body.` prefix:**
- ❌ `$json.commits` - WRONG
- ✅ `$json.body.commits` - CORRECT

### Debugging the Filter Node

The "Filter Valid Events" node must check for `body.commits` array.

**Correct Filter Conditions:**
```
{{ $json.body.commits }} exists
OR
{{ $json.body.pull_request }} exists
OR  
{{ $json.body.pull_request.merged }} is equal to true
```

**GitHub Push Event Structure (as received by n8n):**
```json
{
  "headers": {"x-github-event": "push", ...},
  "body": {
    "ref": "refs/heads/main",
    "before": "abc123...",
    "after": "def456...",
    "commits": [
      {
        "id": "def456...",
        "message": "commit message",
        "added": ["new_file.md"],
        "modified": ["existing_file.py"]
      }
    ],
    "head_commit": {...}
  }
}
```

---

## Quick Reference

| Workflow | Webhook Path | Purpose |
|----------|--------------|---------|
| Trigger | `/github-doc-trigger` | Entry point from GitHub |
| Distributor | `/task-distributor` | Queue & orchestration |
| Agent | `/domain-agent` | AI doc updates |
| Distributor | `/task-done-{id}` | Completion callbacks |
| Staleness Review | `/staleness-review` | Manual trigger for proactive review |

> **Workflow 5 (Staleness Review)** is documented separately in [N8N_STALENESS_REVIEW_BUILDER_PROMPT.md](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md)

---

# 🔧 UPDATE PROMPT: Add Credentials to Existing Workflows

> **Use this prompt if you've already built the 4 workflows and need to add/fix credential configuration.**

**Open each workflow canvas and paste the relevant section below:**

---

## Update: Doc Chain - Agent (Add GitHub Credentials)

```
I need to update the HTTP Request nodes that call GitHub API to use proper authentication.

FIND AND UPDATE THESE NODES:

1. NODE: "Get File SHA" (HTTP Request)
   - Keep: Method GET, URL as-is
   - ADD Authentication:
     - Auth Type: Predefined Credential Type
     - Credential Type: Header Auth
     - Credential: Select "GitHub API Token"
   - ADD Header:
     - Name: Accept
     - Value: application/vnd.github.v3+json

2. NODE: "Commit to GitHub" (HTTP Request)  
   - Keep: Method PUT, URL as-is, Body as-is
   - ADD Authentication:
     - Auth Type: Predefined Credential Type
     - Credential Type: Header Auth
     - Credential: Select "GitHub API Token"
   - ADD Header:
     - Name: Accept
     - Value: application/vnd.github.v3+json

Make sure both nodes use the "GitHub API Token" Header Auth credential.
```

---

## Update: Doc Chain - Trigger (Add Gemini Credentials)

```
I need to update the AI Agent node to use proper Gemini credentials.

FIND AND UPDATE THIS NODE:

1. NODE: "Task Master" (AI Agent)
   - Keep: System prompt and User message as-is
   - UPDATE Credential:
     - Select "Gemini API" credential
   - VERIFY Settings:
     - Model: gemini-1.5-pro (or gemini-1.5-flash)
     - Temperature: 0.3
```

---

## Update: Doc Chain - Agent (Add Gemini Credentials)

```
I need to update the AI Agent node to use proper Gemini credentials.

FIND AND UPDATE THIS NODE:

1. NODE: "Update Document" (AI Agent)
   - Keep: System prompt and User message as-is
   - UPDATE Credential:
     - Select "Gemini API" credential
   - VERIFY Settings:
     - Model: gemini-1.5-flash
     - Temperature: 0.3
```

---

## Verification After Updates

After applying credential updates:

1. [ ] Test "Get File SHA" node manually - should return file info without 401 error
2. [ ] Test "Task Master" AI node - should generate JSON task list
3. [ ] Test "Update Document" AI node - should return update JSON
4. [ ] Run full workflow test with sample payload

---

*Prompt Version: 2.1 - Added credential setup and update prompts*
