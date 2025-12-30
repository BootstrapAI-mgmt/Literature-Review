# Workflow Review: Doc Chain - Release

**Workflow ID:** `pwtrU5ucVt4AKvZF`
**Version:** RELEASE-V001
**Updated:** 2025-12-25
**Nodes:** 10

---

## Checkout Status

| Field | Value |
|-------|-------|
| Reviewer | ⬜ Unclaimed |
| Checkout Time | - |
| Status | 🟢 Available |
| Sign-off | ⬜ Pending |

---

## Purpose

Automates the creation of GitHub Releases by generating a changelog from conventional commits since the previous tag.

---

## Node-by-Node Review

### Node 1: Release Trigger
**Type:** `n8n-nodes-base.webhook`
**Path:** `/release-automation`

| Check | Status | Notes |
|-------|--------|-------|
| Payload | ⬜ | `{"tag": "v1.0.0"}` or empty |

---

### Node 2: Configuration
**Type:** `n8n-nodes-base.set`

| Check | Status | Notes |
|-------|--------|-------|
| Repo config | ⬜ | Hardcoded owner/name |
| Tag selection | ⬜ | Defaults to 'latest' |

---

### Node 3: Get Recent Tags
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `.../tags?per_page=5`

| Check | Status | Notes |
|-------|--------|-------|
| Fetch recent tags | ⬜ | Used to find current/prev range |

---

### Node 4: Parse Tags
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Find logic | ⬜ | Locates tag index in list |
| Previous tag | ⬜ | index + 1 |

---

### Node 5: Has Tags?
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| Safety check | ⬜ | Prevents error if no tags exist |

---

### Node 6: Get Commits Since Previous
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `.../compare/{prev}...{curr}`

| Check | Status | Notes |
|-------|--------|-------|
| Comparison API | ⬜ | Uses GitHub compare endpoint |
| Fallback | ⬜ | `~10` if no previous tag? |

---

### Node 7: Generate Changelog
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Conventional Commits | ⬜ | Categorizes feat, fix, docs, etc. |
| Formatting | ⬜ | Markdown grouping |
| Filtering | ⬜ | Skips `Merge` and `[n8n]` commits |

---

### Node 8: Create GitHub Release
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `.../releases`

| Check | Status | Notes |
|-------|--------|-------|
| Payload mapping | ⬜ | tag_name, name, body (changelog) |
| Prerelease logic | ⬜ | Checks for hyphen in tag |

---

## Data Flow

```
Webhook → Config → Get Tags → Parse → Get Commits → Changelog → Create Release
```

---

## Test Scenarios

### Test 1: Standard Release
Trigger with new tag. Verify changelog includes recent commits formatted by category.

### Test 2: First Release
Release with no previous tag. Should fallback gracefully (or fail depending on `~10` logic).

### Test 3: No Conventional Commit
Commits without prefixes (feat:, fix:) should go to "Other Changes".

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| All nodes reviewed | ⬜ | - | - |
| Changelog logic correct | ⬜ | - | - |
| Release creation works | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
