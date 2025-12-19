# State Reconciliation - n8n Builder Prompt (Minimal)

**Workflow 6:** Verify documentation file counts match repository state. 17 nodes total.

## Node List (Build Exactly)

| # | Type | Name |
|---|------|------|
| 1 | Schedule Trigger | Daily Reconciliation |
| 2 | Webhook | Manual Trigger |
| 3 | Merge | Start (Mode: Append, Include Unpaired: ✅) |
| 4 | Code | Workflow Configuration |
| 5 | HTTP Request | Fetch Matrix |
| 6 | HTTP Request | List Task Cards |
| 7 | Code | Filter and Group Cards |
| 8 | Split In Batches | Process Each Directory |
| 9 | Code | Extract Status from Cards |
| 10 | Code | Aggregate All Directories |
| 11 | HTTP Request | Fetch Current Indexes |
| 12 | Code | Find Mismatches |
| 13 | If | Has Mismatches? |
| 14 | AI Agent | Generate Corrections |
| 15 | Code | Log In Sync |
| 16 | HTTP Request | Send to Distributor |

## Key Connections

```
1,2 → 3 → 4 → 5 → 6 → 7 → 8 ⟲ 9 (loop)
                              ↓
                         10 → 11 → 12 → 13
                                         ├─ true → 14 → 16
                                         └─ false → 15
```

## Node 4 Config (Workflow Configuration)
```javascript
// Compare FILE COUNTS only, not completion status.
// Task card status is inside file content, not filenames.
return {
  target_indexes: ['task-cards/README.md']
};
```

## Node 9 (Extract Status from Cards)
Note: Despite its name, this node now counts files rather than extracting status from filenames.
```javascript
// Just count files - don't try to infer completion from filenames
const batchItem = $input.first().json;
return {
  directory: batchItem.directory,
  config: batchItem.config,
  cards: batchItem.cards.map(c => ({ path: c.path, name: c.path.split('/').pop() })),
  summary: { file_count: batchItem.cards.length }
};
```

## Node 14 (AI Agent)
- Model: Gemini 2.5 Flash
- Output Parser: Use Code node (Clean AI Output) instead
- System: "Generate correction tasks for file count mismatches. Output JSON: {update_list_id, source, tasks[]}"

## URLs
- List Task Cards: `api.github.com/.../git/trees/main?recursive=1`
- Fetch Indexes: `api.github.com/.../contents/task-cards/README.md`
- Distributor: `gitlitreview.app.n8n.cloud/webhook/task-distributor`

## Headers (all GitHub requests)
- Authorization: `Bearer YOUR_PAT`
- Accept: `application/vnd.github.v3+json`
