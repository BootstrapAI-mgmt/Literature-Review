# Doc Chain Workflow Review Master Document

**Generated:** 2025-12-24
**Review Version:** 1.0
**Status:** 🔄 In Progress

---

## Executive Summary

This document provides a comprehensive step-through review system for validating the Doc Chain n8n workflow suite. It includes node-by-node architecture validation, input/output schema verification, and a checkout/sign-off tracking system for parallel agent review.

### Workflow Inventory

| ID | Workflow Name | Nodes | Status | Reviewer | Sign-off |
|----|--------------|-------|--------|----------|----------|
| 1 | Doc Chain - Trigger | 11 | ✅ Active | ⬜ | ⬜ |
| 2 | Doc Chain - Distributor | 24 | ✅ Active | ⬜ | ⬜ |
| 3 | Doc Chain - Agent | 14 | ✅ Active | ⬜ | ⬜ |
| 4 | Doc Chain - State Reconciliation | 35 | ✅ Active | ⬜ | ⬜ |
| 5 | Doc Chain - Staleness | 32 | ✅ Active | ⬜ | ⬜ |
| 6 | Doc Chain - Errors | 5 | ✅ Active | ⬜ | ⬜ |
| 7 | Doc Chain - PR Review | 14 | ✅ Active | ⬜ | ⬜ |
| 8 | Doc Chain - Release | 10 | ✅ Active | ⬜ | ⬜ |

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DOC CHAIN SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐     │
│  │   TRIGGERS   │────▶│   DISTRIBUTOR    │────▶│      AGENT       │     │
│  │              │     │                  │     │                  │     │
│  │ • GitHub WH  │     │ • Queue tasks    │     │ • Fetch doc      │     │
│  │ • Scheduler  │     │ • Dedup logic    │     │ • AI update      │     │
│  │ • Manual WH  │     │ • Dispatch       │     │ • Commit GitHub  │     │
│  └──────────────┘     └──────────────────┘     └──────────────────┘     │
│         │                      ▲                        │               │
│         │                      │ callback               │               │
│         │                      └────────────────────────┘               │
│         │                                                               │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐     │
│  │  STALENESS   │────▶│   DISTRIBUTOR    │     │     ERRORS       │     │
│  │              │     │   (shared)       │     │                  │     │
│  │ • Weekly     │     │                  │     │ • Catch errors   │     │
│  │ • AI assess  │     │                  │     │ • Send callback  │     │
│  └──────────────┘     └──────────────────┘     └──────────────────┘     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    STATE RECONCILIATION                          │   │
│  │  • Daily 3AM scheduled • Scans task cards • Fixes mismatches    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Contracts

### Webhook Endpoints

| Endpoint | Method | Workflow | Purpose |
|----------|--------|----------|---------|
| `/github-doc-trigger` | POST | Trigger | GitHub push events |
| `/task-distributor` | POST | Distributor | Receive task lists |
| `/task-callback` | POST | Distributor | Agent completion callbacks |
| `/distributor-reset` | POST | Distributor | Clear all state |
| `/distributor-status` | GET | Distributor | Status check |
| `/domain-agent` | POST | Agent | Execute document updates |
| `/state-reconciliation` | POST | State Recon | Manual trigger |
| `/staleness-review` | POST | Staleness | Manual trigger |

### Task Schema

```json
{
  "update_list_id": "ul-trigger-{timestamp}",
  "source": "github-trigger|state-reconciliation|staleness-review",
  "trigger": {
    "type": "push|scheduled|manual",
    "message": "commit message",
    "author": "username"
  },
  "tasks": [
    {
      "task_id": "task-{n}",
      "update_type": "UPDATE_REFERENCE|UPDATE_INDEX|CASCADE_UPDATE|...",
      "document": "path/to/file.md",
      "description": "what to update",
      "depends_on": [],
      "priority": 1
    }
  ]
}
```

---

## Checkout System

To prevent conflicts during parallel review, use this checkout system:

### How to Checkout
1. Edit this file
2. Add your name/agent-id to the "Reviewer" column
3. Change status icon to 🔒
4. Commit with message: `[review] checkout: {workflow-name}`

### How to Sign-off
1. Complete all checklist items in the workflow review doc
2. Change "Sign-off" to ✅
3. Add completion timestamp
4. Commit with message: `[review] signoff: {workflow-name}`

---

## Critical Findings (Pre-Review)

### ⚠️ Distributor Dual Architecture
The Distributor workflow contains **BOTH old and new architectures**:
- **OLD (nodes 2-12, 14, 22):** Queue-based with Wait node
- **NEW (nodes 1, 15-21, 23-24):** Direct dispatch with deduplication

**Action Required:** Validate which architecture is actually connected and active.

### ⚠️ Callback URL Mismatch Potential
- Agent sends to: `https://gitlitreview.app.n8n.cloud/webhook/task-callback`
- Errors sends to: `https://gitlitreview.app.n8n.cloud/webhook/task-done-{task_id}`

**Action Required:** Verify Distributor accepts both callback patterns.

---

## Review Documents

- [REVIEW_01_TRIGGER.md](./REVIEW_01_TRIGGER.md)
- [REVIEW_02_DISTRIBUTOR.md](./REVIEW_02_DISTRIBUTOR.md)
- [REVIEW_03_AGENT.md](./REVIEW_03_AGENT.md)
- [REVIEW_04_STATE_RECONCILIATION.md](./REVIEW_04_STATE_RECONCILIATION.md)
- [REVIEW_05_STALENESS.md](./REVIEW_05_STALENESS.md)
- [REVIEW_06_ERRORS.md](./REVIEW_06_ERRORS.md)
- [REVIEW_07_PR_REVIEW.md](./REVIEW_07_PR_REVIEW.md)
- [REVIEW_08_RELEASE.md](./REVIEW_08_RELEASE.md)

---

## Sign-off Summary

| Phase | Status | Date | Reviewer |
|-------|--------|------|----------|
| Individual Workflow Reviews | ⬜ Pending | - | - |
| Integration Flow Validation | ⬜ Pending | - | - |
| End-to-End Test Execution | ⬜ Pending | - | - |
| Production Readiness | ⬜ Pending | - | - |
