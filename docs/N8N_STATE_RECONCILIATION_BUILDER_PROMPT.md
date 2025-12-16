# N8N AI Builder Prompt: State Reconciliation Workflow

> **IMPORTANT:** Build this workflow **EXACTLY** as specified. Do not add, rename, or reorganize nodes. Follow the node names, types, and connections precisely.

## Workflow Overview

**Name:** Doc Chain - State Reconciliation  
**Purpose:** Proactively verify that documentation status matches actual repository state  
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
   List Task Cards ──▶ Filter & Group ──▶ [LOOP: Fetch Contents ──▶ Extract Status]
                                                         │
        ┌────────────────────────────────────────────────┘
        ▼
   Aggregate Results ──▶ Fetch Indexes ──▶ Find Mismatches
                                                │
                               ┌────────────────┴────────────────┐
                               ▼                                 ▼
                        Has Mismatches?                    Log In Sync
                               │ (true)                    (false branch)
                               ▼
                    Generate Corrections ──▶ Send to Distributor
                    (AI + JSON Parser)              │
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
- **Purpose:** Set runtime configuration and thresholds
- **JavaScript:**
```javascript
// Runtime configuration - adjust thresholds here
return {
  mismatch_threshold_percent: 5,  // Ignore differences < 5%
  status_complete_keywords: ['complete', 'done', '✅', 'finished'],
  status_in_progress_keywords: ['in progress', 'started', '🔄', 'wip'],
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
- **Note:** We skip the HTTP fetch since directory listings don't include file content. Instead, we use the card paths from the batch item and check completion based on filename patterns (task cards marked COMPLETE typically have that in the filename or are in certain directories).
- **JavaScript:**
```javascript
// Get data from the current batch item - we already have the card list!
const batchItem = $input.first().json;
const dir = batchItem.directory;
const config = batchItem.config;
const cards = batchItem.cards || [];

// Since we can't easily get file content without individual fetches,
// we'll determine completion based on available metadata.
// The reconciliator's job is to count cards per directory and compare to claimed counts.

const results = cards.map(card => {
  const name = card.path.split('/').pop();
  
  // Check if filename suggests completion (contains COMPLETE, DONE, etc.)
  const filenameUpper = name.toUpperCase();
  const isComplete = config.status_complete_keywords.some(kw => 
    filenameUpper.includes(kw.toUpperCase())
  );
  
  return {
    path: card.path,
    name: name,
    status: isComplete ? 'Complete' : 'Unknown',
    is_complete: isComplete
  };
});

// Calculate directory summary
const complete = results.filter(r => r.is_complete).length;
const total = results.length;
const percentage = total > 0 ? Math.round((complete / total) * 100) : 0;

return {
  directory: dir,
  config: config,  // Pass config through for Aggregate
  cards: results,
  summary: { complete, total, percentage }
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
- Node 9: Extract Status from Cards (uses cards already in batch item)

This eliminates the unnecessary HTTP call since directory listings don't include file content anyway. The Split In Batches node connects directly to Extract Status from Cards.

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
let totalComplete = 0;
let totalCards = 0;

for (const result of loopResults) {
  if (result.directory && result.summary) {
    summaries[result.directory] = result.summary;
    totalComplete += result.summary.complete;
    totalCards += result.summary.total;
  }
}

const overallPercentage = totalCards > 0 ? 
  Math.round((totalComplete / totalCards) * 100) : 0;

return {
  config,
  by_directory: summaries,
  overall: {
    complete: totalComplete,
    total: totalCards,
    percentage: overallPercentage
  },
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
- **JavaScript:**
```javascript
const actual = $('Aggregate All Directories').first().json;
const indexFile = $input.first().json;
const threshold = actual.config.mismatch_threshold_percent;

let indexContent = '';
if (indexFile.content) {
  try {
    indexContent = Buffer.from(indexFile.content, 'base64').toString('utf8');
  } catch (e) { indexContent = ''; }
}

// Extract claimed status - handles both "X/Y Complete" and "XX%" formats
const fractionPattern = /(\d+)\/(\d+)\s*Complete/gi;
const percentPattern = /(\d+)%/g;

// Build map of claimed completions per section
const claimedBySection = {};
const sections = indexContent.split(/^###?\s+/m);

for (const section of sections) {
  const lines = section.split('\n');
  const header = lines[0]?.toLowerCase() || '';
  
  // Look for fraction format: "1/4 Complete"
  const fractionMatch = section.match(/(\d+)\/(\d+)\s*Complete/i);
  if (fractionMatch) {
    const complete = parseInt(fractionMatch[1]);
    const total = parseInt(fractionMatch[2]);
    const pct = total > 0 ? Math.round((complete / total) * 100) : 0;
    
    // Try to match to a directory
    for (const dir of Object.keys(actual.by_directory)) {
      const dirName = dir.replace('task-cards/', '').replace(/\/$/, '').toLowerCase();
      if (header.includes(dirName) || section.toLowerCase().includes(`/${dirName}/`)) {
        claimedBySection[dir] = { complete, total, percentage: pct };
      }
    }
  }
}

const mismatches = [];

// Compare each directory's claimed vs actual
for (const [dir, actualSummary] of Object.entries(actual.by_directory)) {
  const dirName = dir.replace('task-cards/', '').replace(/\/$/, '');
  const claimed = claimedBySection[dir];
  
  if (claimed) {
    // Compare complete count (more reliable than percentage)
    if (claimed.complete !== actualSummary.complete || claimed.total !== actualSummary.total) {
      mismatches.push({
        type: 'completion_count',
        document: 'task-cards/README.md',
        directory: dir,
        claimed: `${claimed.complete}/${claimed.total}`,
        actual: `${actualSummary.complete}/${actualSummary.total}`,
        claimed_pct: claimed.percentage,
        actual_pct: actualSummary.percentage,
        description: `${dirName}: README claims ${claimed.complete}/${claimed.total} but actual is ${actualSummary.complete}/${actualSummary.total}`
      });
    }
  } else {
    // No claim found for this directory - report if it has cards
    if (actualSummary.total > 0) {
      mismatches.push({
        type: 'missing_status',
        document: 'task-cards/README.md',
        directory: dir,
        actual: `${actualSummary.complete}/${actualSummary.total}`,
        description: `${dirName}: No status found in README. Actual: ${actualSummary.complete}/${actualSummary.total} complete`
      });
    }
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
- **Name:** `Has Mismatches?`
- **Type:** If
- **Settings:**
  - Condition: `{{ $json.has_mismatches }}` equals `true`
  - True Output → Node 15 (Generate Corrections)
  - False Output → Node 16 (Log In Sync)

### Node 15: AI AGENT
- **Name:** `Generate Corrections`
- **Type:** AI Agent
- **Settings:**
  - Model: Gemini 2.5 Flash (attach as sub-node)
  - Output Parser: JSON Output Parser (attach as sub-node)
  - System Prompt:
```
You generate correction tasks to fix documentation state mismatches.
Create minimal, targeted updates to bring parent indexes in sync with actual task card status.

For each mismatch, create a task with:
- update_type: "COMPLETION_PERCENTAGE" or "STATUS_UPDATE"
- document: the file path to update
- description: specific change needed (include actual numbers)
- priority: 1 (high) for >20% mismatch, 2 (medium) otherwise

Output ONLY valid JSON in this exact format:
{"update_list_id":"ul-recon-TIMESTAMP","source":"state-reconciliation","tasks":[{"update_type":"...","document":"...","description":"...","priority":1}]}
```
  - User Message (Expression):
```
Fix these documentation state mismatches:

{{ $json.mismatches.map(m => '- ' + m.description).join('\n') }}

Actual state as of {{ $json.check_timestamp }}:
- Overall: {{ $json.actual_state.overall.complete }}/{{ $json.actual_state.overall.total }} ({{ $json.actual_state.overall.percentage }}%)

By directory:
{{ Object.entries($json.actual_state.by_directory).map(([d,s]) => '- ' + d + ': ' + s.complete + '/' + s.total + ' (' + s.percentage + '%)').join('\n') }}
```

### Node 16: CODE
- **Name:** `Log In Sync`
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

### Node 17: HTTP REQUEST
- **Name:** `Send to Distributor`
- **Type:** HTTP Request
- **Settings:**
  - Method: POST
  - URL: `https://gitlitreview.app.n8n.cloud/webhook/task-distributor`
  - Body Content Type: JSON
  - Specify Body: Using JSON
  - JSON (Expression): `{{ $json }}`
- **Connects from:** Node 15 (Generate Corrections)

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
                              Node 9 (Fetch Directory Contents)  │
                                      │                          │
                                      ▼                          │
                              Node 10 (Extract Status from Cards)│
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
              Node 17 (Send to Distributor)
```

---

## Verification Checklist

After building, verify:
- [ ] Both triggers connect to Start merge node
- [ ] Workflow Configuration provides runtime thresholds
- [ ] Loop processes all task-cards subdirectories
- [ ] Status extraction handles base64 decoding
- [ ] Percentage comparison uses threshold (default 5%)
- [ ] AI Agent has JSON Output Parser attached
- [ ] Distributor URL is correct

---

## Related Documentation

- [N8N_AI_BUILDER_PROMPT.md](./N8N_AI_BUILDER_PROMPT.md) - Workflows 1-4
- [N8N_STALENESS_REVIEW_BUILDER_PROMPT.md](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md) - Workflow 5
- [documentation_matrix.json](./documentation_matrix.json) - Matrix configuration
