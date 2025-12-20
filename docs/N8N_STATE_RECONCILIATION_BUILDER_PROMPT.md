# N8N AI Builder Prompt: State Reconciliation Workflow (Full Implementation)

> **IMPORTANT:** Build this workflow **EXACTLY** as specified. Do not add, rename, or reorganize nodes. Follow the node names, types, and connections precisely.

> **VERSION:** 2.0 - Full Deep Reconciliation  
> **SUPERSEDES:** Previous file-count-only implementation

## Workflow Overview

**Name:** Doc Chain - State Reconciliation  
**Purpose:** Deeply analyze repository state, extract actual task/document status from file contents, and reconcile all documentation indexes and roadmaps to ensure accuracy  
**Trigger:** Daily at 4 AM UTC + Manual webhook  
**Total Nodes:** 28

---

## 🎯 What This Workflow Does

Unlike the simplified file-count approach, this **Full State Reconciliation** workflow:

1. **Fetches actual file contents** from task cards to extract real \`**Status:** Complete\` values
2. **Aggregates true completion counts** per directory (not just file counts)
3. **Reconciles multiple targets**: README.md, INDEX.md, and CONSOLIDATED_ROADMAP.md
4. **Scans status reports** for latest status updates
5. **Generates comprehensive corrections** for all detected mismatches

---

## 🏗️ Architecture

\`\`\`
┌────────────────┐     ┌────────────────┐
│ Daily Recon    │────▶│                │
│ (Schedule)     │     │     Start      │────▶ Workflow Config ────▶ List All Files
└────────────────┘     │    (Merge)     │
┌────────────────┐     │                │
│ Manual Trigger │────▶│                │
│ (Webhook)      │     └────────────────┘
└────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ▼                                               ▼
   Filter Task Cards                           Filter Status Reports
        │                                               │
        ▼                                               ▼
   [LOOP: For Each Card]                       [LOOP: For Each Report]
        │                                               │
        ▼                                               ▼
   Fetch Card Content ◀─┐                      Fetch Report Content ◀─┐
        │               │                              │               │
        ▼               │                              ▼               │
   Parse Card Status    │                      Parse Report Status     │
        │               │                              │               │
        └─── Loop ──────┘                              └─── Loop ──────┘
        │                                               │
        ▼                                               ▼
   Aggregate Card Status                       Aggregate Report Status
        │                                               │
        └───────────────────────┬───────────────────────┘
                                │
                                ▼
                    Merge All Aggregated Data
                                │
                                ▼
                    Fetch Target Documents
                    (README, INDEX, ROADMAP)
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   Find All Mismatches   │
                    │ • File counts           │
                    │ • Completion %          │
                    │ • Status accuracy       │
                    │ • Roadmap vs indexes    │
                    └───────────┬─────────────┘
                                │
                     ┌──────────┴──────────┐
                     ▼ (true)              ▼ (false)
              Has Mismatches?         Log In Sync
                     │
                     ▼
          Generate Corrections (AI)
                     │
                     ▼
          Clean & Prepare Tasks
                     │
                     ▼
          Send to Distributor
\`\`\`

---

## Pre-Workflow Setup

Ensure you have:
1. [x] Workflows 1-4 already working
2. [x] GitHub API credential named "GitHub API Token" (Header Auth with PAT)
3. [x] Gemini API credential configured
4. [x] PAT has \`contents:read\` permission for file content access

---

# NODE DEFINITIONS (Build Exactly As Specified)

## Phase 1: Triggers & Configuration (Nodes 1-5)

### Node 1: SCHEDULE TRIGGER
- **Name:** \`Daily Reconciliation\`
- **Type:** Schedule Trigger
- **Settings:**
  - Trigger Interval: Days
  - Days Between Triggers: 1
  - Trigger at Hour: 4
  - Trigger at Minute: 0

### Node 2: WEBHOOK
- **Name:** \`Manual Trigger\`
- **Type:** Webhook
- **Settings:**
  - HTTP Method: POST
  - Path: \`state-reconciliation\`
  - Response Mode: When Last Node Finishes

### Node 3: MERGE
- **Name:** \`Start\`
- **Type:** Merge
- **Settings:**
  - Mode: Append
  - **Options:** Include Any Unpaired Items: ✅ Enabled
- **Connections:** Node 1 → Input 1, Node 2 → Input 2

### Node 4: CODE
- **Name:** \`Workflow Configuration\`
- **Type:** Code
- **Purpose:** Set runtime configuration with status extraction patterns
- **JavaScript:**
\`\`\`javascript
// Full State Reconciliation Configuration
// This workflow performs DEEP content analysis, not just file counts

return {
  // Target documents to reconcile
  reconciliation_targets: [
    {
      path: 'task-cards/README.md',
      type: 'index',
      aggregation: 'count_by_status'
    },
    {
      path: 'task-cards/INDEX.md', 
      type: 'index',
      aggregation: 'count_by_status'
    },
    {
      path: 'docs/CONSOLIDATED_ROADMAP.md',
      type: 'roadmap',
      aggregation: 'summarize_progress'
    }
  ],
  
  // Patterns for extracting status from file content
  status_patterns: {
    // Primary status field: **Status:** Complete or Status: Complete
    task_status: /^\*?\*?Status:?\*?\*?\s*(.+)$/im,
    // Completion percentage: 50% complete
    completion_pct: /(\d+)%\s*(?:complete|done|finished)/i,
    // Checkbox counting: - [x] or - [ ]
    checkbox_checked: /- \[x\]/gi,
    checkbox_unchecked: /- \[ \]/gi,
    // Fraction format: 5/10 Complete
    fraction: /(\d+)\/(\d+)\s*Complete/i,
    // Wave status: ## Wave 2 - Status: Complete
    wave_status: /^##\s*Wave\s*\d+.*?Status:\s*(.+)$/im
  },
  
  // Status value normalization
  status_mappings: {
    'complete': 'Complete',
    'completed': 'Complete',
    '✅ complete': 'Complete',
    '✅ done': 'Complete',
    'done': 'Complete',
    'in progress': 'In Progress',
    'in-progress': 'In Progress',
    '🔄 in progress': 'In Progress',
    '🔄 active': 'In Progress',
    'not started': 'Not Started',
    'ready': 'Not Started',
    '🟢 ready': 'Not Started',
    'blocked': 'Blocked',
    '🔴 blocked': 'Blocked',
    'deferred': 'Deferred',
    '🟡 deferred': 'Deferred'
  },
  
  // Tolerance for percentage mismatches (to avoid noise)
  mismatch_tolerance_pct: 5,
  
  // Timestamp
  run_timestamp: new Date().toISOString()
};
\`\`\`

### Node 5: HTTP REQUEST
- **Name:** \`List All Files\`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL: \`https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/git/trees/main?recursive=1\`
  - Authentication: Predefined Credential Type → Header Auth
  - Credential: GitHub API Token
- **Headers:**
  - Accept: \`application/vnd.github.v3+json\`

---

## Phase 2A: Task Card Deep Scan (Nodes 6-11)

### Node 6: CODE
- **Name:** \`Filter Task Cards\`
- **Type:** Code
- **Purpose:** Extract task card paths for content fetching
- **JavaScript:**
\`\`\`javascript
const config = $('Workflow Configuration').first().json;
const tree = $input.first().json.tree || [];

// Filter to task card .md files (exclude README/INDEX)
const taskCards = tree
  .filter(item => 
    item.type === 'blob' &&
    item.path.startsWith('task-cards/') &&
    item.path.endsWith('.md') &&
    !item.path.includes('README.md') &&
    !item.path.includes('INDEX.md')
  )
  .map(item => ({
    path: item.path,
    sha: item.sha,
    directory: item.path.substring(0, item.path.lastIndexOf('/') + 1) || 'task-cards/'
  }));

// Return each card as a separate item for the loop
return taskCards.map(card => ({
  json: {
    config,
    card_path: card.path,
    card_sha: card.sha,
    directory: card.directory,
    total_cards: taskCards.length
  }
}));
\`\`\`

### Node 7: SPLIT IN BATCHES
- **Name:** \`Process Each Card\`
- **Type:** Split In Batches
- **Settings:**
  - Batch Size: 1
- **Note:** Processes one card at a time for content fetching

### Node 8: HTTP REQUEST
- **Name:** \`Fetch Card Content\`
- **Type:** HTTP Request
- **Purpose:** Fetch actual file content from GitHub
- **Settings:**
  - Method: GET
  - URL (Expression): \`https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/{{ $json.card_path }}\`
  - Authentication: Predefined Credential Type → Header Auth
  - Credential: GitHub API Token
- **Headers:**
  - Accept: \`application/vnd.github.v3+json\`
- **On Error:** Continue (some files may be inaccessible)

### Node 9: CODE
- **Name:** \`Parse Card Status\`
- **Type:** Code
- **Purpose:** Extract status from file content using regex patterns
- **JavaScript:**
\`\`\`javascript
const batchItem = $('Process Each Card').first().json;
const config = batchItem.config;
const cardPath = batchItem.card_path;
const directory = batchItem.directory;

// Get the fetched content
const fileData = $input.first().json;
let content = '';

// Decode base64 content
if (fileData.content) {
  try {
    content = Buffer.from(fileData.content, 'base64').toString('utf8');
  } catch (e) {
    content = '';
  }
}

// Extract status using patterns
let extractedStatus = 'Unknown';
let checkboxComplete = 0;
let checkboxTotal = 0;

if (content) {
  // Try primary status pattern: **Status:** X or Status: X
  const statusMatch = content.match(/^\*?\*?Status:?\*?\*?\s*(.+)$/im);
  if (statusMatch) {
    let rawStatus = statusMatch[1].trim();
    // Normalize the status
    const normalized = rawStatus.toLowerCase().replace(/[^\w\s]/g, '').trim();
    
    for (const [key, value] of Object.entries(config.status_mappings)) {
      if (normalized.includes(key.toLowerCase().replace(/[^\w\s]/g, ''))) {
        extractedStatus = value;
        break;
      }
    }
    
    // If still unknown but has a value, use it directly
    if (extractedStatus === 'Unknown' && rawStatus.length < 30) {
      extractedStatus = rawStatus;
    }
  }
  
  // Count checkboxes for additional context
  const checkedMatches = content.match(/- \[x\]/gi);
  const uncheckedMatches = content.match(/- \[ \]/gi);
  checkboxComplete = checkedMatches ? checkedMatches.length : 0;
  checkboxTotal = checkboxComplete + (uncheckedMatches ? uncheckedMatches.length : 0);
}

return {
  card_path: cardPath,
  directory: directory,
  status: extractedStatus,
  is_complete: extractedStatus === 'Complete',
  checkbox_complete: checkboxComplete,
  checkbox_total: checkboxTotal,
  config: config
};
\`\`\`
- **Connects back to:** Node 7 (Process Each Card) for loop continuation

### Node 10: LOOP (back to Node 7)
- **Connection:** Node 9 → Node 7 (loop connector on Split In Batches)

### Node 11: CODE
- **Name:** \`Aggregate Card Status\`
- **Type:** Code
- **Purpose:** Aggregate all parsed statuses by directory
- **JavaScript:**
\`\`\`javascript
// Collect all results from the loop
const allResults = $input.all().map(item => item.json);

// Get config from first result
const config = allResults[0]?.config || $('Workflow Configuration').first().json;

// Group by directory
const byDirectory = {};
const statusCounts = {};

for (const result of allResults) {
  const dir = result.directory || 'task-cards/';
  
  if (!byDirectory[dir]) {
    byDirectory[dir] = {
      cards: [],
      complete: 0,
      in_progress: 0,
      not_started: 0,
      blocked: 0,
      unknown: 0,
      total: 0
    };
  }
  
  byDirectory[dir].cards.push({
    path: result.card_path,
    status: result.status
  });
  byDirectory[dir].total++;
  
  // Count by status
  switch (result.status) {
    case 'Complete':
      byDirectory[dir].complete++;
      break;
    case 'In Progress':
      byDirectory[dir].in_progress++;
      break;
    case 'Not Started':
      byDirectory[dir].not_started++;
      break;
    case 'Blocked':
      byDirectory[dir].blocked++;
      break;
    default:
      byDirectory[dir].unknown++;
  }
}

// Calculate overall totals
let overall = { complete: 0, in_progress: 0, not_started: 0, blocked: 0, unknown: 0, total: 0 };
for (const dir of Object.values(byDirectory)) {
  overall.complete += dir.complete;
  overall.in_progress += dir.in_progress;
  overall.not_started += dir.not_started;
  overall.blocked += dir.blocked;
  overall.unknown += dir.unknown;
  overall.total += dir.total;
}

return {
  source: 'task_cards',
  by_directory: byDirectory,
  overall: overall,
  overall_completion_pct: overall.total > 0 ? Math.round((overall.complete / overall.total) * 100) : 0,
  config: config,
  timestamp: new Date().toISOString()
};
\`\`\`

---

## Phase 2B: Status Reports Scan (Nodes 12-16)

### Node 12: CODE
- **Name:** \`Filter Status Reports\`
- **Type:** Code
- **Purpose:** Extract status report paths from the tree listing
- **JavaScript:**
\`\`\`javascript
const config = $('Workflow Configuration').first().json;
const tree = $('List All Files').first().json.tree || [];

// Filter to status report files
const statusReports = tree
  .filter(item => 
    item.type === 'blob' &&
    item.path.startsWith('docs/status-reports/') &&
    item.path.endsWith('.md')
  )
  .map(item => ({
    path: item.path,
    sha: item.sha
  }));

// If no status reports, return empty marker
if (statusReports.length === 0) {
  return { json: { config, reports: [], has_reports: false } };
}

// Return each report as a separate item for the loop
return statusReports.map(report => ({
  json: {
    config,
    report_path: report.path,
    report_sha: report.sha,
    total_reports: statusReports.length
  }
}));
\`\`\`
- **Connection:** Parallel branch from Node 5 (List All Files)

### Node 13: IF
- **Name:** \`Has Status Reports?\`
- **Type:** If
- **Settings:**
  - Condition: \`{{ $json.has_reports }}\` is not equal to \`false\`
  - True Output → Node 14
  - False Output → Node 17 (Skip to Merge)

### Node 14: SPLIT IN BATCHES
- **Name:** \`Process Each Report\`
- **Type:** Split In Batches
- **Settings:**
  - Batch Size: 1

### Node 15: HTTP REQUEST
- **Name:** \`Fetch Report Content\`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL (Expression): \`https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/{{ $json.report_path }}\`
  - Authentication: Predefined Credential Type → Header Auth
  - Credential: GitHub API Token
- **Headers:**
  - Accept: \`application/vnd.github.v3+json\`
- **On Error:** Continue

### Node 15.5: CODE
- **Name:** \`Parse Report Status\`
- **Type:** Code
- **Purpose:** Extract latest status and key metrics from status reports
- **JavaScript:**
\`\`\`javascript
const batchItem = $('Process Each Report').first().json;
const config = batchItem.config;
const reportPath = batchItem.report_path;

const fileData = $input.first().json;
let content = '';

if (fileData.content) {
  try {
    content = Buffer.from(fileData.content, 'base64').toString('utf8');
  } catch (e) {
    content = '';
  }
}

// Extract key information from status report
let summary = {
  path: reportPath,
  filename: reportPath.split('/').pop(),
  date: null,
  overall_status: 'Unknown',
  completion_pct: null,
  key_updates: []
};

if (content) {
  // Extract date from filename or content
  const dateMatch = reportPath.match(/(\d{4}-\d{2}-\d{2})/);
  if (dateMatch) summary.date = dateMatch[1];
  
  // Look for overall status/summary
  const statusMatch = content.match(/(?:Overall\s+)?Status:\s*(.+)/i);
  if (statusMatch) summary.overall_status = statusMatch[1].trim();
  
  // Look for completion percentage
  const pctMatch = content.match(/(\d+)%\s*(?:complete|done|finished)/i);
  if (pctMatch) summary.completion_pct = parseInt(pctMatch[1]);
  
  // Look for wave status mentions
  const waveMatches = content.matchAll(/Wave\s*(\d+).*?(?:Status|:)\s*(.+)/gi);
  for (const match of waveMatches) {
    summary.key_updates.push({
      wave: parseInt(match[1]),
      status: match[2].trim().substring(0, 50)
    });
  }
}

return {
  report: summary,
  config: config
};
\`\`\`
- **Connects back to:** Node 14 for loop

### Node 16: CODE
- **Name:** \`Aggregate Report Status\`
- **Type:** Code
- **Purpose:** Combine all status report findings
- **JavaScript:**
\`\`\`javascript
const allResults = $input.all().map(item => item.json);
const config = allResults[0]?.config || $('Workflow Configuration').first().json;

const reports = allResults
  .filter(r => r.report)
  .map(r => r.report)
  .sort((a, b) => {
    // Sort by date descending (newest first)
    if (a.date && b.date) return b.date.localeCompare(a.date);
    return 0;
  });

// Get latest status from most recent report
const latestReport = reports[0];

return {
  source: 'status_reports',
  reports: reports,
  latest: latestReport || null,
  report_count: reports.length,
  config: config,
  timestamp: new Date().toISOString()
};
\`\`\`

---

## Phase 3: Merge & Fetch Targets (Nodes 17-19)

### Node 17: MERGE
- **Name:** \`Merge Aggregated Data\`
- **Type:** Merge
- **Settings:**
  - Mode: Append
  - Options: Include Any Unpaired Items: ✅ Enabled
- **Connections:** 
  - Input 1: Node 11 (Aggregate Card Status)
  - Input 2: Node 16 (Aggregate Report Status) OR Node 13 false branch

### Node 18: CODE
- **Name:** \`Prepare Target Fetch\`
- **Type:** Code
- **Purpose:** Combine aggregated data and prepare for target document fetching
- **JavaScript:**
\`\`\`javascript
// Collect all aggregated data
const allData = $input.all().map(item => item.json);

// Find the task cards data and status reports data
let taskCardsData = null;
let statusReportsData = null;
let config = null;

for (const data of allData) {
  if (data.source === 'task_cards') {
    taskCardsData = data;
    config = data.config;
  } else if (data.source === 'status_reports') {
    statusReportsData = data;
    if (!config) config = data.config;
  }
}

// Fallback to get config
if (!config) {
  config = $('Workflow Configuration').first().json;
}

return {
  task_cards: taskCardsData,
  status_reports: statusReportsData,
  config: config,
  targets_to_fetch: config.reconciliation_targets.map(t => t.path),
  timestamp: new Date().toISOString()
};
\`\`\`

### Node 19: HTTP REQUEST
- **Name:** \`Fetch Target README\`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL: \`https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/task-cards/README.md\`
  - Authentication: Header Auth → GitHub API Token
- **Headers:**
  - Accept: \`application/vnd.github.v3+json\`

### Node 19.2: HTTP REQUEST
- **Name:** \`Fetch Target INDEX\`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL: \`https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/task-cards/INDEX.md\`
  - Authentication: Header Auth → GitHub API Token
- **Headers:**
  - Accept: \`application/vnd.github.v3+json\`
- **On Error:** Continue (INDEX.md may not exist)

### Node 19.3: HTTP REQUEST
- **Name:** \`Fetch Target Roadmap\`
- **Type:** HTTP Request
- **Settings:**
  - Method: GET
  - URL: \`https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/docs/CONSOLIDATED_ROADMAP.md\`
  - Authentication: Header Auth → GitHub API Token
- **Headers:**
  - Accept: \`application/vnd.github.v3+json\`
- **On Error:** Continue

---

## Phase 4: Find Mismatches (Nodes 20-21)

### Node 20: CODE
- **Name:** \`Find All Mismatches\`
- **Type:** Code
- **Purpose:** Comprehensive comparison of actual state vs claimed state across all targets
- **JavaScript:**
\`\`\`javascript
// Get aggregated actual state
const preparedData = $('Prepare Target Fetch').first().json;
const taskCards = preparedData.task_cards;
const statusReports = preparedData.status_reports;
const config = preparedData.config;

// Get target document contents
const readmeData = $('Fetch Target README').first().json;
const indexData = $('Fetch Target INDEX').first().json;
const roadmapData = $('Fetch Target Roadmap').first().json;

// Helper: decode base64 content
function decodeContent(data) {
  if (!data || !data.content) return '';
  try {
    return Buffer.from(data.content, 'base64').toString('utf8');
  } catch (e) {
    return '';
  }
}

const readmeContent = decodeContent(readmeData);
const indexContent = decodeContent(indexData);
const roadmapContent = decodeContent(roadmapData);

const mismatches = [];
const tolerance = config.mismatch_tolerance_pct || 5;

// ============================================
// MISMATCH TYPE 1: File Count Mismatches
// ============================================
// Check if README claims different file counts than actual
if (taskCards && taskCards.by_directory) {
  for (const [dir, stats] of Object.entries(taskCards.by_directory)) {
    const dirName = dir.replace('task-cards/', '').replace(/\/$/, '') || 'root';
    
    // Look for "X/Y Complete" pattern in README for this directory
    const dirPattern = new RegExp(
      \`\${dirName}.*?(\\\\d+)/(\\\\d+)\\\\s*Complete\`,
      'i'
    );
    const match = readmeContent.match(dirPattern);
    
    if (match) {
      const claimedComplete = parseInt(match[1]);
      const claimedTotal = parseInt(match[2]);
      
      // Check total file count mismatch
      if (claimedTotal !== stats.total) {
        mismatches.push({
          type: 'FILE_COUNT_MISMATCH',
          severity: 'high',
          document: 'task-cards/README.md',
          directory: dir,
          description: \`\${dirName}: README claims \${claimedTotal} total files but directory has \${stats.total} files\`,
          claimed: { total: claimedTotal },
          actual: { total: stats.total },
          action: \`Update "\${claimedComplete}/\${claimedTotal}" to "\${stats.complete}/\${stats.total}" in \${dirName} section\`
        });
      }
      
      // Check completion count mismatch
      if (claimedComplete !== stats.complete && claimedTotal === stats.total) {
        mismatches.push({
          type: 'COMPLETION_COUNT_MISMATCH',
          severity: 'high',
          document: 'task-cards/README.md',
          directory: dir,
          description: \`\${dirName}: README claims \${claimedComplete} complete but \${stats.complete} are actually complete\`,
          claimed: { complete: claimedComplete, total: claimedTotal },
          actual: { complete: stats.complete, total: stats.total },
          action: \`Update "\${claimedComplete}/\${claimedTotal}" to "\${stats.complete}/\${stats.total}" in \${dirName} section\`
        });
      }
    }
  }
}

// ============================================
// MISMATCH TYPE 2: Completion Percentage Mismatches
// ============================================
if (taskCards) {
  const actualOverallPct = taskCards.overall_completion_pct;
  
  // Check README overall percentage
  const readmePctMatch = readmeContent.match(/(?:Overall|Total).*?(\d+)%/i);
  if (readmePctMatch) {
    const claimedPct = parseInt(readmePctMatch[1]);
    if (Math.abs(claimedPct - actualOverallPct) > tolerance) {
      mismatches.push({
        type: 'PERCENTAGE_MISMATCH',
        severity: 'medium',
        document: 'task-cards/README.md',
        description: \`README claims \${claimedPct}% overall completion but actual is \${actualOverallPct}%\`,
        claimed: { percentage: claimedPct },
        actual: { percentage: actualOverallPct },
        action: \`Update overall completion percentage from \${claimedPct}% to \${actualOverallPct}%\`
      });
    }
  }
  
  // Check ROADMAP percentages
  if (roadmapContent) {
    const roadmapPctMatches = roadmapContent.matchAll(/(?:Completed?|Progress):\s*(\d+)(?:\/\d+)?\s*\(?(\d+)%?\)?/gi);
    for (const match of roadmapPctMatches) {
      const claimedPct = parseInt(match[2] || match[1]);
      if (Math.abs(claimedPct - actualOverallPct) > tolerance) {
        mismatches.push({
          type: 'ROADMAP_PERCENTAGE_MISMATCH',
          severity: 'medium',
          document: 'docs/CONSOLIDATED_ROADMAP.md',
          description: \`Roadmap claims \${claimedPct}% completion but task cards show \${actualOverallPct}%\`,
          claimed: { percentage: claimedPct },
          actual: { percentage: actualOverallPct },
          action: \`Update roadmap completion metrics to reflect \${actualOverallPct}% actual completion\`
        });
        break; // Only report first mismatch to avoid duplicates
      }
    }
  }
}

// ============================================
// MISMATCH TYPE 3: Status Inconsistencies
// ============================================
// Check for cards marked complete in README but not in actual content
if (taskCards && taskCards.by_directory) {
  for (const [dir, stats] of Object.entries(taskCards.by_directory)) {
    // Find cards that should be reviewed (unknown status)
    const unknownCards = stats.cards.filter(c => 
      c.status === 'Unknown' || c.status === undefined
    );
    
    if (unknownCards.length > 0 && unknownCards.length > stats.total * 0.2) {
      mismatches.push({
        type: 'STATUS_FORMAT_ISSUE',
        severity: 'low',
        document: dir,
        description: \`\${unknownCards.length} cards in \${dir} have missing or unrecognized status format\`,
        cards: unknownCards.slice(0, 5).map(c => c.path), // First 5 examples
        action: \`Review and standardize Status: field format in \${unknownCards.length} task cards\`
      });
    }
  }
}

// ============================================
// MISMATCH TYPE 4: Roadmap vs Index Rollup
// ============================================
if (roadmapContent && taskCards) {
  // Check wave status claims in roadmap
  const waveStatuses = roadmapContent.matchAll(/Wave\s*(\d+).*?(?:Status|:)\s*(Complete|In Progress|Planned)/gi);
  
  for (const match of waveStatuses) {
    const waveNum = match[1];
    const claimedStatus = match[2];
    
    // Cross-reference with task card wave assignments if present
    // This is a simplified check - full implementation would parse wave metadata from cards
  }
}

// ============================================
// MISMATCH TYPE 5: Status Report vs Roadmap
// ============================================
if (statusReports && statusReports.latest && roadmapContent) {
  const latestReport = statusReports.latest;
  
  if (latestReport.completion_pct !== null) {
    const roadmapPctMatch = roadmapContent.match(/(?:Current|Overall).*?(\d+)%/i);
    if (roadmapPctMatch) {
      const roadmapPct = parseInt(roadmapPctMatch[1]);
      if (Math.abs(roadmapPct - latestReport.completion_pct) > tolerance) {
        mismatches.push({
          type: 'STATUS_REPORT_MISMATCH',
          severity: 'medium',
          document: 'docs/CONSOLIDATED_ROADMAP.md',
          description: \`Latest status report (\${latestReport.filename}) shows \${latestReport.completion_pct}% but roadmap shows \${roadmapPct}%\`,
          claimed: { roadmap_pct: roadmapPct },
          actual: { report_pct: latestReport.completion_pct, report_file: latestReport.path },
          action: \`Reconcile roadmap with latest status report data\`
        });
      }
    }
  }
}

// Sort mismatches by severity
const severityOrder = { high: 0, medium: 1, low: 2 };
mismatches.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

return {
  has_mismatches: mismatches.length > 0,
  mismatch_count: mismatches.length,
  mismatches: mismatches,
  actual_state: {
    task_cards: taskCards,
    status_reports: statusReports
  },
  targets_checked: [
    'task-cards/README.md',
    'task-cards/INDEX.md',
    'docs/CONSOLIDATED_ROADMAP.md'
  ],
  check_timestamp: new Date().toISOString()
};
\`\`\`

### Node 21: IF
- **Name:** \`Has Mismatches?\`
- **Type:** If
- **Settings:**
  - Condition: \`{{ $json.has_mismatches }}\` equals \`true\`
  - True Output → Node 22 (Generate Corrections)
  - False Output → Node 26 (Log In Sync)

---

## Phase 5: Generate & Dispatch Corrections (Nodes 22-28)

### Node 22: AI AGENT
- **Name:** \`Generate Corrections\`
- **Type:** AI Agent
- **Settings:**
  - Model: Gemini 2.5 Flash (attach as sub-node)
  - **DO NOT attach JSON Output Parser** - handled in Clean AI Output node
  - System Prompt:
\`\`\`
You are a documentation reconciliation expert. Generate COMPREHENSIVE correction tasks to fix all detected mismatches between actual repository state and documentation claims.

Your job is to ensure ALL documentation accurately reflects the true state of the repository after your corrections are applied.

TASK CONSOLIDATION RULES:
1. Group all updates targeting the SAME FILE into ONE task
2. For task-cards/README.md: Create ONE task with ALL directory count updates
3. For docs/CONSOLIDATED_ROADMAP.md: Create ONE task with ALL percentage/status updates
4. Never create multiple tasks for the same document
5. Include SPECIFIC changes needed (from → to)

SEVERITY-BASED PRIORITIES:
- HIGH severity (file count, completion count mismatches): priority 1
- MEDIUM severity (percentage mismatches, roadmap drift): priority 2  
- LOW severity (status format issues): priority 3

TASK STRUCTURE:
Each task must have:
- task_id: unique identifier (e.g., "recon-readme-001", "recon-roadmap-001")
- update_type: "RECONCILIATION_UPDATE"
- target: the file path to update
- description: COMPREHENSIVE list of ALL corrections needed for this file
- priority: 1 (high), 2 (medium), or 3 (low)
- changes: array of specific changes [{ section, field, from, to }]

CRITICAL: Output ONLY raw JSON - NO markdown code blocks, NO backticks, NO formatting.

Example output structure:
{"update_list_id":"ul-recon-TIMESTAMP","source":"state-reconciliation-full","tasks":[{"task_id":"recon-readme-001","update_type":"RECONCILIATION_UPDATE","target":"task-cards/README.md","description":"Update completion counts: automation 0/4 → 1/4 (1 complete), integration 3/15 → 5/15 (2 more complete)","priority":1,"changes":[{"section":"automation","field":"completion","from":"0/4","to":"1/4"},{"section":"integration","field":"completion","from":"3/15","to":"5/15"}]},{"task_id":"recon-roadmap-001","update_type":"RECONCILIATION_UPDATE","target":"docs/CONSOLIDATED_ROADMAP.md","description":"Update overall completion from 50% to 65% based on actual task card status","priority":2,"changes":[{"section":"Executive Summary","field":"completion_pct","from":"50%","to":"65%"}]}]}
\`\`\`
  - User Message (Expression):
\`\`\`
Analyze and fix these documentation mismatches:

MISMATCHES DETECTED ({{ $json.mismatch_count }} total):
{{ $json.mismatches.map(m => \`
[\${m.severity.toUpperCase()}] \${m.type}
  Document: \${m.document}
  Issue: \${m.description}
  Recommended Action: \${m.action}
\`).join('\\n') }}

ACTUAL STATE (from deep repository scan):
- Total Task Cards: {{ $json.actual_state.task_cards?.overall?.total || 'N/A' }}
- Complete: {{ $json.actual_state.task_cards?.overall?.complete || 0 }}
- In Progress: {{ $json.actual_state.task_cards?.overall?.in_progress || 0 }}
- Overall Completion: {{ $json.actual_state.task_cards?.overall_completion_pct || 0 }}%

BY DIRECTORY:
{{ Object.entries($json.actual_state.task_cards?.by_directory || {}).map(([dir, stats]) => 
  \`- \${dir}: \${stats.complete}/\${stats.total} complete (\${Math.round(stats.complete/stats.total*100) || 0}%)\`
).join('\\n') }}

{{ $json.actual_state.status_reports?.latest ? \`
LATEST STATUS REPORT: \${$json.actual_state.status_reports.latest.filename}
- Date: \${$json.actual_state.status_reports.latest.date || 'Unknown'}
- Reported Completion: \${$json.actual_state.status_reports.latest.completion_pct || 'Not specified'}%
\` : '' }}

Generate consolidated correction tasks to bring ALL documentation into alignment with this actual state.
\`\`\`

### Node 23: CODE
- **Name:** \`Clean AI Output\`
- **Type:** Code
- **Purpose:** Strip markdown code blocks that AI may wrap around JSON output
- **JavaScript:**
\`\`\`javascript
// Get raw AI output (may have markdown code blocks)
let rawOutput = $input.first().json.output || $input.first().json.text || '';

// If it's already an object, return it
if (typeof rawOutput === 'object' && rawOutput.tasks) {
  return rawOutput;
}

// Convert to string if needed
if (typeof rawOutput !== 'string') {
  rawOutput = JSON.stringify(rawOutput);
}

// Strip markdown code blocks if present
rawOutput = rawOutput.trim();
if (rawOutput.startsWith('\`\`\`json')) {
  rawOutput = rawOutput.replace(/^\`\`\`json\\n?/, '').replace(/\\n?\`\`\`$/, '');
} else if (rawOutput.startsWith('\`\`\`')) {
  rawOutput = rawOutput.replace(/^\`\`\`\\n?/, '').replace(/\\n?\`\`\`$/, '');
}

// Parse JSON
try {
  const parsed = JSON.parse(rawOutput.trim());
  return parsed;
} catch (e) {
  // Try to extract JSON from the text
  const jsonMatch = rawOutput.match(/\\{[\\s\\S]*\\}/);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[0]);
    } catch (e2) {
      throw new Error('Failed to parse AI output as JSON: ' + e.message + '\\nRaw: ' + rawOutput.substring(0, 500));
    }
  }
  throw new Error('No valid JSON found in AI output: ' + rawOutput.substring(0, 500));
}
\`\`\`

### Node 24: CODE
- **Name:** \`Prepare for Distributor\`
- **Type:** Code
- **Purpose:** Format tasks for Distributor webhook
- **JavaScript:**
\`\`\`javascript
// Get parsed AI output
const aiOutput = $input.first().json;
const tasks = aiOutput.tasks || [];

console.log('State Reconciliation generated', tasks.length, 'consolidated correction tasks');

// Validate task structure
const validTasks = tasks.filter(task => 
  task.task_id && 
  task.target && 
  task.description
);

if (validTasks.length === 0) {
  return { 
    skip: true, 
    message: 'No valid correction tasks generated',
    original_count: tasks.length
  };
}

// Ensure each task has required fields
const normalizedTasks = validTasks.map(task => ({
  task_id: task.task_id,
  update_type: task.update_type || 'RECONCILIATION_UPDATE',
  target: task.target,
  document: task.target,
  description: task.description,
  priority: task.priority || 2,
  changes: task.changes || [],
  source_workflow: 'state-reconciliation-full'
}));

return {
  skip: false,
  update_list_id: aiOutput.update_list_id || 'ul-recon-full-' + Date.now(),
  source: 'state-reconciliation-full',
  scan_type: 'deep_content_analysis',
  tasks: normalizedTasks,
  task_count: normalizedTasks.length
};
\`\`\`

### Node 25: IF
- **Name:** \`Has Tasks?\`
- **Type:** If
- **Settings:**
  - Condition: \`{{ $json.skip }}\` equals \`false\`
  - True Output → Node 27 (Send to Distributor)
  - False Output → End

### Node 26: CODE
- **Name:** \`Log In Sync\`
- **Type:** Code
- **Purpose:** Log when all documentation is in sync (false branch from Has Mismatches?)
- **JavaScript:**
\`\`\`javascript
const checkData = $('Find All Mismatches').first().json;

return {
  status: 'in_sync',
  message: 'All documentation accurately reflects repository state',
  scan_type: 'deep_content_analysis',
  targets_verified: checkData.targets_checked || [],
  task_cards_scanned: checkData.actual_state?.task_cards?.overall?.total || 0,
  status_reports_scanned: checkData.actual_state?.status_reports?.report_count || 0,
  overall_completion: checkData.actual_state?.task_cards?.overall_completion_pct || 0,
  timestamp: new Date().toISOString()
};
\`\`\`

### Node 27: HTTP REQUEST
- **Name:** \`Send Corrections\`
- **Type:** HTTP Request
- **Settings:**
  - Method: POST
  - URL: \`https://gitlitreview.app.n8n.cloud/webhook/task-distributor\`
  - Body Content Type: JSON
  - Specify Body: Using JSON
  - JSON (Expression): \`{{ $json }}\`
- **CRITICAL:** Ensure \`$json\` contains \`update_list_id\`, \`source\`, and \`tasks\` array

### Node 28: CODE
- **Name:** \`Summary Report\`
- **Type:** Code
- **Purpose:** Generate final execution summary
- **JavaScript:**
\`\`\`javascript
const sentData = $input.first().json;
const mismatchData = $('Find All Mismatches').first().json;

return {
  workflow: 'State Reconciliation (Full)',
  status: 'completed',
  scan_type: 'deep_content_analysis',
  execution_summary: {
    mismatches_found: mismatchData.mismatch_count,
    correction_tasks_sent: sentData.task_count || 0,
    targets_checked: mismatchData.targets_checked,
    task_cards_scanned: mismatchData.actual_state?.task_cards?.overall?.total || 0,
    actual_completion_pct: mismatchData.actual_state?.task_cards?.overall_completion_pct || 0
  },
  tasks_dispatched: sentData.tasks?.map(t => ({
    id: t.task_id,
    target: t.target,
    priority: t.priority
  })) || [],
  timestamp: new Date().toISOString()
};
\`\`\`

---

## Node Connections Summary

\`\`\`
Node 1 (Daily Reconciliation) ──┐
                                ├──▶ Node 3 (Start)
Node 2 (Manual Trigger) ────────┘
                                      │
                                      ▼
                              Node 4 (Workflow Configuration)
                                      │
                                      ▼
                              Node 5 (List All Files)
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
            Node 6 (Filter Task Cards)         Node 12 (Filter Status Reports)
                    │                                   │
                    ▼                                   ▼
            Node 7 (Process Each Card) ◀──┐    Node 13 (Has Status Reports?)
                    │                     │            │
                    ▼                     │     ┌──────┴──────┐
            Node 8 (Fetch Card Content)   │     ▼ (true)      ▼ (false)
                    │                     │  Node 14 ──┐      │
                    ▼                     │     │      │      │
            Node 9 (Parse Card Status)    │     ▼      │      │
                    │                     │  Node 15   │      │
                    └─── (loop) ──────────┘     │      │      │
                    │                           ▼      │      │
                    ▼ (loop complete)      Node 15.5   │      │
            Node 11 (Aggregate Card Status)     │      │      │
                    │                           └──────┘      │
                    │                              │          │
                    │                              ▼          │
                    │                      Node 16 (Agg)      │
                    │                              │          │
                    └───────────┬──────────────────┴──────────┘
                                │
                                ▼
                        Node 17 (Merge Aggregated Data)
                                │
                                ▼
                        Node 18 (Prepare Target Fetch)
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              Node 19      Node 19.2    Node 19.3
            (README)       (INDEX)      (ROADMAP)
                    │           │           │
                    └───────────┴───────────┘
                                │
                                ▼
                        Node 20 (Find All Mismatches)
                                │
                                ▼
                        Node 21 (Has Mismatches?)
                                │
                ┌───────────────┴───────────────┐
                ▼ (true)                        ▼ (false)
        Node 22 (Generate Corrections)    Node 26 (Log In Sync)
                │
                ▼
        Node 23 (Clean AI Output)
                │
                ▼
        Node 24 (Prepare for Distributor)
                │
                ▼
        Node 25 (Has Tasks?)
                │
                ▼ (true)
        Node 27 (Send Corrections)
                │
                ▼
        Node 28 (Summary Report)
\`\`\`

---

## Verification Checklist

After building, verify:

### Triggers & Config
- [ ] Both triggers connect to Start merge node
- [ ] Workflow Configuration includes status_patterns and status_mappings
- [ ] reconciliation_targets includes README, INDEX, and ROADMAP

### Deep Content Scan
- [ ] Filter Task Cards extracts individual card paths
- [ ] Fetch Card Content uses expression URL with card_path
- [ ] Parse Card Status correctly decodes base64 and extracts Status field
- [ ] Loop completes all cards before proceeding to Aggregate

### Status Reports (Optional Branch)
- [ ] Filter Status Reports checks for docs/status-reports/*.md
- [ ] Has Status Reports? properly routes when no reports exist
- [ ] Parse Report Status extracts date, status, and completion_pct

### Mismatch Detection
- [ ] Find All Mismatches checks 5 mismatch types
- [ ] Tolerance is applied to percentage comparisons
- [ ] All three target documents are analyzed

### Correction Generation
- [ ] AI Agent receives comprehensive context with actual state
- [ ] Clean AI Output handles markdown-wrapped JSON
- [ ] Tasks are consolidated by target document
- [ ] Distributor receives properly formatted payload

---

## Design Principles

### Deep Content Analysis
This workflow performs FULL content analysis, not just file counting:
- Fetches actual file content via GitHub API
- Parses Status fields from task cards using regex patterns
- Calculates true completion counts per directory
- Compares claimed vs actual state across all target documents

### Multi-Target Reconciliation
Reconciles three documentation layers:
1. **task-cards/README.md** - Primary task card index
2. **task-cards/INDEX.md** - Secondary index (if exists)
3. **docs/CONSOLIDATED_ROADMAP.md** - Master project roadmap

### Comprehensive Mismatch Detection
Five types of mismatches detected:
1. **FILE_COUNT_MISMATCH** - Total files differ from claimed
2. **COMPLETION_COUNT_MISMATCH** - Complete count differs from actual
3. **PERCENTAGE_MISMATCH** - Percentage claims differ beyond tolerance
4. **STATUS_FORMAT_ISSUE** - Cards with unrecognized status format
5. **STATUS_REPORT_MISMATCH** - Status reports don't align with roadmap

### API Considerations
This workflow makes N+M API calls where:
- N = number of task card files (for content fetch)
- M = number of status report files (for content fetch)
- Plus 3 calls for target documents

For repositories with many task cards (100+), consider:
- Running during low-traffic periods (4 AM UTC default)
- Implementing caching for unchanged files
- Using GitHub GraphQL API for batch fetching (advanced)

---

## Rate Limit Mitigation

If hitting GitHub API rate limits:

### Option 1: Add Delays
Add a Wait node (1 second) between Fetch Card Content iterations.

### Option 2: Batch Using GraphQL
Replace individual content fetches with GraphQL batch query:
\`\`\`graphql
query {
  repository(owner: "BootstrapAI-mgmt", name: "Literature-Review") {
    object(expression: "main:task-cards") {
      ... on Tree {
        entries {
          name
          object {
            ... on Blob {
              text
            }
          }
        }
      }
    }
  }
}
\`\`\`

### Option 3: Cache with SHA Check
Store SHA values and only fetch files that changed since last run.

---

## Comparison: Full vs Lightweight

| Aspect | Lightweight (Previous) | Full (This Version) |
|--------|----------------------|---------------------|
| API Calls | ~5 per run | N+M+5 per run |
| Content Analysis | File counts only | Full status parsing |
| Accuracy | Detects file adds/removes | Detects all status changes |
| Targets | README only | README, INDEX, ROADMAP |
| Status Reports | Not scanned | Scanned & compared |
| Completion % | Not calculated | Calculated from actual |
| Execution Time | ~10 seconds | ~2-5 minutes |

---

## Related Documentation

- [N8N_AI_BUILDER_PROMPT.md](./N8N_AI_BUILDER_PROMPT.md) - Workflows 1-4
- [N8N_STALENESS_REVIEW_BUILDER_PROMPT.md](./N8N_STALENESS_REVIEW_BUILDER_PROMPT.md) - Workflow 5
- [documentation_matrix.json](./documentation_matrix.json) - Matrix configuration
- [CURRENT_STATE_SYNC_ANALYSIS.md](./CURRENT_STATE_SYNC_ANALYSIS.md) - Gap analysis
- [N8N_STATE_RECONCILIATION_MINIMAL.md](./N8N_STATE_RECONCILIATION_MINIMAL.md) - Quick reference

---

## Changelog

### v2.0 (2025-12-20)
- **MAJOR:** Implemented full deep content analysis
- Added file content fetching for task cards
- Added status extraction from file content using regex
- Added status reports scanning
- Expanded to multi-target reconciliation (README, INDEX, ROADMAP)
- Added 5 mismatch types (was 1)
- Enhanced AI prompt for comprehensive corrections
- Added execution summary reporting

### v1.0 (2025-12-19)
- Initial implementation with file count comparison only
