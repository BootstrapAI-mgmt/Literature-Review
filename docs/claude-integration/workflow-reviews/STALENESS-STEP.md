# Doc Chain - Staleness: Step-Through Validation

> **Workflow ID**: `WRzBAw1oMYLbnu7d`  
> **Version**: STALE-V001  
> **Total Nodes**: 29 (including AI sub-nodes)  
> **Last n8n Update**: 2025-12-23T17:17:16.841Z

---

## Checkout Status

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |

---

## Flow Diagram (Simplified)

```
┌─ Weekly Review (2 AM) ─┐
│                        ├→ Start Review → Workflow Configuration → Fetch Matrix
└─ Manual Trigger ───────┘                                              │
                                                                   Get Domains
                                                                        │
                                                              Process Each Domain
                                                                        │
                                                              Get Last Activity
                                                                        │
                                                             Calculate Inactivity
                                                                        │
                                                               Needs Review?
                                                        (yes) ↓           ↓ (no)
                                                   Fetch Recent Changes   │
                                                           ↓              │
                                                     Filter Changes       │
                                                           ↓              │
                                                      Has Changes?        │
                                                  (yes) ↓       ↓ (no)    │
                                               Prep Doc Fetch   │         │
                                                     ↓          │         │
                                               Get Doc Content  │         │
                                                     ↓          │         │
                                               Aggregate Docs   │         │
                                                     ↓          │         │
                                            Staleness Assessment│         │
                                              (AI + Parser)     │         │
                                                     ↓          │         │
                                             Parse Assessment   │         │
                                                     ↓          │         │
                                              Route By Score    │         │
                               ┌────────┬────────┬────────┬─────┘         │
                               ↓        ↓        ↓        ↓               ↓
                          Auto Update  Manual   Create   Healthy ←────────┘
                               ↓       Review   Issue      ↓
                          Send to       ↓        ↓         ↓
                         Distributor  Search Issues → Create/Skip
                               │        │        │         │
                               └────────┴────────┴─────────┘
                                            ↓
                                     Collect Results
                                            ↓
                                     Generate Digest
                                            ↓
                                      Has Findings?
                                            ↓ (yes)
                                    Create Digest Issue
```

---

## Node-by-Node Validation

### Trigger Section

#### Node 1: Weekly Review
| ID | `d32e0056-45fd-4a70-9eba-2eb0793d6c28` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Type: Schedule Trigger | [ ] | |
| Interval: Weekly at 2 AM | [ ] | `field: "weeks"` |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 2: Manual Trigger
| ID | `8dfb338b-2c3b-40aa-99fb-978c93c7b81a` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `/staleness-review` | [ ] | |
| Method: POST | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 3: Start Review (Merge)
| ID | `92fc419e-87a1-440d-b10b-22c4c1ea2895` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Mode: combine by position | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Configuration Section

#### Node 4: Workflow Configuration
| ID | `d1f38440-3e89-41bc-813d-288973ecf423` |
|----|-------|

| Field | Value | Status |
|-------|-------|--------|
| matrixUrl | `https://raw.githubusercontent.com/.../documentation_matrix.json` | [ ] |
| githubRepo | `BootstrapAI-mgmt/Literature-Review` | [ ] |
| githubBranch | `main` | [ ] |
| distributorWebhook | ⚠️ PLACEHOLDER | [ ] |

**⚠️ ACTION REQUIRED**: `distributorWebhook` has placeholder value - verify if used.

**Sign-off**: [ ] ________ Date: ________

---

#### Node 5: Fetch Matrix
| ID | `833d76c1-e07a-4af1-ab36-38b3a1df660d` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: Raw GitHub matrix | [ ] | |
| Response format: JSON | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Domain Processing Section

#### Node 6: Get Domains
| ID | `cb76fb1c-a30d-4817-b440-7a9d3965a58d` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Parses `owner_domains` from matrix | [ ] | |
| Handles array and object formats | [ ] | |
| Supports stagger_day scheduling | [ ] | |
| Extracts staleness_indicators | [ ] | |
| Deduplicates indicators | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 7: Process Each Domain
| ID | `51342bce-71f5-4fed-8757-339cbbbb9d27` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Maps domains to items | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 8: Get Last Activity
| ID | `24a488d5-93ee-4ea2-91e0-d81ce7a83dde` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub Commits API | [ ] | |
| Query: path, per_page=1 | [ ] | First doc or `docs/` |
| Uses Header Auth credential | [ ] | Not hardcoded |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 9: Calculate Inactivity
| ID | `ec39350e-4ef5-48a4-bbd7-426b9fc1ba9f` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Calculates days since last commit | [ ] | |
| Compares to review_interval_days | [ ] | Default: 7 days |
| Sets needs_review flag | [ ] | |
| Handles empty commits | [ ] | Defaults to 2000-01-01 |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 10: Needs Review?
| ID | `b2eb4a9d-246b-46ca-9391-98cc87d065f0` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `needs_review === true` | [ ] | |
| True → Fetch Recent Changes | [ ] | |
| False → Log Healthy | [ ] | Skip domain |

**Sign-off**: [ ] ________ Date: ________

---

### Change Analysis Section

#### Node 11: Fetch Recent Changes
| ID | `f8c39769-ff01-4370-917b-8cf562728791` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Query: since=last_activity | [ ] | |
| Query: per_page=100 | [ ] | |
| Uses Header Auth | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 12: Filter Changes
| ID | `1093288b-e833-49dd-8d4e-62d07f778131` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Ignores test/ci/chore/style/docs commits | [ ] | Regex patterns |
| Checks staleness_indicators relevance | [ ] | |
| Limits to 20 relevant changes | [ ] | |
| Sets has_relevant_changes flag | [ ] | |

**Ignore Patterns**:
- `^test(\(|:)` - Test commits
- `^ci(\(|:)` - CI commits
- `^chore(\(|:)` - Chores
- `^style(\(|:)` - Style changes
- `^docs(\(|:)` - Doc commits (checking FOR staleness)

**Sign-off**: [ ] ________ Date: ________

---

#### Node 13: Has Changes?
| ID | `b9a1a2d9-6b26-4b81-bb34-c81c06049511` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `has_relevant_changes === true` | [ ] | |
| True → Prep Doc Fetch | [ ] | |
| False → Log Healthy | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Document Fetch Section

#### Node 14: Prep Doc Fetch
| ID | `912ce88a-d8f9-4bf7-bb07-2a354c0669e6` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Limits to 3 documents | [ ] | Performance |
| Spreads domain data to each | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 15: Get Doc Content
| ID | `f1b4a512-496e-4bc5-ba2c-dc6a91baef83` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: Raw GitHub content | [ ] | Dynamic path |
| Response format: text | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 16: Aggregate Docs
| ID | `a6ea498d-8645-4937-a8ec-95a148769085` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Combines document contents | [ ] | |
| Truncates to 2000 chars each | [ ] | Context limit |
| Formats with headers | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### AI Assessment Section

#### Node 17: Staleness Assessment (AI Agent)
| ID | `606a0720-4ec5-4928-ab92-d1db0d11886d` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| System message defines review criteria | [ ] | |
| Includes staleness scoring guide | [ ] | 0.0-1.0 scale |
| Specifies JSON output format | [ ] | |
| Has output parser connected | [ ] | |

**Staleness Scoring Guide (from prompt)**:
| Score Range | Meaning |
|-------------|---------|
| 0.0-0.2 | Healthy |
| 0.2-0.4 | Minor drift |
| 0.4-0.6 | Moderate staleness |
| 0.6-0.8 | Significant staleness |
| 0.8-1.0 | Critical staleness |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 17a: Gemini 2.5 Flash (Sub-node)
| ID | `585bfbff-159f-4e2f-9299-1c911acf939b` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Credential: Google Gemini API | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 17b: Structured Output Parser (Sub-node)
| ID | `7ea3db7c-bafd-4d9c-becf-3bd31fa0abb9` |
|----|-------|

| Schema Field | Type | Required | Status |
|--------------|------|----------|--------|
| staleness_score | number | Yes | [ ] |
| findings | array[string] | Yes | [ ] |
| recommended_action | enum | Yes | [ ] |
| update_tasks | array[string] | No | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 18: Parse Assessment
| ID | `8885903c-9a65-460a-8a74-28025ffcc190` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Extracts JSON from markdown blocks | [ ] | |
| Normalizes score to 0-1 | [ ] | |
| Generates assessment_id | [ ] | |
| Determines recommended_action | [ ] | Based on score thresholds |
| Normalizes update_tasks | [ ] | |

**Action Thresholds**:
| Score | Action |
|-------|--------|
| >= 0.7 | auto_update |
| >= 0.5 | manual_review |
| >= 0.3 | create_issue |
| < 0.3 | healthy |

**Sign-off**: [ ] ________ Date: ________

---

### Routing Section

#### Node 19: Route By Score (Switch)
| ID | `f386d2e5-45fd-4815-93a2-22f2bd094000` |
|----|-------|

| Output | Condition | Destination | Status |
|--------|-----------|-------------|--------|
| Auto Update | score >= 0.7 AND tasks not empty | Send to Distributor | [ ] |
| Manual Review | 0.5 <= score < 0.7 | Search Existing Issues | [ ] |
| Create Issue | 0.3 <= score < 0.5 | Search Existing Issues | [ ] |
| Healthy (fallback) | score < 0.3 | Log Healthy | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Auto Update Path

#### Node 20: Send to Distributor
| ID | `9a6c894b-5c0b-4caf-9c02-6af0a7044720` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: `/webhook/task-distributor` | [ ] | |
| Method: POST | [ ] | |
| Body includes update_tasks | [ ] | |
| Source: staleness_review | [ ] | |

**Integration Check**:
| This Workflow | Connects To | Status |
|---------------|-------------|--------|
| Send to Distributor | Distributor → Receive List | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Issue Creation Path

#### Node 21: Search Existing Issues
| ID | `efa21e21-a156-4c42-bb82-455a8e86738d` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub Search Issues API | [ ] | |
| Query: repo + is:open + label:staleness-review | [ ] | |
| Searches domain in title | [ ] | Deduplication |
| Uses Header Auth | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 22: Issue Exists?
| ID | `eee3cfb6-f2c1-4e31-a68b-3cc4d6ff381b` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `total_count > 0` | [ ] | |
| True → Skip Duplicate Issue | [ ] | |
| False → Create Review Issue | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 23: Skip Duplicate Issue
| ID | `9ad0c89c-a946-4574-8a7c-1bc4d48b579d` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Logs skip reason | [ ] | |
| Returns status: skipped | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 24: Create Review Issue
| ID | `318d36cf-705e-442c-b528-9564e0a6fcf4` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub Issues API | [ ] | |
| Method: POST | [ ] | |
| Title includes domain and score | [ ] | |
| Body includes findings | [ ] | |
| Labels: documentation, staleness-review, automated | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Results Collection

#### Node 25: Log Healthy
| ID | `291a4c74-cf3f-4f39-bbb1-d5acddb774e7` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Mode: runOnceForEachItem | [ ] | |
| Returns healthy status | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 26: Collect Results (Merge)
| ID | `253e822d-735d-4e65-a684-6797515703f5` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| numberInputs: 4 | [ ] | All paths |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 27: Generate Digest
| ID | `5ac80835-3fe6-4793-9811-4ba0765a54f7` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Calculates week number | [ ] | YYYY-Wxx format |
| Counts domains by health | [ ] | |
| Calculates average staleness | [ ] | |
| Maps domain statuses | [ ] | |

**Digest Output Schema**:
```json
{
  "digest_id": "digest-2024-W52",
  "week": "2024-W52",
  "summary": {
    "domains_reviewed": 5,
    "domains_healthy": 3,
    "domains_need_attention": 2,
    "avg_staleness": 0.35
  },
  "domain_statuses": [...]
}
```

**Sign-off**: [ ] ________ Date: ________

---

#### Node 28: Has Findings?
| ID | `489227d5-b51c-49c1-ae3c-08adc7515474` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `domains_need_attention > 0` | [ ] | |
| True → Create Digest Issue | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 29: Create Digest Issue
| ID | `463bac90-5f77-41e2-b79e-dd446f2a7910` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Title: Weekly Staleness Digest | [ ] | |
| Body: Table of domain statuses | [ ] | |
| Labels: documentation, staleness-digest, automated | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

## Test Scenarios

### Scenario 1: Weekly Run - All Healthy
| Step | Expected | Status |
|------|----------|--------|
| Fetch matrix | Domains extracted | [ ] |
| Check each domain | All < 7 days inactive | [ ] |
| Log Healthy | All domains logged | [ ] |
| Digest | domains_need_attention: 0 | [ ] |
| No digest issue | Skipped | [ ] |

### Scenario 2: Stale Domain with Auto Update
| Step | Expected | Status |
|------|----------|--------|
| Domain inactive > 7 days | needs_review: true | [ ] |
| Relevant changes found | has_relevant_changes: true | [ ] |
| AI assessment | staleness_score: 0.75 | [ ] |
| Route | Auto Update path | [ ] |
| Send to Distributor | Tasks sent | [ ] |

### Scenario 3: Stale Domain - Create Issue
| Step | Expected | Status |
|------|----------|--------|
| AI assessment | staleness_score: 0.4 | [ ] |
| Route | Create Issue path | [ ] |
| Search existing | No duplicate | [ ] |
| Create issue | GitHub issue created | [ ] |

### Scenario 4: Duplicate Issue Prevention
| Step | Expected | Status |
|------|----------|--------|
| Search existing | Finds open issue | [ ] |
| Skip duplicate | Logged and skipped | [ ] |

### Scenario 5: Manual Trigger
| Step | Expected | Status |
|------|----------|--------|
| POST to webhook | Workflow starts | [ ] |
| Full review runs | All domains checked | [ ] |

---

## Configuration Notes

### ⚠️ Placeholder Value
The `distributorWebhook` in Workflow Configuration contains a placeholder:
```
<__PLACEHOLDER_VALUE__Task Distributor Webhook URL__>
```
**Note**: This appears to be unused - the Send to Distributor node uses a hardcoded URL instead.

### Domain Staggering
The workflow supports domain staggering via `stagger_day` in the matrix:
- If `config.schedule.stagger_domains` is enabled
- Only domains scheduled for the current day are processed
- Otherwise all domains are processed in weekly batch

---

## Final Sign-Off

| Reviewer | Date | Status |
|----------|------|--------|
| | | |

**Workflow Approved**: [ ] Yes [ ] No

### Issues Found
| Node | Issue | Severity | Resolution |
|------|-------|----------|------------|
| | | | |

---

*Document Version: 1.0*  
*Created: 2024-12-25*
