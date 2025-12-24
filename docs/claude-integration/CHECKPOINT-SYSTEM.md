# Claude Desktop Checkpoint System

> **Purpose**: Ensure work progress is saved incrementally, not just at task completion.  
> **Last Updated**: 2024-12-24 (v2 - refined triggers based on retrospective)

## Core Principle

**CHECKPOINT EARLY, CHECKPOINT OFTEN**

Never accumulate more than 5 minutes of unsaved work. The cost of an extra commit is ~10 seconds. The cost of lost work is 10-30 minutes of redo.

---

## Mandatory Checkpoint Triggers (Priority Order)

### 🔴 IMMEDIATE COMMIT REQUIRED

| Trigger | Action | Why |
|---------|--------|-----|
| Created new file (any size) | `git commit` NOW | Files are discrete deliverables |
| Rewrote/replaced existing file | `git commit` NOW | Major changes = major risk |
| File >50 lines created/modified | `git commit` NOW | Significant work investment |

### 🟡 BATCH COMMIT (within 2-3 actions)

| Trigger | Action | Why |
|---------|--------|-----|
| 3+ edits to same file | Commit the batch | Logical unit complete |
| Related edits across 2-3 files | Commit together | Coherent change set |
| Completing logical subtask | Commit + update PROGRESS.md | Milestone reached |

### 🟢 TIME-BASED CHECKS

| Trigger | Action | Why |
|---------|--------|-----|
| ~5 min since last commit | Check for uncommitted work | Prevent drift |
| Before starting new major task | Commit current work first | Clean slate |
| Before context-heavy operation | Commit first | Protect against context loss |

---

## Anti-Patterns (What NOT To Do)

```
❌ Create 180-line file → edit 4 other files → then commit
❌ "I'll commit when I'm done with this whole task"
❌ Multiple major deliverables in single commit
❌ Waiting for user prompt to save work

✅ Create file → COMMIT → edit related files → COMMIT
✅ Each major file gets its own checkpoint
✅ Commit before moving to unrelated work
```

---

## Checkpoint Decision Tree

```
Did I just create a new file?
  YES → COMMIT NOW
  NO  ↓

Did I just rewrite/replace a file >50 lines?
  YES → COMMIT NOW
  NO  ↓

Have I made 3+ edits since last commit?
  YES → COMMIT NOW
  NO  ↓

Has it been ~5 minutes since last commit?
  YES → Check for uncommitted work, commit if any
  NO  → Continue working
```

---

## Commit Message Prefixes

| Prefix | Meaning | Example |
|--------|---------|---------|
| `checkpoint:` | Work in progress save | `checkpoint: add TESTING-GUIDE.md` |
| `wip:` | Incomplete, may not work | `wip: distributor refactor partial` |
| `progress:` | Incremental milestone | `progress: 3/6 reviews complete` |
| `save:` | Explicit save point | `save: before complex refactor` |

---

## Progress Journal Protocol

Maintain `/docs/claude-integration/PROGRESS.md`:

### Update BEFORE starting work:
```markdown
### Active Task
[What I'm about to do]

### Next Actions
1. [ ] First thing I'll do
```

### Update AFTER each checkpoint:
```markdown
### Completed This Session
| # | Task | Commit | Time |
|---|------|--------|------|
| N | What I did | abc123 | NOW |
```

---

## Recovery Protocol

On context loss or "continue" request:

1. `view PROGRESS.md` - Understand current state
2. `git log --oneline -10` - See recent commits
3. Check `/mnt/transcripts/[latest].txt` if needed
4. Resume from documented "Next Actions"
5. **Update PROGRESS.md before resuming work**

---

## Real Example: What Should Have Happened

**Scenario**: Update Distributor review + create testing guide

```
CORRECT SEQUENCE:
1. Rewrite DISTRIBUTOR-REVIEW.md (180 lines)
   → git commit -m "checkpoint: update DISTRIBUTOR-REVIEW.md - cleanup verified"
   
2. Edit MASTER-REVIEW.md (4 small edits)
   → git commit -m "checkpoint: update MASTER-REVIEW.md status"
   
3. Create TESTING-GUIDE.md (200 lines)
   → git commit -m "checkpoint: add TESTING-GUIDE.md"
   
4. Update PROGRESS.md
   → git commit -m "checkpoint: update progress journal"

RESULT: 4 commits, max ~8 min work at risk between any two

WRONG (what actually happened):
1. Rewrite DISTRIBUTOR-REVIEW.md
2. Edit MASTER-REVIEW.md x4
3. git commit (finally!) ← 10+ min of work at risk
4. Create TESTING-GUIDE.md
5. Edit PROGRESS.md x5
6. git commit ← another 10+ min at risk

RESULT: 2 commits, up to 15 min work at risk
```

---

## Memory Integration

Store in `memory_user_edits` for cross-conversation persistence:
- Checkpoint protocol reminder (always active)
- Current project phase and status
- Key blockers or decisions

Memory survives: context compaction, conversation end, Claude restart
