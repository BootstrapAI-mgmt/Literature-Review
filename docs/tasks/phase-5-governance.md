# Phase 5: Governance Bootstrap — Task Cards

## TC-LR15: Create ARCHITECTURE.md Following Command-Center Schema

**Priority:** P0
**Status:** in-progress
**Dependencies:** None

**Problem:**
The repo has extensive internal documentation (67 files in `docs/`) but no standardized `ARCHITECTURE.md` following the command-center schema. Without it, the repo stays at L0 compliance and `ccv scan` reports missing documentation. The architecture is mature (~26K LOC, 12 subpackages, 4 LLM providers, FastAPI dashboard) and deserves a proper blueprint.

**Deliverables:**
- `ARCHITECTURE.md` with all 6 required sections: What This Is, Design Principles, System Overview, Project Structure, Key Interfaces, Dependencies
- Content derived from actual codebase, not placeholder text

**Files to create/modify:**
- `ARCHITECTURE.md` (new file at repo root)

**Acceptance Criteria:**
1. All 6 section headings present
2. No `[FUTURE]`, `[PLANNED]`, `[TODO]` tags
3. No future-tense verbs in "What This Is" section
4. All paths listed in Project Structure exist in the repo
5. Design Principles contains 3+ numbered items with rationale

---

## TC-LR16: Create ROADMAP.md with Verifiable Milestones

**Priority:** P0
**Status:** in-progress
**Dependencies:** None

**Problem:**
The existing `docs/CONSOLIDATED_ROADMAP.md` uses a wave-based structure with emoji status markers that does not conform to the command-center roadmap schema. A compliant `ROADMAP.md` is needed at repo root with proper phase structure, tangible milestones, verification steps, and evidence references.

**Deliverables:**
- `ROADMAP.md` at repo root with Strategic Direction, Phases (with Goal/Milestone/Verification/Status/Evidence), Phase Gate Criteria, and Known Risks
- Milestones reference tangible artifacts; verification has 2+ numbered steps

**Files to create/modify:**
- `ROADMAP.md` (new file at repo root)

**Acceptance Criteria:**
1. All active phases have Goal, Milestone, Verification, Status, Completed, Evidence fields
2. Milestones contain no vague verbs (improve, optimize, enhance, etc.)
3. Verification sections have 2+ numbered steps
4. Complete phases have non-placeholder Evidence (PR numbers or commit SHAs)
5. Phase Gate Criteria and Known Risks tables present

---

## TC-LR17: Create TODO-MASTER.md with Phase-Based Task Tracker

**Priority:** P0
**Status:** in-progress
**Dependencies:** None

**Problem:**
There is no centralized task tracker that maps to the roadmap phases and links to task card specifications. The existing `docs/CONSOLIDATED_ROADMAP.md` mixes roadmap and task tracking concerns. A proper `TODO-MASTER.md` provides the bridge between high-level phases and detailed task cards.

**Deliverables:**
- `TODO-MASTER.md` at repo root with How to Read This, Summary table, and Phase sections
- Every checkbox item has a TC-ID, completed items have PR/commit references

**Files to create/modify:**
- `TODO-MASTER.md` (new file at repo root)

**Acceptance Criteria:**
1. Every checkbox has `[TC-LRXX]` ID
2. TC-IDs are unique across the file
3. `[x]` items include `*(PR #N)*` or `*(commit ...)*` references
4. Summary table counts match actual checkbox counts per phase
5. "How to Read This" section present

---

## TC-LR18: Create Task Card Files Under docs/tasks/

**Priority:** P1
**Status:** in-progress
**Dependencies:** TC-LR17

**Problem:**
The repo has 50+ task card files in `task-cards/` using a legacy format that predates the command-center task card schema. Open work items need new task cards in `docs/tasks/` following the CC schema with required fields (TC-ID, Priority, Status, Dependencies, Problem, Deliverables, Files, Acceptance Criteria).

**Deliverables:**
- Task card files in `docs/tasks/` grouped by phase
- Cards for all open TC-IDs referenced in TODO-MASTER.md

**Files to create/modify:**
- `docs/tasks/phase-4-golden-dataset.md` (new)
- `docs/tasks/phase-5-governance.md` (new)

**Acceptance Criteria:**
1. Every open TC-ID in TODO-MASTER.md has a corresponding task card heading in `docs/tasks/`
2. Each card has Priority, Status, Dependencies, Problem, Deliverables, Files to create/modify, and Acceptance Criteria fields
3. TC-IDs match the pattern `TC-[A-Z]{1,4}[0-9]{2,}`
4. Acceptance criteria are objectively testable

---

## TC-LR19: Create CLAUDE.md Agent Context File

**Priority:** P1
**Status:** in-progress
**Dependencies:** None

**Problem:**
There is no `CLAUDE.md` at the repo root, which means Claude Code sessions in this repo start without project-specific context. A `CLAUDE.md` file provides the agent with project structure, key commands, conventions, and data file locations so it can assist effectively from the first interaction.

**Deliverables:**
- `CLAUDE.md` at repo root with project overview, commands, structure, conventions

**Files to create/modify:**
- `CLAUDE.md` (new file at repo root)

**Acceptance Criteria:**
1. File exists at repo root
2. Contains accurate project structure matching actual directory layout
3. Contains working command examples for pipeline, tests, and dashboard
4. References governance tracking by command-center
