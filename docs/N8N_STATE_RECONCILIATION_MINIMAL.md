# State Reconciliation - n8n Builder Prompt (Minimal Reference)

**Workflow 6:** Deep content analysis to verify and reconcile documentation state. 28 nodes total.

> **VERSION:** 2.0 - Full Deep Reconciliation

## Node List (Build Exactly)

| # | Type | Name | Purpose |
|---|------|------|---------|
| 1 | Schedule Trigger | Daily Reconciliation | 4 AM UTC |
| 2 | Webhook | Manual Trigger | POST /state-reconciliation |
| 3 | Merge | Start | Append mode, Include Unpaired ✅ |
| 4 | Code | Workflow Configuration | Status patterns & mappings |
| 5 | HTTP Request | List All Files | Git tree recursive |
| 6 | Code | Filter Task Cards | Extract card paths |
| 7 | Split In Batches | Process Each Card | Batch Size: 1 |
| 8 | HTTP Request | Fetch Card Content | GET contents/{path} |
| 9 | Code | Parse Card Status | Extract Status field |
| 10 | (Loop) | → back to Node 7 | Loop connector |
| 11 | Code | Aggregate Card Status | Group by directory |
| 12 | Code | Filter Status Reports | Extract report paths |
| 13 | If | Has Status Reports? | Route or skip |
| 14 | Split In Batches | Process Each Report | Batch Size: 1 |
| 15 | HTTP Request | Fetch Report Content | GET contents/{path} |
| 15.5 | Code | Parse Report Status | Extract date, status |
| 16 | Code | Aggregate Report Status | Combine reports |
| 17 | Merge | Merge Aggregated Data | Combine branches |
| 18 | Code | Prepare Target Fetch | Combine data |
| 19 | HTTP Request | Fetch Target README | task-cards/README.md |
| 19.2 | HTTP Request | Fetch Target INDEX | task-cards/INDEX.md |
| 19.3 | HTTP Request | Fetch Target Roadmap | docs/CONSOLIDATED_ROADMAP.md |
| 20 | Code | Find All Mismatches | 5 mismatch types |
| 21 | If | Has Mismatches? | Route true/false |
| 22 | AI Agent | Generate Corrections | Gemini 2.5 Flash |
| 23 | Code | Clean AI Output | Strip markdown |
| 24 | Code | Prepare for Distributor | Format payload |
| 25 | If | Has Tasks? | Check skip flag |
| 26 | Code | Log In Sync | False branch output |
| 27 | HTTP Request | Send Corrections | POST to Distributor |
| 28 | Code | Summary Report | Execution summary |

## Key Connections

```
1,2 → 3 → 4 → 5 ─┬─→ 6 → 7 ⟲ 8 → 9 (loop) → 11 ─┐
                 │                                │
                 └─→ 12 → 13 ─┬─→ 14 ⟲ 15 → 15.5 → 16 ─┤
                              │                        │
                              └─→ (skip) ──────────────┤
                                                       │
                         ┌─────────────────────────────┘
                         ▼
                   17 → 18 → [19, 19.2, 19.3] → 20 → 21
                                                      │
                              ┌────────────┬──────────┘
                              ▼ (true)     ▼ (false)
                        22 → 23 → 24 → 25   26
                                      │
                                      ▼ (true)
                                  27 → 28
```

## Node 4: Workflow Configuration
```javascript
return {
  reconciliation_targets: [
    { path: 'task-cards/README.md', type: 'index', aggregation: 'count_by_status' },
    { path: 'task-cards/INDEX.md', type: 'index', aggregation: 'count_by_status' },
    { path: 'docs/CONSOLIDATED_ROADMAP.md', type: 'roadmap', aggregation: 'summarize_progress' }
  ],
  status_patterns: {
    task_status: /^\*?\*?Status:?\*?\*?\s*(.+)$/im,
    completion_pct: /(\d+)%\s*(?:complete|done|finished)/i,
    fraction: /(\d+)\/(\d+)\s*Complete/i
  },
  status_mappings: {
    'complete': 'Complete', 'done': 'Complete', '✅ complete': 'Complete',
    'in progress': 'In Progress', '🔄 in progress': 'In Progress',
    'not started': 'Not Started', 'ready': 'Not Started', '🟢 ready': 'Not Started',
    'blocked': 'Blocked', 'deferred': 'Deferred'
  },
  mismatch_tolerance_pct: 5
};
```

## Node 9: Parse Card Status (Key Logic)
```javascript
// Decode base64 content from GitHub API
const content = Buffer.from(fileData.content, 'base64').toString('utf8');

// Extract status field
const statusMatch = content.match(/^\*?\*?Status:?\*?\*?\s*(.+)$/im);
let extractedStatus = 'Unknown';

if (statusMatch) {
  const rawStatus = statusMatch[1].trim().toLowerCase();
  // Normalize using status_mappings
  for (const [key, value] of Object.entries(config.status_mappings)) {
    if (rawStatus.includes(key)) {
      extractedStatus = value;
      break;
    }
  }
}

return { status: extractedStatus, is_complete: extractedStatus === 'Complete' };
```

## Node 20: Find All Mismatches (5 Types)
```javascript
// 1. FILE_COUNT_MISMATCH - README total differs from actual file count
// 2. COMPLETION_COUNT_MISMATCH - README "X/Y Complete" differs from parsed status
// 3. PERCENTAGE_MISMATCH - Claimed % differs from actual beyond tolerance
// 4. STATUS_FORMAT_ISSUE - >20% cards have Unknown status
// 5. STATUS_REPORT_MISMATCH - Status reports don't match roadmap
```

## Node 22: AI Agent System Prompt
```
You generate CONSOLIDATED correction tasks to fix documentation mismatches.

TASK CONSOLIDATION RULES:
1. Group all updates for SAME FILE into ONE task
2. For task-cards/README.md: ONE task with ALL directory updates
3. For CONSOLIDATED_ROADMAP.md: ONE task with ALL percentage updates

Output ONLY raw JSON (no markdown code blocks):
{"update_list_id":"ul-recon-TIMESTAMP","source":"state-reconciliation-full","tasks":[...]}
```

## URLs & Headers

| Node | URL |
|------|-----|
| List All Files | `api.github.com/.../git/trees/main?recursive=1` |
| Fetch Card Content | `api.github.com/.../contents/{{ $json.card_path }}` |
| Fetch Target README | `api.github.com/.../contents/task-cards/README.md` |
| Fetch Target Roadmap | `api.github.com/.../contents/docs/CONSOLIDATED_ROADMAP.md` |
| Send Corrections | `gitlitreview.app.n8n.cloud/webhook/task-distributor` |

**All GitHub requests need:**
- Authorization: `Bearer YOUR_PAT`
- Accept: `application/vnd.github.v3+json`

## Comparison: Full vs Lightweight

| Aspect | Lightweight (v1) | Full (v2) |
|--------|-----------------|-----------|
| API Calls | ~5 | N+M+5 |
| Analysis | File counts only | Full content parsing |
| Targets | README only | README, INDEX, ROADMAP |
| Status Reports | ❌ | ✅ Scanned |
| Mismatch Types | 1 | 5 |
| Completion % | Not calculated | Calculated from actual |

## Changelog

### v2.0 (2025-12-20)
- Full deep content analysis
- Multi-target reconciliation
- Status extraction from file content
- 5 mismatch detection types
- Status reports integration

### v1.0 (2025-12-19)
- File count comparison only
