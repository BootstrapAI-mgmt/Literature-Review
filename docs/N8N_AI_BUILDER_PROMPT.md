# N8N AI Builder Prompts: Documentation Update Chain

> **Instructions:** This system requires **4 separate workflows** built one at a time. Each prompt below is designed for a single n8n canvas. Create each workflow manually in n8n, then use the corresponding prompt to build it.

---

## 🏗️ Architecture Overview (Reference for All Prompts)

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  GitHub     │────▶│  Doc Chain -    │────▶│  Doc Chain - │
│  Webhook    │     │  Trigger        │     │  Distributor │
└─────────────┘     └─────────────────┘     └──────┬───────┘
                                                   │
                           ┌───────────────────────┘
                           ▼
                    ┌──────────────┐     callback     ┌──────────────┐
                    │  Doc Chain - │─────────────────▶│  Distributor │
                    │  Agent       │                  │  (continues) │
                    └──────────────┘                  └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Doc Chain - │ (catches errors from all)
                    │  Errors      │
                    └──────────────┘
```

**Workflow Communication:**
- Trigger → Distributor: HTTP POST to `/webhook/task-distributor`
- Distributor → Agent: HTTP POST to `/webhook/domain-agent`
- Agent → Distributor: HTTP POST to `/webhook/task-done-{task_id}`

**Environment Variables (configure in n8n Settings → Variables):**
- `GITHUB_REPO`: `BootstrapAI-mgmt/Literature-Review`
- `GITHUB_TOKEN`: Your GitHub PAT with repo scope
- `N8N_WEBHOOK_URL`: Your n8n instance base URL (e.g., `https://n8n.example.com`)

---

## Pre-Setup Checklist

Before using these prompts:
1. [ ] Create 4 empty workflows in n8n named exactly:
   - `Doc Chain - Trigger`
   - `Doc Chain - Distributor`
   - `Doc Chain - Agent`
   - `Doc Chain - Errors`
2. [ ] Configure environment variables in n8n Settings
3. [ ] Set up Gemini API credentials in n8n

---

# WORKFLOW 1: Doc Chain - Trigger
**Open the "Doc Chain - Trigger" canvas, then use this prompt:**

```
Build a workflow that receives GitHub webhooks and identifies which documentation files need updating.

CONTEXT: This is workflow 1 of 4 in a documentation auto-update system. This workflow receives GitHub push/merge events, looks up a dependency matrix to find affected docs, uses AI to create a task list, then sends it to a separate "Distributor" workflow via HTTP.

BUILD THESE NODES:

1. WEBHOOK node named "GitHub Webhook"
   - Path: /github-doc-trigger
   - Method: POST
   - Respond: Immediately

2. IF node named "Filter Valid Events"
   - Condition: Check if webhook contains commits array OR (pull_request exists AND pull_request.merged is true)
   - On false: connect to a NoOp node to end

3. CODE node named "Parse Changes"
   - JavaScript:
   const event = $input.first().json;
   const files = [];
   if (event.commits) {
     event.commits.forEach(c => {
       files.push(...(c.added || []), ...(c.modified || []));
     });
   }
   return {
     commit_sha: event.after || event.pull_request?.merge_commit_sha,
     author: event.pusher?.name || event.pull_request?.user?.login,
     message: event.head_commit?.message || event.pull_request?.title,
     changed_files: [...new Set(files)]
   };

4. HTTP REQUEST node named "Fetch Matrix"
   - Method: GET
   - URL: https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json

5. CODE node named "Find Affected Docs"
   - JavaScript:
   const matrix = $('Fetch Matrix').first().json;
   const changes = $('Parse Changes').first().json;
   const affected = new Set();
   for (const file of changes.changed_files) {
     for (const [script, docs] of Object.entries(matrix.script_to_docs || {})) {
       if (file.includes(script.replace('.py',''))) {
         docs.forEach(d => affected.add(d));
       }
     }
   }
   const docs = [...affected].map(path => {
     const info = matrix.documents?.find(d => d.path === path) || {level:'L2',owner:'@core'};
     return {path, ...info};
   }).sort((a,b) => a.level.localeCompare(b.level));
   return { affected_docs: docs, trigger: changes, has_updates: docs.length > 0 };

6. IF node named "Has Updates"
   - Condition: has_updates equals true
   - On false: connect to NoOp to end

7. AI AGENT node named "Task Master" (use Gemini)
   - Model: gemini-1.5-pro
   - System: You generate JSON task lists. Output exactly: {"update_list_id":"ul-DATE-TIME","tasks":[{"task_id":"task-001","document":"path","owner":"@domain","update_type":"UPDATE_REFERENCE","description":"what to update","depends_on":[],"priority":1}]}
   - User message: Create task list for commit: {{$json.trigger.message}}. Affected docs: {{$json.affected_docs.map(d=>d.path).join(', ')}}

8. CODE node named "Parse AI Response"
   - JavaScript:
   const text = $input.first().json.text || $input.first().json.output || JSON.stringify($input.first().json);
   const match = text.match(/\{[\s\S]*\}/);
   if (match) return JSON.parse(match[0]);
   return { update_list_id: 'ul-fallback', tasks: [] };

9. HTTP REQUEST node named "Send to Distributor"
   - Method: POST
   - URL: {{$env.N8N_WEBHOOK_URL}}/webhook/task-distributor
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
   return { state: staticData.state, new_list: $input.first().json };

3. CODE node named "Add To Queue"
   - JavaScript:
   const { state, new_list } = $input.first().json;
   new_list.status = 'queued';
   new_list.queued_at = new Date().toISOString();
   if (new_list.tasks) new_list.tasks.forEach(t => t.status = 'pending');
   state.queue.push(new_list);
   const staticData = $getWorkflowStaticData('global');
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
   staticData.state = state;
   return { has_work: true, current_list: state.current_list };

6. CODE node named "Get Runnable Tasks"
   - JavaScript:
   const list = $input.first().json.current_list;
   if (!list || !list.tasks) return { runnable: [], list_id: null };
   const done = list.tasks.filter(t => t.status === 'completed').map(t => t.task_id);
   const runnable = list.tasks.filter(t => 
     t.status === 'pending' && (!t.depends_on || t.depends_on.every(d => done.includes(d)))
   );
   return { runnable: runnable, list_id: list.update_list_id, trigger: list.trigger || {} };

7. IF node named "Has Runnable"
   - Condition: Check if runnable array length > 0
   - On false: End or loop back

8. Split In Batches node named "Process Each Task"
   - Batch Size: 1

9. HTTP REQUEST node named "Dispatch to Agent"
   - Method: POST
   - URL: {{$env.N8N_WEBHOOK_URL}}/webhook/domain-agent
   - Body: {"task": {{$json}}, "list_id": "{{$('Get Runnable Tasks').first().json.list_id}}", "trigger": {{$('Get Runnable Tasks').first().json.trigger}} }

10. WAIT node named "Wait for Callback"
    - Resume: On Webhook Call
    - Webhook Suffix: task-done-{{$json.task_id}}
    - Timeout: 5 minutes

11. CODE node named "Update Task Status"
    - JavaScript:
    const staticData = $getWorkflowStaticData('global');
    const state = staticData.state;
    const result = $input.first().json;
    if (state.current_list && state.current_list.tasks) {
      const task = state.current_list.tasks.find(t => t.task_id === result.task_id);
      if (task) { task.status = result.status || 'completed'; }
    }
    staticData.state = state;
    const pending = state.current_list?.tasks?.filter(t => t.status === 'pending') || [];
    return { all_done: pending.length === 0, state };

12. IF node named "All Done"
    - Condition: all_done equals true
    - On true: Go to Finalize
    - On false: Loop back to "Get Runnable Tasks"

13. CODE node named "Finalize List"
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

14. IF node named "More Queued"
    - Condition: more_queued equals true
    - On true: Loop back to "Pop Next List"
    - On false: End

Connect: 1→2→3→4→5→6→7→8→9→10→11→12→13→14
Create loops as specified in conditions.
```

---

# WORKFLOW 3: Doc Chain - Agent
**Open the "Doc Chain - Agent" canvas, then use this prompt:**

```
Build a workflow that uses AI to update documentation files and commits changes to GitHub.

CONTEXT: This is workflow 3 of 4. It receives individual tasks from "Distributor", fetches the target document, uses AI to make updates, commits to GitHub, and sends a completion callback.

BUILD THESE NODES:

1. WEBHOOK node named "Receive Task"
   - Path: /domain-agent
   - Method: POST
   - Respond: Immediately

2. HTTP REQUEST node named "Fetch Document"
   - Method: GET
   - URL: https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/{{$json.task.document}}
   - Response Format: Text

3. AI AGENT node named "Update Document" (use Gemini)
   - Model: gemini-1.5-flash
   - System prompt: You update documentation. Make minimal targeted changes. Preserve formatting. Output JSON: {"changes_needed":true/false,"updated_content":"full updated doc","summary":"brief description"}
   - User message: Task: {{$json.task.description}}. Document: {{$json.task.document}}. Trigger: {{$json.trigger.message}}. Current content: {{$('Fetch Document').first().json.data}}

4. CODE node named "Parse AI Output"
   - JavaScript:
   const input = $('Receive Task').first().json;
   const text = $input.first().json.text || $input.first().json.output || '';
   const match = text.match(/\{[\s\S]*?\}/);
   let result = { changes_needed: false, summary: 'No changes' };
   if (match) {
     try { result = JSON.parse(match[0]); } catch(e) {}
   }
   return { ...result, task_id: input.task.task_id, document: input.task.document };

5. IF node named "Changes Needed"
   - Condition: changes_needed equals true
   - On false: Skip to Callback

6. HTTP REQUEST node named "Get File SHA"
   - Method: GET
   - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/{{$json.document}}
   - Authentication: Bearer Token (use GITHUB_TOKEN)
   - Add header: Accept: application/vnd.github.v3+json

7. CODE node named "Prepare Commit"
   - JavaScript:
   const prev = $('Parse AI Output').first().json;
   const sha = $input.first().json.sha;
   const content = Buffer.from(prev.updated_content || '').toString('base64');
   return { ...prev, sha, content_base64: content };

8. HTTP REQUEST node named "Commit to GitHub"
   - Method: PUT
   - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/{{$json.document}}
   - Authentication: Bearer Token
   - Body: {"message":"docs: {{$json.summary}}","content":"{{$json.content_base64}}","sha":"{{$json.sha}}"}

9. HTTP REQUEST node named "Send Callback" (connect BOTH paths here - from Changes Needed false AND from Commit)
   - Method: POST
   - URL: {{$env.N8N_WEBHOOK_URL}}/webhook/task-done-{{$json.task_id}}
   - Body: {"task_id":"{{$json.task_id}}","status":"completed","result":{"summary":"{{$json.summary}}"}}

Connect: 1→2→3→4→5→(true: 6→7→8→9, false: 9)
Make sure both paths merge at the Callback node.
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
   return {
     workflow: error.workflow?.name || 'Unknown',
     node: error.execution?.lastNodeExecuted || 'Unknown',
     message: error.execution?.error?.message || 'Unknown error',
     timestamp: new Date().toISOString(),
     task_id: error.execution?.data?.task_id || null
   };

3. IF node named "Has Task ID"
   - Condition: Check if task_id is not null
   - On true: Send failure callback
   - On false: End

4. HTTP REQUEST node named "Send Failure Callback"
   - Method: POST
   - URL: {{$env.N8N_WEBHOOK_URL}}/webhook/task-done-{{$json.task_id}}
   - Body: {"task_id":"{{$json.task_id}}","status":"failed","result":{"error":"{{$json.message}}"}}

5. (Optional) Add a Slack/Email node after Log Error to notify your team

Connect: 1→2→3→(true: 4, false: end)
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
5. [ ] Configure GitHub webhook to point to your Trigger workflow URL

---

## Quick Reference

| Workflow | Webhook Path | Purpose |
|----------|--------------|---------|
| Trigger | `/github-doc-trigger` | Entry point from GitHub |
| Distributor | `/task-distributor` | Queue & orchestration |
| Agent | `/domain-agent` | AI doc updates |
| Distributor | `/task-done-{id}` | Completion callbacks |

---

*Prompt Version: 2.0 - Canvas-specific format*
