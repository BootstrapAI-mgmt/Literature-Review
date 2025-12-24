# Claude Desktop Checkpoint System

> **Purpose**: Ensure work progress is saved incrementally, not just at task completion.

## Core Principle

**CHECKPOINT EARLY, CHECKPOINT OFTEN**

Every significant unit of work should be persisted before moving to the next. Never accumulate more than 5-10 minutes of unsaved work.

---

## Checkpoint Triggers

Claude agents should create checkpoints when:

1. **After ANY file creation** → Commit immediately
2. **After completing a subtask** → Update progress file + commit
3. **Before starting a new phase** → Save current state
4. **Every 3-5 tool calls** → Update progress journal
5. **When context feels "full"** → Emergency checkpoint
6. **Before complex operations** → Pre-operation snapshot

---

## Checkpoint Methods

### Method 1: Micro-Commits (PRIMARY)
```bash
# After each file or small group of related files
git add <specific-files>
git commit -m "checkpoint: <brief description>"
```

Commit message prefixes:
- `checkpoint:` - Work in progress, not complete
- `wip:` - Work in progress, may not build/work
- `progress:` - Incremental progress on larger task
- `save:` - Explicit save point

### Method 2: Progress Journal (REQUIRED)
Maintain `/docs/claude-integration/PROGRESS.md` with real-time updates:

```markdown
## Current Session: [DATE TIME]
### Task: [Description]
### Status: IN_PROGRESS | BLOCKED | COMPLETE

### Completed Steps:
- [x] Step 1 description (commit: abc123)
- [x] Step 2 description (commit: def456)
- [ ] Step 3 description (IN PROGRESS)

### Current State:
- Working on: [specific item]
- Files modified: [list]
- Next action: [what comes next]

### Blockers/Notes:
- [Any issues encountered]
```

### Method 3: State Snapshots
For complex multi-step operations, create state files:
```
/docs/claude-integration/state/
  session-2024-12-24-1200.json
  session-2024-12-24-1430.json
```

---

## Implementation Rules for Agents

### Rule 1: Never Batch More Than 3 Files
```
❌ BAD: Create 10 files, then commit all at once
✅ GOOD: Create 2-3 files, commit, repeat
```

### Rule 2: Update Progress Before Each Major Step
```
❌ BAD: Complete entire task, then document
✅ GOOD: Document intent → Do work → Document completion → Commit
```

### Rule 3: Commit Before Context-Heavy Operations
```
Before: Large file reads, complex analysis, multiple API calls
Action: Commit current work first
Reason: If operation fails or fills context, work is saved
```

### Rule 4: Use Explicit Save Points
When user says "continue" or similar, first action should be:
1. Read PROGRESS.md to understand state
2. Verify last checkpoint
3. Resume from known state

---

## Emergency Recovery

If context is compacted or work seems lost:

1. **Check Git Log**:
   ```bash
   git log --oneline -20
   ```

2. **Check Progress Journal**:
   ```bash
   cat docs/claude-integration/PROGRESS.md
   ```

3. **Check Transcript**:
   ```bash
   cat /mnt/transcripts/[latest].txt
   ```

4. **Check State Files**:
   ```bash
   ls -la docs/claude-integration/state/
   ```

---

## Checkpoint Frequency Guide

| Task Type | Checkpoint Frequency |
|-----------|---------------------|
| File creation | After each file |
| Code changes | Every 20-30 lines |
| Documentation | Every major section |
| Research/Analysis | Every finding |
| Multi-step workflows | After each step |
| API interactions | Before and after |

---

## Sample Workflow

```
1. START TASK
   └─> Update PROGRESS.md: "Starting task X"
   └─> git commit -m "checkpoint: starting task X"

2. SUBTASK A
   └─> Do work
   └─> Create/modify files
   └─> git commit -m "checkpoint: completed subtask A"
   └─> Update PROGRESS.md

3. SUBTASK B
   └─> Do work
   └─> git commit -m "checkpoint: completed subtask B"
   └─> Update PROGRESS.md

4. COMPLETE
   └─> Final review
   └─> git commit -m "feat: complete task X"
   └─> Update PROGRESS.md: "COMPLETE"
```

---

## Integration with Memory System

For critical state that should persist across ALL sessions:
```
Use memory_user_edits tool to store:
- Current project phase
- Major milestones completed
- Key decisions made
- Blocking issues
```

This survives context compaction AND conversation boundaries.
