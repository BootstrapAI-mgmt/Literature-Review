# Doc Chain - Staleness Workflow Review

> **Workflow ID:** WRzBAw1oMYLbnu7d  
> **Status:** ✅ Active  
> **Version:** STALE-V001  
> **Last Updated:** 2025-12-23T17:17:16.841Z

---

## Checkout Information

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |
| **Sign-off By** | - |
| **Sign-off Time** | - |

---

## Workflow Purpose

Runs weekly (or via manual webhook), reviews documentation domains for staleness by comparing doc content against recent code changes, assigns staleness scores (0-1), generates update tasks or GitHub issues based on severity, and creates weekly digest reports.

---

## Trigger Configuration

| Trigger | Schedule | Notes |
|---------|----------|-------|
| Weekly Review | Every week at 2:00 AM | `weeks` interval |
| Manual Trigger | POST `/webhook/staleness-review` | On-demand |

---

## Node-by-Node Validation (28 Nodes)

### INITIALIZATION (Nodes 1-5)

#### Node 1: Weekly Review
| Check | Status | Notes |
|-------|--------|-------|
| Schedule: Weekly 2 AM | [ ] | `field: "weeks", triggerAtHour: 2` |

#### Node 2: Manual Trigger
| Check | Status | Notes |
|-------|--------|-------|
| Path correct | [ ] | `/staleness-review` |

#### Node 3: Start Review (Merge)
| Check | Status | Notes |
|-------|--------|-------|
| Combines triggers | [ ] | |

#### Node 4: Workflow Configuration
| Check | Status | Notes |
|-------|--------|-------|
| Matrix URL set | [ ] | raw.githubusercontent.com |
| GitHub repo set | [ ] | BootstrapAI-mgmt/Literature-Review |
| Branch set | [ ] | main |
| **⚠️ Placeholder value** | [ ] | `distributorWebhook` has placeholder |

**Note:** `distributorWebhook` contains `<__PLACEHOLDER_VALUE__...>` but this value is NOT used - URL is hardcoded in Send to Distributor node.

#### Node 5: Fetch Matrix
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | |
| Response format: JSON | [ ] | |

---

### DOMAIN EXTRACTION (Nodes 6-8)

#### Node 6: Get Domains
| Check | Status | Notes |
|-------|--------|-------|
| Parses owner_domains | [ ] | From matrix |
| Handles old/new format | [ ] | Array vs object |
| Applies stagger logic | [ ] | If configured |
| Extracts staleness_indicators | [ ] | |

#### Node 7: Process Each Domain
| Check | Status | Notes |
|-------|--------|-------|
| Maps domains for iteration | [ ] | |

---

### ACTIVITY CHECK (Nodes 8-11)

#### Node 8: Get Last Activity
| Check | Status | Notes |
|-------|--------|-------|
| GitHub Commits API | [ ] | |
| Filters by path | [ ] | First document in domain |
| Uses HTTP Header Auth | [ ] | Credential: Ho5S7HOxBPdmEAL0 |

#### Node 9: Calculate Inactivity
| Check | Status | Notes |
|-------|--------|-------|
| Calculates days since last commit | [ ] | |
| Compares to review_interval_days | [ ] | |
| Sets needs_review flag | [ ] | |

#### Node 10: Needs Review? (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `needs_review === true` |
| True → Fetch Recent Changes | [ ] | |
| False → Log Healthy | [ ] | |

---

### CHANGE ANALYSIS (Nodes 11-15)

#### Node 11: Fetch Recent Changes
| Check | Status | Notes |
|-------|--------|-------|
| GitHub Commits API | [ ] | Since last_activity |
| per_page: 100 | [ ] | |

#### Node 12: Filter Changes
| Check | Status | Notes |
|-------|--------|-------|
| Ignores test/ci/chore/style/docs | [ ] | Regex patterns |
| Matches staleness_indicators | [ ] | If defined |
| Limits to 20 commits | [ ] | |

#### Node 13: Has Changes? (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `has_relevant_changes === true` |
| True → Prep Doc Fetch | [ ] | |
| False → Log Healthy | [ ] | |

#### Node 14: Prep Doc Fetch
| Check | Status | Notes |
|-------|--------|-------|
| Limits to 3 docs | [ ] | Per domain |
| Prepares for fetch loop | [ ] | |

#### Node 15: Get Doc Content
| Check | Status | Notes |
|-------|--------|-------|
| Fetches from raw.githubusercontent | [ ] | |
| Response format: text | [ ] | |

---

### AI ASSESSMENT (Nodes 16-20)

#### Node 16: Aggregate Docs
| Check | Status | Notes |
|-------|--------|-------|
| Combines doc contents | [ ] | |
| Truncates to 2000 chars each | [ ] | Context limits |

#### Node 17: Staleness Assessment (AI Agent)
| Check | Status | Notes |
|-------|--------|-------|
| Uses Gemini model | [ ] | |
| Output parser configured | [ ] | Structured JSON |
| System prompt complete | [ ] | Scoring criteria defined |

**Staleness Scoring:**
| Score | Meaning |
|-------|---------|
| 0.0-0.2 | Healthy |
| 0.2-0.4 | Minor drift |
| 0.4-0.6 | Moderate staleness |
| 0.6-0.8 | Significant staleness |
| 0.8-1.0 | Critical staleness |

#### Node 18: Gemini 2.5 Flash
| Check | Status | Notes |
|-------|--------|-------|
| Credential valid | [ ] | |

#### Node 19: Structured Output Parser
| Check | Status | Notes |
|-------|--------|-------|
| Schema defined | [ ] | staleness_score, findings, action |

#### Node 20: Parse Assessment
| Check | Status | Notes |
|-------|--------|-------|
| Normalizes score 0-1 | [ ] | |
| Sets recommended_action | [ ] | Based on score thresholds |

---

### ROUTING (Node 21)

#### Node 21: Route By Score (Switch)
| Check | Status | Notes |
|-------|--------|-------|
| ≥0.7 + has tasks → Auto Update | [ ] | Send to Distributor |
| 0.5-0.7 → Manual Review | [ ] | Search/Create Issue |
| 0.3-0.5 → Create Issue | [ ] | Search/Create Issue |
| <0.3 → Healthy | [ ] | Log Healthy |

---

### ACTION HANDLERS (Nodes 22-27)

#### Node 22: Send to Distributor
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | `/webhook/task-distributor` |
| Source: staleness_review | [ ] | |

#### Node 23: Search Existing Issues
| Check | Status | Notes |
|-------|--------|-------|
| GitHub Search API | [ ] | |
| Filters by label + domain | [ ] | `staleness-review` |

#### Node 24: Issue Exists? (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `total_count > 0` |

#### Node 25: Skip Duplicate Issue
| Check | Status | Notes |
|-------|--------|-------|
| Logs skip reason | [ ] | |

#### Node 26: Create Review Issue
| Check | Status | Notes |
|-------|--------|-------|
| GitHub Issues API | [ ] | |
| Title includes score % | [ ] | |
| Labels: documentation, staleness-review, automated | [ ] | |

#### Node 27: Log Healthy
| Check | Status | Notes |
|-------|--------|-------|
| Logs domain status | [ ] | |

---

### DIGEST (Nodes 28-30)

#### Node 28: Collect Results (Merge)
| Check | Status | Notes |
|-------|--------|-------|
| 4 inputs configured | [ ] | All paths converge |

#### Node 29: Generate Digest
| Check | Status | Notes |
|-------|--------|-------|
| Calculates week ID | [ ] | YYYY-WNN format |
| Summarizes all domains | [ ] | |
| Calculates avg staleness | [ ] | |

#### Node 30: Has Findings? (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `domains_need_attention > 0` |
| True → Create Digest Issue | [ ] | |

#### Node 31: Create Digest Issue
| Check | Status | Notes |
|-------|--------|-------|
| Weekly summary issue | [ ] | |
| Labels: staleness-digest | [ ] | |

---

## Issues Found

| # | Severity | Description | Recommendation |
|---|----------|-------------|----------------|
| 1 | 🟢 LOW | Placeholder in distributorWebhook | Clean up unused config value |
| 2 | 🟢 LOW | HTTP Header Auth credential | Verify credential Ho5S7HOxBPdmEAL0 is valid |

---

## Sign-off

- [ ] All 28 nodes validated
- [ ] Staleness scoring logic verified
- [ ] Issue creation/deduplication confirmed
- [ ] Digest generation validated

**Reviewer:** ________________________  
**Date:** ________________________  
**Signature:** ________________________
