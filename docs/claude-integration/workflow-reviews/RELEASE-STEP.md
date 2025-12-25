# Doc Chain - Release: Step-Through Validation

> **Workflow ID**: `pwtrU5ucVt4AKvZF`  
> **Version**: Release-V001 (Phase 4 New)  
> **Total Nodes**: 10  
> **Last n8n Update**: 2025-12-25T00:50:18.836Z

---

## Checkout Status

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |

---

## Flow Diagram

```
Release Trigger → Configuration → Get Recent Tags → Parse Tags → Has Tags?
                                                                   ↓ (yes)
                                                    Get Commits Since Previous
                                                                   ↓
                                                       Generate Changelog
                                                                   ↓
                                                      Create GitHub Release
                                                                   ↓
                                                          Log Success

                                                   Has Tags? (no) → Log Error
```

---

## Node-by-Node Validation

### Node 1: Release Trigger
| ID | `release-webhook` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `/release-automation` | [ ] | |
| Method: POST | [ ] | |
| Accepts tag in body | [ ] | `{"tag": "v1.0.0"}` or `{"tag": "latest"}` |

**Usage Examples**:
```bash
# Specific tag
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/release-automation \
  -H "Content-Type: application/json" -d '{"tag": "v1.0.0"}'

# Latest tag
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/release-automation \
  -H "Content-Type: application/json" -d '{}'
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 2: Configuration
| ID | `config-node` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Sets repo_owner | [ ] | `BootstrapAI-mgmt` |
| Sets repo_name | [ ] | `Literature-Review` |
| Extracts tag from body | [ ] | Defaults to `'latest'` |

**Sign-off**: [ ] ________ Date: ________

---

### Node 3: Get Recent Tags
| ID | `get-tags` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub Tags API | [ ] | `/repos/.../tags` |
| Limit: 5 tags | [ ] | `per_page=5` |
| Uses Header Auth credential | [ ] | Not hardcoded |

**Sign-off**: [ ] ________ Date: ________

---

### Node 4: Parse Tags
| ID | `parse-tags` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Handles empty tag list | [ ] | Returns error object |
| Finds specific tag if requested | [ ] | |
| Uses latest if not specified | [ ] | `tagList[0]` |
| Identifies previous tag | [ ] | For changelog range |
| Returns SHAs for comparison | [ ] | |

**Output Schema**:
```json
{
  "current_tag": "v1.0.0",
  "current_sha": "abc123...",
  "previous_tag": "v0.9.0",
  "previous_sha": "def456...",
  "repo_owner": "BootstrapAI-mgmt",
  "repo_name": "Literature-Review"
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 5: Has Tags?
| ID | `has-tags-check` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `current_tag !== null` | [ ] | |
| True → Get Commits | [ ] | |
| False → Log Error | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 6: Get Commits Since Previous
| ID | `get-commits` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: Compare API | [ ] | `/repos/.../compare/{base}...{head}` |
| Handles no previous tag | [ ] | Falls back to `~10` |
| Uses Header Auth | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 7: Generate Changelog
| ID | `generate-changelog` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Categorizes by conventional commit | [ ] | feat, fix, docs, etc. |
| Skips merge commits | [ ] | `startsWith('Merge ')` |
| Skips [n8n] commits | [ ] | `startsWith('[n8n]')` |
| Formats with emojis | [ ] | ✨ 🐛 📚 etc. |
| Includes commit SHAs | [ ] | Abbreviated |

**Categories Verified**:
| Type | Emoji | Title | Status |
|------|-------|-------|--------|
| feat | ✨ | Features | [ ] |
| fix | 🐛 | Bug Fixes | [ ] |
| docs | 📚 | Documentation | [ ] |
| chore | 🔧 | Maintenance | [ ] |
| refactor | ♻️ | Refactoring | [ ] |
| test | 🧪 | Tests | [ ] |
| other | 📝 | Other Changes | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Node 8: Create GitHub Release
| ID | `create-release` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: Releases API | [ ] | `/repos/.../releases` |
| Method: POST | [ ] | |
| tag_name from tag | [ ] | |
| body from changelog | [ ] | JSON.stringify |
| prerelease detection | [ ] | If tag contains `-` |
| draft: false | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 9: Log Success
| ID | `success-log` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns release URL | [ ] | |
| Returns commit count | [ ] | |
| Returns success message | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 10: Log Error
| ID | `error-log` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns error message | [ ] | From Parse Tags |
| Returns status: error | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

## Repository Alignment

| Check | Status | Notes |
|-------|--------|-------|
| Repo has tags | [ ] | Test: `git tag -l` |
| Tags follow semver | [ ] | v1.0.0 format |
| Commits use conventional format | [ ] | For proper categorization |

---

## Test Scenarios

### Scenario 1: Latest Tag Release
| Step | Expected | Status |
|------|----------|--------|
| POST with empty body | tag = 'latest' | [ ] |
| Get tags returns array | At least 1 tag | [ ] |
| Compare commits | Commits listed | [ ] |
| Changelog generated | Categorized | [ ] |
| Release created | GitHub release exists | [ ] |

### Scenario 2: Specific Tag Release
| Step | Expected | Status |
|------|----------|--------|
| POST with `{"tag": "v1.0.0"}` | tag = 'v1.0.0' | [ ] |
| Tag found in list | Index found | [ ] |
| Compare to previous tag | Correct range | [ ] |

### Scenario 3: No Tags
| Step | Expected | Status |
|------|----------|--------|
| Repository has no tags | Empty array | [ ] |
| Error logged | "No tags found" | [ ] |

### Scenario 4: Prerelease Detection
| Step | Expected | Status |
|------|----------|--------|
| Tag: `v1.0.0-beta` | prerelease: true | [ ] |
| Tag: `v1.0.0` | prerelease: false | [ ] |

---

## Final Sign-Off

| Reviewer | Date | Status |
|----------|------|--------|
| | | |

**Workflow Approved**: [ ] Yes [ ] No

---

*Document Version: 1.0*  
*Created: 2024-12-24*
