# N8N AI Builder Prompt: State Reconciliation Workflow

> **IMPORTANT:** Build this workflow **EXACTLY** as specified. Do not add, rename, or reorganize nodes. Follow the node names, types, and connections precisely.

## Workflow Overview

**Name:** Doc Chain - State Reconciliation  
**Purpose:** Proactively verify that documentation file counts match actual repository state  
**Trigger:** Daily at 4 AM UTC + Manual webhook  
**Total Nodes:** 17

---

## 🏗️ Architecture (Updated)

```
┌────────────────┐     ┌────────────────┐
│ Daily Recon    │────▶│                │
│ (Schedule)     │     │     Start      │────▶ Workflow Config ────▶ Fetch Matrix
└────────────────┘     │    (Merge)     │
┌────────────────┐     │                │
│ Manual Trigger │────▶│                │
│ (Webhook)      │     └────────────────┘
└────────────────┘
                                │
        ┌───────────────────────┘
        ▼
   List Task Cards ──▶ Filter & Group ──▶ [LOOP: Count Files per Directory]
                                                         │
        ┌────────────────────────────────────────────────┘
        ▼
   Aggregate Counts ──▶ Fetch Indexes ──▶ Find Mismatches (file counts)
                                                │
                               ┌────────────────┴────────────────┐
                               ▼                                 ▼
                        Has Mismatches?                    Log In Sync
                               │ (true)                    (false branch)
                               ▼
                    Generate Corrections ──▶ Send to Distributor
                    (AI + Code parser)              │
                                                    ▼
                                              Summary Report
```

---

## Pre-Workflow Setup

Ensure you have:
1. [x] Workflows 1-4 already working
2. [x] GitHub API credential named "GitHub API Token" (Header Auth with PAT)
3. [x] Gemini API credential configured

---

# NODE DEFINITIONS (Build Exactly As Specified)

## Triggers & Start (Nodes 1-4)

### Node 1: SCHEDULE TRIGGER
- **Name:** `Daily Reconciliation`
- **Type:** Schedule Trigger
- **Settings:**
  - Trigger Interval: Days
  - Days Between Triggers: 1
  - Trigger at Hour: 4
  - Trigger at Minute: 0

### Node 2: WEBHOOK
- **Name:** `Manual Trigger`
- **Type:** Webhook
- **Settings:**
  - HTTP Method: POST
  - Path: `state-reconciliation`

### Node 3: MERGE
- **Name:** `Start`
- **Type:** Merge
- **Settings:**
  - Mode: Append
  - **Options:** (expand Options section)
    - Include Any Unpaired Items: ✅ Enabled
- **Connections:** Node 1 → Input 1, Node 2 → Input 2
- **Note:** Must use Append mode so workflow runs when only ONE trigger fires (manual OR schedule)

### Node 4: CODE
- **Name:** `Workflow Configuration`
- **Type:** Code
- **Purpose:** Set runtime configuration
- **JavaScript:**
```javascript
// Runtime configuration
// NOTE: Deduplication is handled by the Distributor, not here
// State Reconciliation always scans fresh and sends all detected mismatches
// 
// IMPORTANT: This workflow compares FILE COUNTS only, not completion status.
// Task card completion status is stored inside file content, which would
// require individual API calls to read. Instead, we trust the README as
// the source of truth for completion counts and only flag mismatches when
// file counts differ (files added/removed).

return {
  target_indexes: [
    'task-cards/README.md',
    'task-cards/INDEX.md'
  ],
  run_timestamp: new Date().toISOString()
};
```

---

## Fetch & Scan (Nodes 5-7)

### Node 5: HTTP REQUEST
- **Name:** `Fetch Matrix`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL: `https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json`

### Node 6: HTTP REQUEST
- **Name:** `List Task Cards`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL: `https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/git/trees/main?recursive=1`
  - Send Headers: Specify Headers → Using Fields Below
    - Header 1: Name=`Authorization`, Value=`Bearer YOUR_GITHUB_PAT`
    - Header 2: Name=`Accept`, Value=`application/vnd.github.v3+json`

### Node 7: CODE
- **Name:** `Filter and Group Cards`
- **Type:** Code
- **JavaScript:**
```javascript
const config = $('Workflow Configuration').first().json;
const tree = $input.first().json.tree || [];

// Filter to task card .md files (exclude README/INDEX)
const taskCards = tree
  .filter(item => 
    item.type === 'blob' &&
    item.path.startsWith('task-cards/') &&
    item.path.endsWith('.md') &&
    !item.path.endsWith('README.md') &&
    !item.path.endsWith('INDEX.md')
  )
  .map(item => ({
    path: item.path,
    sha: item.sha,
    directory: item.path.substring(0, item.path.lastIndexOf('/') + 1)
  }));

// Group by directory
const byDirectory = {};
for (const card of taskCards) {
  if (!byDirectory[card.directory]) byDirectory[card.directory] = [];
  byDirectory[card.directory].push(card);
}

// IMPORTANT: Return MULTIPLE ITEMS (one per directory) for Split In Batches
// Each item contains the directory name and its cards
return Object.entries(byDirectory).map(([dir, cards]) => ({
  json: {
    config,
    directory: dir,
    cards: cards,
    total_cards: taskCards.length
  }
}));
```
- **Note:** Returns multiple items (one per directory) so Split In Batches can iterate

---

## Loop: Process Each Directory (Nodes 8-10)

### Node 8: SPLIT IN BATCHES
- **Name:** `Process Each Directory`
- **Type:** Split In Batches
- **Settings:**
  - Batch Size: 1
- **Note:** Now receives multiple items (one per directory) from Filter and Group Cards. No special input expression needed.

### Node 9: CODE
- **Name:** `Extract Status from Cards`
- **Type:** Code
- **Note:** We count files per directory rather than trying to determine completion status from filenames. Task card status is stored inside file content (e.g., `**Status:** Complete`), which requires individual API calls to read. Instead, we use file counts and compare against README-claimed totals.
- **JavaScript:**
```javascript
// Get data from the current batch item - we already have the card list!
const batchItem = $input.first().json;
const dir = batchItem.directory;
const config = batchItem.config;
const cards = batchItem.cards || [];

// Just count files - don't try to determine completion from filenames.
// Task card completion status is stored inside file content, not filenames.
// README is the source of truth for completion counts.

const results = cards.map(card => ({
  path: card.path,
  name: card.path.split('/').pop()
}));

return {
  directory: dir,
  config: config,  // Pass config through for Aggregate
  cards: results,
  summary: { 
    file_count: results.length 
  }
};
```

---

## Note: Simplified Architecture

The original design had:
- Node 8: Split In Batches
- Node 9: Fetch Directory Contents (HTTP)
- Node 10: Extract Status from Cards

**Simplified to:**
- Node 8: Split In Batches  
- Node 9: Extract Status from Cards (counts files only, no HTTP fetch)

This eliminates the unnecessary HTTP call since directory listings don't include file content anyway. Task card completion status is stored inside file content (e.g., `**Status:** Complete`), not in filenames. Reading individual file contents would require N API calls per run. Instead, we count files per directory and compare to README-claimed totals.

---

## Aggregate & Compare (Nodes 11-13)

### Node 11: CODE
- **Name:** `Aggregate All Directories`
- **Type:** Code
- **JavaScript:**
```javascript
const loopResults = $input.all().map(item => item.json);
// Get config from the first result (all have same config)
const config = loopResults[0]?.config || $('Filter and Group Cards').first().json.config;

const summaries = {};
let totalFiles = 0;

for (const result of loopResults) {
  if (result.directory && result.summary) {
    summaries[result.directory] = result.summary;
    totalFiles += result.summary.file_count;
  }
}

return {
  config,
  by_directory: summaries,
  overall: { total_files: totalFiles },
  timestamp: new Date().toISOString()
};
```

### Node 12: HTTP REQUEST
- **Name:** `Fetch Current Indexes`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL: `https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/task-cards/README.md`
  - Send Headers: Using Fields Below
    - Header 1: Name=`Authorization`, Value=`Bearer YOUR_GITHUB_PAT`
    - Header 2: Name=`Accept`, Value=`application/vnd.github.v3+json`

### Node 13: CODE
- **Name:** `Find Mismatches`
- **Type:** Code
- **Note:** Compares file counts per directory against README-claimed totals. Since task card completion status is stored inside file content (not filenames), we only flag mismatches when file counts don't match. This avoids false positives from "Unknown" status detection.
- **JavaScript:**
```javascript
const actual = $('Aggregate All Directories').first().json;
const indexFile = $input.first().json;

let indexContent = '';
if (indexFile.content) {
  try {
    indexContent = Buffer.from(indexFile.content, 'base64').toString('utf8');
  } catch (e) { indexContent = ''; }
}

// Extract claimed totals from README: "X/Y Complete" → Y is total file count
const claimedBySection = {};
const sections = indexContent.split(/^###?\s+/m);

for (const section of sections) {
  const fractionMatch = section.match(/(\d+)\/(\d+)\s*Complete/i);
  if (fractionMatch) {
    const claimedTotal = parseInt(fractionMatch[2]);
    
    // Match to directory
    for (const dir of Object.keys(actual.by_directory)) {
      const dirName = dir.replace('task-cards/', '').replace(/\/$/, '').toLowerCase();
      const header = section.split('\n')[0]?.toLowerCase() || '';
      if (header.includes(dirName) || section.toLowerCase().includes(`/${dirName}/`)) {
        claimedBySection[dir] = { claimed_total: claimedTotal };
      }
    }
  }
}

const mismatches = [];

// Compare each directory's claimed total vs actual file count
for (const [dir, actualSummary] of Object.entries(actual.by_directory)) {
  const dirName = dir.replace('task-cards/', '').replace(/\/$/, '') || 'task-cards';
  const claimed = claimedBySection[dir];
  
  if (claimed && claimed.claimed_total !== actualSummary.file_count) {
    mismatches.push({
      type: 'file_count_mismatch',
      document: 'task-cards/README.md',
      directory: dir,
      claimed_total: claimed.claimed_total,
      actual_total: actualSummary.file_count,
      description: `${dirName}: README claims total of ${claimed.claimed_total} files but directory has ${actualSummary.file_count} files`
    });
  }
}

return {
  has_mismatches: mismatches.length > 0,
  mismatch_count: mismatches.length,
  mismatches,
  actual_state: actual,
  check_timestamp: new Date().toISOString()
};
```

---

## Decision & Action (Nodes 14-17)

### Node 14: IF
- **Name:** `Has Discrepancies?`
- **Type:** If
- **Settings:**
  - Condition: `{{ $json.has_mismatches }}` equals `true`
  - True Output → Node 15 (Generate Corrections)
  - False Output → Node 16 (Log Consistent)

### Node 15: AI AGENT
- **Name:** `Generate Corrections`
- **Type:** AI Agent
- **Settings:**
  - Model: Gemini 2.5 Flash (attach as sub-node)
  - **DO NOT attach JSON Output Parser** - we handle parsing in a separate Code node
  - System Prompt:
```
You generate CONSOLIDATED correction tasks to fix documentation file count mismatches.
Your goal is to CREATE THE MINIMUM NUMBER OF TASKS needed to fix all mismatches.

IMPORTANT: Mismatches are about FILE COUNTS, not completion status.
The README shows "X/Y Complete" where Y is the total file count for that directory.
When Y doesn't match the actual file count, the README needs updating.

CONSOLIDATION RULES:
1. Group all updates that target the SAME FILE into ONE task
2. For task-cards/README.md: Create ONE task listing ALL directory file count updates needed
3. Never create multiple tasks for the same document

Each task must have:
- task_id: unique identifier (e.g., "recon-readme-001")
- update_type: "FILE_COUNT_UPDATE"
- target: the file path to update
- document: same as target
- description: COMPREHENSIVE list of ALL file count corrections needed
- priority: 1 (high) if files were added/removed, else 2 (medium)
- changes: array of specific changes [{section: "directory name", from: "old_total", to: "new_total"}]

CRITICAL: Output ONLY raw JSON - NO markdown code blocks, NO backticks, NO formatting.

Example - consolidating file count mismatches into 1 task:
{"update_list_id":"ul-recon-TIMESTAMP","source":"state-reconciliation","tasks":[{"task_id":"recon-readme-001","update_type":"FILE_COUNT_UPDATE","target":"task-cards/README.md","document":"task-cards/README.md","description":"Update file counts: automation 0/4 → 0/5 (1 file added), integration 0/15 → 0/14 (1 file removed)","priority":1,"changes":[{"section":"automation","from":"4","to":"5"},{"section":"integration","from":"15","to":"14"}]}]}
```
  - User Message (Expression):
```
Fix these documentation file count mismatches:

{{ $json.mismatches.map(m => '- ' + m.description).join('\n') }}

Actual state as of {{ $json.check_timestamp }}:
- Total files: {{ $json.actual_state.overall.total_files }}

By directory (file counts):
{{ Object.entries($json.actual_state.by_directory).map(([d,s]) => '- ' + d + ': ' + s.file_count + ' files').join('\n') }}
```

### Node 15.5: CODE
- **Name:** `Clean AI Output`
- **Type:** Code
- **Purpose:** Strip markdown code blocks that AI may wrap around JSON output
- **JavaScript:**
```javascript
// Get raw AI output (may have markdown code blocks)
let rawOutput = $input.first().json.output || $input.first().json.text || '';

// If it's already an object, return it
if (typeof rawOutput === 'object') {
  return rawOutput;
}

// Strip markdown code blocks if present
rawOutput = rawOutput.trim();
if (rawOutput.startsWith('```json')) {
  rawOutput = rawOutput.replace(/^```json\n?/, '').replace(/\n?```$/, '');
} else if (rawOutput.startsWith('```')) {
  rawOutput = rawOutput.replace(/^```\n?/, '').replace(/\n?```$/, '');
}

// Parse JSON
try {
  return JSON.parse(rawOutput.trim());
} catch (e) {
  throw new Error('Failed to parse AI output as JSON: ' + e.message + '\nRaw: ' + rawOutput.substring(0, 200));
}
```
- **Connects from:** Node 15 (Generate Corrections)
- **Connects to:** Node 16.5 (Filter Recently Corrected)

### Node 16: CODE
- **Name:** `Log Consistent`
- **Type:** Code
- **JavaScript:**
```javascript
const actual = $('Aggregate All Directories').first().json;
return {
  status: 'in_sync',
  message: 'All documentation indexes match actual state',
  overall: actual.overall,
  timestamp: new Date().toISOString()
};
```
- **Note:** This is the FALSE branch endpoint

### Node 16.5: CODE
- **Name:** `Prepare for Distributor`
- **Type:** Code
- **Purpose:** Format tasks for Distributor (deduplication happens at Distributor level)
- **JavaScript:**
```javascript
// State Reconciliation always sends fresh tasks based on current repo state
// Deduplication is handled by the Distributor, which tracks:
// 1. Tasks already in pending queue (by document path)
// 2. Tasks completed in last hour (actual completions, not sends)

const aiOutput = $input.first().json;
const tasks = aiOutput.tasks || [];

console.log('Sending', tasks.length, 'consolidated tasks to Distributor');

// If no tasks, skip
if (tasks.length === 0) {
  return { skip: true, message: 'No corrections needed' };
}

return {
  skip: false,
  update_list_id: aiOutput.update_list_id || 'ul-recon-' + Date.now(),
  source: 'state-reconciliation',
  tasks: tasks
};
```
- **Connects from:** Node 15.5 (Clean AI Output)
- **Note:** No filtering here - Distributor handles deduplication based on actual completions

### Node 16.6: IF
- **Name:** `Has Tasks?`
- **Type:** If
- **Settings:**
  - Condition: `{{ $json.skip }}` equals `false`
  - True Output → Node 17 (Send to Distributor)
  - False Output → End (no tasks generated)

### Node 17: HTTP REQUEST
- **Name:** `Send Corrections`
- **Type:** HTTP Request
- **Settings:**
  - Method: POST
  - URL: `https://gitlitreview.app.n8n.cloud/webhook/task-distributor`
  - Body Content Type: JSON
  - Specify Body: Using JSON
  - JSON (Expression): `{{ $json }}`
  - **IMPORTANT:** Use `{{ $json }}` WITHOUT the `=` prefix. Click the expression toggle (fx) first.
- **Connects from:** Node 16.6 True branch (Should Send?)
- **CRITICAL:** The input `$json` must contain `update_list_id`, `source`, and `tasks` array.
  - This comes from Filter Recently Corrected → Should Send? → Send Corrections
  - Do NOT connect directly from Generate Corrections (wrong data format)

---

## Node Connections Summary

```
Node 1 (Daily Reconciliation) ──┐
                                ├──▶ Node 3 (Start)
Node 2 (Manual Trigger) ────────┘
                                      │
                                      ▼
                              Node 4 (Workflow Configuration)
                                      │
                                      ▼
                              Node 5 (Fetch Matrix)
                                      │
                                      ▼
                              Node 6 (List Task Cards)
                                      │
                                      ▼
                              Node 7 (Filter and Group Cards)
                                      │
                                      ▼
                              Node 8 (Process Each Directory) ◀──┐
                                      │                          │
                                      ▼                          │
                              Node 9 (Extract Status from Cards) │
                                      │                          │
                                      └─── (loop back) ──────────┘
                                      │
                                      ▼ (when loop complete)
                              Node 11 (Aggregate All Directories)
                                      │
                                      ▼
                              Node 12 (Fetch Current Indexes)
                                      │
                                      ▼
                              Node 13 (Find Mismatches)
                                      │
                                      ▼
                              Node 14 (Has Mismatches?)
                                      │
                        ┌─────────────┴─────────────┐
                        ▼ (true)                    ▼ (false)
              Node 15 (Generate Corrections)  Node 16 (Log In Sync)
                        │
                        ▼
              Node 15.5 (Clean AI Output)
                        │
                        ▼
              Node 16.5 (Prepare for Distributor)
                        │
                        ▼
              Node 16.6 (Has Tasks?)
                        │
                        ▼
              Node 17 (Send to Distributor)
```

---

## Verification Checklist

After building, verify:
- [ ] Both triggers connect to Start merge node
- [ ] Workflow Configuration provides runtime settings (no deduplication - that's in Distributor)
- [ ] Loop processes all task-cards subdirectories
- [ ] Extract Status from Cards counts files only (does NOT try to infer completion from filenames)
- [ ] Find Mismatches compares file counts to README-claimed totals
- [ ] AI Agent has NO JSON Output Parser (we use Clean AI Output node instead)
- [ ] AI prompt focuses on file count corrections (not completion status)
- [ ] Clean AI Output strips markdown and parses JSON
- [ ] Distributor URL is correct
- [ ] State Reconciliation sends ALL detected mismatches (deduplication happens at Distributor)

---

## Design Principles

### Fresh Eyes Every Time
State Reconciliation always scans the repository fresh and reports ALL mismatches found. It does NOT track what was previously sent. This ensures:
- No stale cache issues
- Repository state is always accurately assessed
- Tasks are never incorrectly filtered

### File Count Comparison (Not Completion Status)
Task card completion status is stored inside file content (e.g., `**Status:** Complete`), not in filenames. Reading individual file contents would require N API calls per run. Instead, we:
- Count files per directory (fast, single API call)
- Compare file counts to README-claimed totals
- Only flag mismatches when files are added/removed
- Trust README as source of truth for completion counts

### Deduplication at Distributor
The Distributor is the single source of truth for task state:
- Skips tasks for documents already in pending queue
- Skips tasks for documents completed in last hour
- This prevents duplicate work while allowing fresh scans

### Task Consolidation
The AI prompt instructs consolidation of updates by target document:
- Multiple directory file count updates → ONE task for README.md
- This minimizes the number of actual file edits needed

---

## Related Documentation

- [N8N_AI_BUILDER_PROMPT.md](./N8N_AI_BUILDER_PROMPT.md) - Workflows 1-4
- [N8N_STALENESS_REVIEW_BUILDER_PROMPT.md](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md) - Workflow 5
- [documentation_matrix.json](./documentation_matrix.json) - Matrix configuration
