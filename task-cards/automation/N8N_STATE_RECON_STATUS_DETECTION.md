# Task Card: Fix State Reconciliation Status Detection

**Task ID:** N8N-RECON-001  
**Priority:** 🔴 HIGH  
**Estimated Effort:** 4-6 hours  
**Status:** ✅ COMPLETE → 🔄 SUPERSEDED  
**Created:** 2025-12-19  
**Completed:** 2025-12-19  
**Superseded:** 2025-12-20  
**Source:** Gap Analysis - Gap 2  
**PR:** #92

> ⚠️ **SUPERSEDED:** This task implemented Option B (file count comparison only). On 2025-12-20, the workflow was upgraded to implement **Option A (full content parsing)** as the primary approach. See [N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md](../../docs/N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md) v2.0 for the full deep reconciliation implementation.

---

## Problem Statement

The State Reconciliation workflow (Workflow 6) currently determines task card completion status by checking **filenames** for keywords like "COMPLETE" or "DONE". However, task cards store their status **inside the file content** using a `**Status:** Complete` field.

### Current Behavior (Wrong)

```javascript
// In "Extract Status from Cards" node
const filenameUpper = name.toUpperCase();
const isComplete = config.status_complete_keywords.some(kw => 
  filenameUpper.includes(kw.toUpperCase())
);
```

This reports nearly all task cards as "Unknown" status because filenames don't contain completion keywords.

### Actual Task Card Format

```markdown
## Status
**Status:** Complete
**Completion Date:** 2025-12-15
```

### Impact

- State Reconciliation reports 0 complete cards when many are complete
- AI generates incorrect correction tasks
- README.md gets updated with wrong completion counts
- Creates noise and wasted API calls

---

## Proposed Solutions

### Option A: Parse File Contents (Accurate but Expensive)

Fetch actual file contents and parse status from each task card.

**Pros:**
- Most accurate - reads actual status
- Handles all status formats

**Cons:**
- Requires N API calls per run (one per task card file)
- May hit GitHub API rate limits
- Slower execution

**Implementation:**
1. Add HTTP Request node to fetch each file via GitHub Contents API
2. Parse `**Status:**` field from markdown
3. Handle base64 decoding

### Option B: Use README.md as Source of Truth (Recommended)

Instead of determining "actual" completion from files, compare:
- **Total file count per directory** (from Git tree - already available)
- **Claimed counts in README.md** (already fetched)

Only flag mismatches when:
1. Total count differs (files added/removed)
2. Leave completion tracking to the README maintainers

**Pros:**
- No additional API calls
- Faster execution
- README is the intended source of truth anyway

**Cons:**
- Won't catch cases where status changed in file but README wasn't updated
- Relies on other workflows (Trigger, Agent) to maintain README accuracy

**Implementation:**
1. Modify `Extract Status from Cards` to only count files, not infer status
2. Modify `Find Mismatches` to compare totals, not completion counts
3. Change mismatch descriptions to focus on file count discrepancies

### Option C: Hybrid Approach

Use README as source of truth for counts, but add optional deep scan:
- Normal runs: Compare file counts only (fast)
- Weekly deep scan: Fetch file contents and validate completion status

---

## Recommended Implementation (Option B)

### Node Changes

#### 1. Update `Extract Status from Cards` (Node 9)

```javascript
// Get data from the current batch item
const batchItem = $input.first().json;
const dir = batchItem.directory;
const config = batchItem.config;
const cards = batchItem.cards || [];

// Just count files - don't try to determine completion
const results = cards.map(card => ({
  path: card.path,
  name: card.path.split('/').pop()
}));

return {
  directory: dir,
  config: config,
  cards: results,
  summary: { 
    file_count: results.length 
  }
};
```

#### 2. Update `Aggregate All Directories` (Node 11)

```javascript
const loopResults = $input.all().map(item => item.json);
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

#### 3. Update `Find Mismatches` (Node 13)

```javascript
const actual = $('Aggregate All Directories').first().json;
const indexFile = $input.first().json;

let indexContent = '';
if (indexFile.content) {
  try {
    indexContent = Buffer.from(indexFile.content, 'base64').toString('utf8');
  } catch (e) { indexContent = ''; }
}

// Extract claimed totals from README: "X/Y Complete" → Y is total
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
      description: `${dirName}: README claims X/${claimed.claimed_total} but directory has ${actualSummary.file_count} files`
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

#### 4. Update AI Prompt in `Generate Corrections`

Update the system prompt to focus on file count corrections rather than completion status.

---

## Acceptance Criteria

- [ ] State Reconciliation correctly counts files per directory
- [ ] Mismatches are only flagged when file counts don't match README claims
- [ ] No false positives from "Unknown" status detection
- [ ] AI generates appropriate correction tasks for actual discrepancies
- [ ] README updates reflect accurate file counts

---

## Testing

1. Add/remove a task card file and trigger reconciliation
2. Verify mismatch is detected for file count change
3. Verify no false mismatches when file count matches
4. Verify AI generates correct update task

---

## Related Files

- `docs/N8N_STATE_RECONCILIATION_BUILDER_PROMPT.md` - Workflow specification
- `task-cards/README.md` - Target document for corrections
- `docs/N8N_ARCHITECTURE_GAP_ANALYSIS.md` - Source gap analysis

---

## Notes

This issue was identified in the third-party architecture gap analysis (December 2025). The current implementation was a simplification that assumed filename-based status detection would work, but task cards use internal status fields instead.
